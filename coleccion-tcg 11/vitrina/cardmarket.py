"""Integración con Cardmarket.

Dos vías, ambas reales:

1) FICHEROS OFICIALES (recomendada, no necesita credenciales).
   Cardmarket publica la guía de precios y el catálogo de productos en
   https://www.cardmarket.com/Data/Download (hay que estar logueado).
   La guía se actualiza una vez al día. Desde 2024 estos ficheros
   sustituyen al antiguo endpoint /priceguide de la API, que quedó
   deprecado. Descarga los de tus juegos, déjalos en data/ y ejecuta
   la sincronización: el importador detecta solo el formato
   (csv / json / gzip) y el nombre de cada columna.

2) API 2.0 CON CREDENCIALES (opcional).
   Para buscar productos por nombre y leer las ofertas vivas de una
   carta. Requiere una app creada en tu perfil de Cardmarket
   (OAuth 1.0a, HMAC-SHA1, "dedicated app": el realm es la URL completa).

Lo que NO existe en ninguna de las dos: un listado de ventas individuales.
Cardmarket no lo publica. Lo más cercano es AVG1, el precio medio de las
unidades vendidas ese día; guardando un AVG1 por día se construye el
histórico de ventas que se ve en la app.
"""

import base64
import csv
import gzip
import hashlib
import hmac
import io
import json
import os
import random
import time
import urllib.parse
import urllib.request

API_BASE = "https://api.cardmarket.com/ws/v2.0/output.json"
DOWNLOADS_PAGE = "https://www.cardmarket.com/Data/Download"

# Nombres de columna posibles -> campo interno. Se compara en minúsculas y
# sin espacios, guiones ni puntos, porque el formato ha ido cambiando.
PRICE_KEYS = {
    "idproduct": "id_product",
    "productid": "id_product",
    "avgsellprice": "avg",
    "avg": "avg",
    "average": "avg",
    "lowprice": "low",
    "low": "low",
    "trendprice": "trend",
    "trend": "trend",
    "avg1": "avg1",
    "avg1day": "avg1",
    "avg7": "avg7",
    "avg7days": "avg7",
    "avg30": "avg30",
    "avg30days": "avg30",
}

PRODUCT_KEYS = {
    "idproduct": "id_product",
    "productid": "id_product",
    "name": "name",
    "enname": "name",
    "expansion": "expansion",
    "expansionname": "expansion",
    "idexpansion": "expansion",
    "categoryname": "category",
    "category": "category",
}


def _norm(k):
    return "".join(ch for ch in str(k).lower() if ch.isalnum())


def _num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s.lower() in ("null", "none", "n/a", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------- lectura de ficheros

def _raw(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    return blob


def _records(path):
    """Devuelve una lista de dicts, venga el fichero como venga."""
    blob = _raw(path)
    text = blob.decode("utf-8-sig", errors="replace").strip()

    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            # A veces el contenido llega dentro de una clave, y en el formato
            # antiguo de la API venía en base64+gzip.
            for k in ("priceGuides", "priceguides", "products", "product", "data", "items"):
                if isinstance(data.get(k), list):
                    return data[k]
            for k in ("priceguidefile", "productsfile", "file"):
                if isinstance(data.get(k), str):
                    inner = gzip.decompress(base64.b64decode(data[k]))
                    return list(csv.DictReader(io.StringIO(inner.decode("utf-8-sig"))))
            raise ValueError(f"No encuentro la lista de registros en {os.path.basename(path)}")
        return data

    sample = text[:4000]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def _map_rows(rows, keymap, wanted):
    out = []
    for row in rows:
        rec = {k: None for k in wanted}
        for k, v in row.items():
            field = keymap.get(_norm(k))
            if field:
                rec[field] = v
        if rec.get("id_product") in (None, ""):
            continue
        try:
            rec["id_product"] = int(float(rec["id_product"]))
        except (TypeError, ValueError):
            continue
        out.append(rec)
    return out


def parse_price_guide(path):
    rows = _map_rows(_records(path), PRICE_KEYS,
                     ["id_product", "low", "trend", "avg", "avg1", "avg7", "avg30"])
    for r in rows:
        for k in ("low", "trend", "avg", "avg1", "avg7", "avg30"):
            r[k] = _num(r[k])
    return rows


def parse_catalogue(path, game=""):
    rows = _map_rows(_records(path), PRODUCT_KEYS,
                     ["id_product", "name", "expansion", "category"])
    for r in rows:
        r["name"] = (r["name"] or "").strip()
        r["expansion"] = str(r["expansion"] or "").strip()
        r["category"] = str(r["category"] or "").strip()
        r["game"] = game or _guess_game(os.path.basename(path))
    return rows


def _guess_game(filename):
    f = filename.lower()
    for key, label in (("pokemon", "Pokémon"), ("onepiece", "One Piece"),
                       ("one_piece", "One Piece"), ("magic", "Magic"),
                       ("yugioh", "Yu-Gi-Oh!"), ("lorcana", "Lorcana")):
        if key in f:
            return label
    return ""


def sync_folder(con, folder, snapshot_date=None):
    """Importa todos los ficheros de data/. Devuelve un resumen legible."""
    from . import db
    import datetime

    snapshot_date = snapshot_date or datetime.date.today().isoformat()
    summary = {"prices": 0, "products": 0, "files": [], "errors": []}
    if not os.path.isdir(folder):
        summary["errors"].append(f"No existe la carpeta {folder}")
        return summary

    for fn in sorted(os.listdir(folder)):
        if fn.startswith("."):
            continue
        path = os.path.join(folder, fn)
        if not os.path.isfile(path):
            continue
        low = fn.lower()
        try:
            if "price" in low or "guide" in low:
                rows = parse_price_guide(path)
                db.upsert_prices(con, rows, snapshot_date)
                summary["prices"] += len(rows)
                summary["files"].append(f"{fn}: {len(rows)} precios")
            elif "product" in low or "catalog" in low or "singles" in low:
                rows = parse_catalogue(path)
                db.upsert_products(con, rows)
                summary["products"] += len(rows)
                summary["files"].append(f"{fn}: {len(rows)} productos")
            else:
                summary["files"].append(f"{fn}: ignorado (el nombre no dice si es precio o catálogo)")
        except Exception as exc:  # noqa: BLE001
            summary["errors"].append(f"{fn}: {exc}")

    db.set_meta(con, "last_sync", snapshot_date)
    return summary


# ---------------------------------------------------------------- API 2.0 (opcional)

class CardmarketAPI:
    """Cliente OAuth 1.0a mínimo, sólo con la librería estándar."""

    def __init__(self, app_token, app_secret, access_token, access_secret, timeout=20):
        self.app_token = app_token
        self.app_secret = app_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.timeout = timeout

    @property
    def configured(self):
        return all([self.app_token, self.app_secret, self.access_token, self.access_secret])

    def _header(self, method, url, params):
        oauth = {
            "oauth_consumer_key": self.app_token,
            "oauth_token": self.access_token,
            "oauth_nonce": hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest(),
            "oauth_timestamp": str(int(time.time())),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_version": "1.0",
        }
        # El realm no entra en la firma; el resto de parámetros sí, ordenados.
        signing = {**oauth, **{k: str(v) for k, v in params.items()}}
        encoded = "&".join(
            f"{urllib.parse.quote(k, safe='~')}={urllib.parse.quote(v, safe='~')}"
            for k, v in sorted(signing.items())
        )
        base = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe="~"),
            urllib.parse.quote(encoded, safe="~"),
        ])
        key = f"{urllib.parse.quote(self.app_secret, safe='~')}&{urllib.parse.quote(self.access_secret, safe='~')}"
        sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
        oauth["oauth_signature"] = sig
        parts = ", ".join(f'{k}="{urllib.parse.quote(v, safe="~")}"' for k, v in oauth.items())
        return f'OAuth realm="{url}", {parts}'

    def get(self, endpoint, params=None):
        if not self.configured:
            raise RuntimeError("Faltan credenciales de Cardmarket en config.json")
        params = params or {}
        url = f"{API_BASE}{endpoint}"
        req_url = url + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(req_url, headers={
            "Authorization": self._header("GET", url, params),
            "Accept": "application/json",
            "User-Agent": "coleccion-tcg/1.0",
        })
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    # --- llamadas útiles -------------------------------------------------

    def games(self):
        return self.get("/games").get("game", [])

    def find_products(self, name, id_game=None, exact=False):
        params = {"search": name, "exact": "true" if exact else "false"}
        if id_game:
            params["idGame"] = id_game
        data = self.get("/products/find", params)
        prods = data.get("product", [])
        return prods if isinstance(prods, list) else [prods]

    def product(self, id_product):
        return self.get(f"/products/{id_product}").get("product", {})

    def articles(self, id_product, min_condition="NM", id_language=None, start=0, max_results=20):
        """Ofertas vivas: lo más cerca de 'lo que se está pagando ahora mismo'."""
        params = {"start": start, "maxResults": max_results, "minCondition": min_condition}
        if id_language:
            params["idLanguage"] = id_language
        arts = self.get(f"/articles/{id_product}", params).get("article", [])
        return arts if isinstance(arts, list) else [arts]

    def cheapest(self, id_product, **kw):
        arts = self.articles(id_product, **kw)
        prices = sorted(a["price"] for a in arts if a.get("price"))
        if not prices:
            return None
        return {
            "from": prices[0],
            "avg5": sum(prices[:5]) / len(prices[:5]),
            "n": len(prices),
        }
