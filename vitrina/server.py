"""Servidor de la vitrina. En modo compartido escucha en toda tu red wifi
para que el móvil u otro ordenador usen la misma base de datos."""

import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import art, cardmarket, db, psa, search, ui, valuation


import threading
import hashlib
import secrets
import datetime
STATE_LOCK = threading.Lock()


def _hash_clave(clave, salt):
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(salt), 200_000).hex()


def make_handler(con, config):
    base_dir = config.get("base_dir", ".")

    cuentas = bool(config.get("cuentas"))
    db.ensure_users(con)

    def api_client():
        return cardmarket.CardmarketAPI(
            config.get("app_token"), config.get("app_secret"),
            config.get("access_token"), config.get("access_secret"))

    class Handler(BaseHTTPRequestHandler):
        server_version = "coleccion-tcg"

        def log_message(self, fmt, *args):
            pass  # sin ruido en el terminal

        # -------------------------------------------------- utilidades
        def _send(self, code, body, ctype="application/json; charset=utf-8", cache=None):
            data = body if isinstance(body, bytes) else str(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if cache:
                self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False, default=str))

        def _error(self, msg, code=400):
            self._json({"error": str(msg)}, code)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

        def _uid(self):
            """Devuelve el usuario de la ficha de acceso, o None."""
            auth = self.headers.get("Authorization") or ""
            token = auth[7:] if auth.startswith("Bearer ") else ""
            if not token:
                return None
            row = con.execute("SELECT user_id FROM tokens WHERE token=?", (token,)).fetchone()
            return row[0] if row else None

        def _bucket(self, uid):
            """Claves del estado: por usuario con cuenta, compartidas sin ella."""
            return (f"appstate:{uid}", f"appstate_v:{uid}") if uid else ("appstate", "appstate_v")

        # -------------------------------------------------- GET
        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(url.query)
            one = lambda k, d="": (qs.get(k) or [d])[0]  # noqa: E731
            try:
                if url.path in ("/", "/index.html", "/app") or url.path.startswith("/@"):
                    page = os.path.join(base_dir, "collector.app.html")
                    if os.path.exists(page):
                        with open(page, "rb") as fh:
                            return self._send(200, fh.read(), "text/html; charset=utf-8")
                    return self._send(200, ui.PAGE, "text/html; charset=utf-8")

                if url.path == "/clasico":
                    return self._send(200, ui.PAGE, "text/html; charset=utf-8")

                if url.path == "/api/appstate":
                    uid = self._uid()
                    if cuentas and not uid:
                        return self._error("hace falta entrar con tu cuenta", 401)
                    k, kv = self._bucket(uid)
                    raw = db.get_meta(con, k) or "{}"
                    ver = int(db.get_meta(con, kv) or 0)
                    return self._send(200, '{"version": %d, "state": %s}' % (ver, raw))

                if url.path == "/manifest.webmanifest":
                    return self._send(200, json.dumps({
                        "name": "collector.app", "short_name": "collector",
                        "start_url": "/", "display": "standalone",
                        "background_color": "#0b1b13", "theme_color": "#0b1b13",
                        "icons": [{"src": "/icon.png", "sizes": "512x512", "type": "image/png"}],
                    }), "application/manifest+json")

                if url.path == "/icon.png":
                    ic = os.path.join(base_dir, "icon.png")
                    if os.path.exists(ic):
                        with open(ic, "rb") as fh:
                            return self._send(200, fh.read(), "image/png", cache="max-age=86400")
                    return self._error("sin icono", 404)

                if url.path.startswith("/api/publico/"):
                    nombre = url.path.split("/api/publico/", 1)[1].strip("/").lstrip("@").lower()
                    row = con.execute("SELECT id, public FROM users WHERE name=?", (nombre,)).fetchone()
                    if not row or not row[1]:
                        return self._error("esa vitrina no existe o no es pública", 404)
                    raw = db.get_meta(con, f"appstate:{row[0]}") or "{}"
                    try:
                        cards = (json.loads(raw).get("cards") or [])
                    except Exception:
                        cards = []
                    publicas = [{k: c.get(k) for k in
                                 ("name", "collection", "number", "category", "variant",
                                  "rarity", "sealed", "graded", "grader", "grade",
                                  "quantity", "image", "cache")}
                                for c in cards if not c.get("wish")]
                    return self._json({"usuario": nombre, "cards": publicas})

                if url.path == "/api/perfil":
                    uid = self._uid()
                    if not uid:
                        return self._error("hace falta entrar con tu cuenta", 401)
                    row = con.execute("SELECT name, email, created FROM users WHERE id=?", (uid,)).fetchone()
                    if not row:
                        return self._error("cuenta no encontrada", 404)
                    pub = con.execute("SELECT public FROM users WHERE id=?", (uid,)).fetchone()
                    return self._json({"usuario": row[0], "correo": row[1] or "",
                                       "alta": (row[2] or "")[:10], "publico": bool(pub and pub[0])})

                if url.path == "/api/admin":
                    uid = self._uid()
                    if uid != 1:
                        return self._error("sólo el dueño de la web", 403)
                    filas = []
                    for (i, nom, mail, alta, pub) in con.execute(
                            "SELECT id, name, email, created, public FROM users ORDER BY id"):
                        raw = db.get_meta(con, f"appstate:{i}") or "{}"
                        try:
                            n = len(json.loads(raw).get("cards") or [])
                        except Exception:
                            n = 0
                        ult = con.execute("SELECT MAX(created) FROM tokens WHERE user_id=?", (i,)).fetchone()[0]
                        filas.append({"usuario": nom, "correo": mail or "", "alta": (alta or "")[:10],
                                      "cartas": n, "publico": bool(pub),
                                      "ultimo": (ult or "")[:16].replace("T", " ")})
                    return self._json({"usuarios": filas})

                if url.path == "/api/admin/copia":
                    uid = self._uid()
                    if uid != 1:
                        return self._error("sólo el dueño de la web", 403)
                    usuarios = [dict(zip(("id", "name", "email", "created", "public", "salt", "hash"), f))
                                for f in con.execute(
                                    "SELECT id, name, email, created, public, salt, hash FROM users")]
                    estados = {}
                    for (u,) in con.execute("SELECT id FROM users"):
                        estados[str(u)] = json.loads(db.get_meta(con, f"appstate:{u}") or "{}")
                    cuerpo = json.dumps({"copia": "collector.app-servidor", "usuarios": usuarios,
                                         "estados": estados}, ensure_ascii=False)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Disposition", "attachment; filename=copia-servidor.json")
                    cuerpo = cuerpo.encode("utf-8")
                    self.send_header("Content-Length", str(len(cuerpo)))
                    self.end_headers()
                    self.wfile.write(cuerpo)
                    return

                if url.path == "/api/quien":
                    uid = self._uid()
                    nombre = None
                    if uid:
                        row = con.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()
                        nombre = row[0] if row else None
                    return self._json({"cuentas": cuentas, "usuario": nombre})

                if url.path == "/api/state":
                    basis = one("basis", "avg7")
                    if basis not in valuation.BASES:
                        basis = "avg7"
                    state = valuation.portfolio(con, basis)
                    state["last_sync"] = db.get_meta(con, "last_sync")
                    state["cm_linked"] = api_client().configured
                    return self._json(state)

                if url.path == "/api/search":
                    return self._json(search.search(
                        con, one("q"), one("cat") or None, api_client()))

                if url.path == "/api/products":  # compatibilidad
                    q = one("q")
                    return self._json({"results": db.search_products(con, q) if q else []})

                if url.path == "/api/art":
                    cat = one("cat", "all")
                    cats = art.CATEGORIES if cat == "all" else [cat]
                    imgs = []
                    for c in cats:
                        imgs += art.images_for(base_dir, c)
                    return self._json({
                        "images": imgs,
                        "motif": f"/art/motif/{cat}.svg",
                        "palette": art.PALETTES.get(cat, art.PALETTES["all"]),
                    })

                if url.path.startswith("/art/motif/"):
                    cat = url.path.rsplit("/", 1)[-1].replace(".svg", "")
                    return self._send(200, art.motif(cat), "image/svg+xml",
                                      cache="max-age=3600")

                if url.path.startswith("/art/"):
                    return self._serve_art(url.path)

                if url.path.startswith("/api/psa/"):
                    cert = url.path.rsplit("/", 1)[-1]
                    return self._json(psa.cert_lookup(config.get("psa_token"), cert))

                return self._error("Ruta desconocida", 404)
            except Exception as exc:  # noqa: BLE001
                return self._error(exc, 500)

        def _serve_art(self, path):
            rel = urllib.parse.unquote(path[len("/art/"):])
            root = os.path.abspath(art.art_dir(base_dir))
            full = os.path.abspath(os.path.join(root, rel))
            if not full.startswith(root + os.sep) or not os.path.isfile(full):
                return self._error("Imagen no encontrada", 404)
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            with open(full, "rb") as fh:
                return self._send(200, fh.read(), ctype, cache="max-age=86400")

        # -------------------------------------------------- POST
        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path

            if path in ("/api/registro", "/api/acceso"):
                try:
                    body = self._body()
                    nombre = str(body.get("usuario") or "").strip().lower()
                    clave = str(body.get("clave") or "")
                    if not (2 <= len(nombre) <= 30) or not nombre.replace("_", "").replace(".", "").isalnum():
                        return self._error("el nombre: de 2 a 30 letras o números (vale _ y .)")
                    if len(clave) < 6:
                        return self._error("la clave necesita al menos 6 caracteres")
                    correo = str(body.get("correo") or "").strip().lower()
                    if path == "/api/registro":
                        if not ("@" in correo and "." in correo.split("@")[-1] and 5 <= len(correo) <= 120):
                            return self._error("hace falta un correo válido para poder recuperar la clave")
                    with STATE_LOCK:
                        row = con.execute("SELECT id, salt, hash FROM users WHERE name=?", (nombre,)).fetchone()
                        if path == "/api/registro":
                            if row:
                                return self._error("ese nombre ya está cogido", 409)
                            salt = secrets.token_hex(16)
                            con.execute("INSERT INTO users(name, salt, hash, created, email) VALUES(?,?,?,?,?)",
                                        (nombre, salt, _hash_clave(clave, salt),
                                         datetime.datetime.utcnow().isoformat(), correo))
                            uid = con.execute("SELECT id FROM users WHERE name=?", (nombre,)).fetchone()[0]
                        else:
                            if not row or not secrets.compare_digest(row[2], _hash_clave(clave, row[1])):
                                return self._error("nombre o clave incorrectos", 401)
                            uid = row[0]
                        token = secrets.token_hex(24)
                        con.execute("INSERT INTO tokens(token, user_id, created) VALUES(?,?,?)",
                                    (token, uid, datetime.datetime.utcnow().isoformat()))
                        con.commit()
                    return self._json({"token": token, "usuario": nombre})
                except Exception as exc:   # noqa: BLE001
                    return self._error(exc, 500)

            if path == "/api/recuperar":
                try:
                    body = self._body()
                    nombre = str(body.get("usuario") or "").strip().lower()
                    correo = str(body.get("correo") or "").strip().lower()
                    nueva = str(body.get("clave") or "")
                    if len(nueva) < 6:
                        return self._error("la clave nueva necesita al menos 6 caracteres")
                    with STATE_LOCK:
                        row = con.execute("SELECT id, email FROM users WHERE name=?", (nombre,)).fetchone()
                        if not row or not row[1] or row[1] != correo:
                            return self._error("ese usuario y correo no casan", 401)
                        salt = secrets.token_hex(16)
                        con.execute("UPDATE users SET salt=?, hash=? WHERE id=?",
                                    (salt, _hash_clave(nueva, salt), row[0]))
                        con.execute("DELETE FROM tokens WHERE user_id=?", (row[0],))
                        con.commit()
                    return self._json({"hecho": True})
                except Exception as exc:   # noqa: BLE001
                    return self._error(exc, 500)

            if path == "/api/perfil":
                try:
                    uid = self._uid()
                    if not uid:
                        return self._error("hace falta entrar con tu cuenta", 401)
                    body = self._body()
                    actual = str(body.get("clave_actual") or "")
                    with STATE_LOCK:
                        row = con.execute("SELECT salt, hash, name FROM users WHERE id=?", (uid,)).fetchone()
                        if not row or not secrets.compare_digest(row[1], _hash_clave(actual, row[0])):
                            return self._error("la clave actual no es correcta", 401)
                        if body.get("nuevo_usuario"):
                            nu = str(body["nuevo_usuario"]).strip().lower()
                            if not (2 <= len(nu) <= 30) or not nu.replace("_", "").replace(".", "").isalnum():
                                return self._error("el nombre: de 2 a 30 letras o números (vale _ y .)")
                            if con.execute("SELECT 1 FROM users WHERE name=? AND id<>?", (nu, uid)).fetchone():
                                return self._error("ese nombre ya está cogido", 409)
                            con.execute("UPDATE users SET name=? WHERE id=?", (nu, uid))
                        if body.get("nuevo_correo"):
                            nc = str(body["nuevo_correo"]).strip().lower()
                            if not ("@" in nc and "." in nc.split("@")[-1] and 5 <= len(nc) <= 120):
                                return self._error("ese correo no parece válido")
                            con.execute("UPDATE users SET email=? WHERE id=?", (nc, uid))
                        if "publico" in body:
                            con.execute("UPDATE users SET public=? WHERE id=?",
                                        (1 if body["publico"] else 0, uid))
                        if body.get("nueva_clave"):
                            nk = str(body["nueva_clave"])
                            if len(nk) < 6:
                                return self._error("la clave nueva necesita al menos 6 caracteres")
                            salt = secrets.token_hex(16)
                            con.execute("UPDATE users SET salt=?, hash=? WHERE id=?",
                                        (salt, _hash_clave(nk, salt), uid))
                            auth = self.headers.get("Authorization") or ""
                            mio = auth[7:] if auth.startswith("Bearer ") else ""
                            con.execute("DELETE FROM tokens WHERE user_id=? AND token<>?", (uid, mio))
                        con.commit()
                        nombre = con.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()[0]
                    return self._json({"hecho": True, "usuario": nombre})
                except Exception as exc:   # noqa: BLE001
                    return self._error(exc, 500)

            if path == "/api/salir":
                auth = self.headers.get("Authorization") or ""
                token = auth[7:] if auth.startswith("Bearer ") else ""
                with STATE_LOCK:
                    con.execute("DELETE FROM tokens WHERE token=?", (token,))
                    con.commit()
                return self._json({"hecho": True})

            if path == "/api/appstate":
                try:
                    uid = self._uid()
                    if cuentas and not uid:
                        return self._error("hace falta entrar con tu cuenta", 401)
                    k, kv = self._bucket(uid)
                    body = self._body()
                    base = int(body.get("version", -1))
                    with STATE_LOCK:
                        ver = int(db.get_meta(con, kv) or 0)
                        if base != ver:   # otro dispositivo guardó antes: devuelve lo suyo para mezclar
                            raw = db.get_meta(con, k) or "{}"
                            return self._send(409, '{"version": %d, "state": %s}' % (ver, raw))
                        db.set_meta(con, k, json.dumps(body.get("state") or {}, ensure_ascii=False))
                        db.set_meta(con, kv, str(ver + 1))
                        con.commit()
                        return self._json({"version": ver + 1})
                except Exception as exc:   # noqa: BLE001
                    return self._error(exc, 500)
            return self._post_rest()

        def _post_rest(self):
            url = urllib.parse.urlparse(self.path)
            try:
                if url.path == "/api/card":
                    data = self._body()
                    card_id = db.save_card(con, data)
                    if "sales" in data:
                        db.replace_sales(con, card_id, data["sales"])
                    return self._json({"id": card_id})

                if url.path == "/api/sync":
                    summary = cardmarket.sync_folder(con, config.get("data_dir", "data"))
                    api = api_client()
                    if api.configured:
                        summary["live"] = self._refresh_linked(api)
                    return self._json(summary)

                if url.path == "/api/live":
                    data = self._body()
                    return self._json(api_client().cheapest(int(data["id_product"])) or {})

                return self._error("Ruta desconocida", 404)
            except Exception as exc:  # noqa: BLE001
                return self._error(exc, 500)

        def _refresh_linked(self, api):
            """Refresca por API las cartas enlazadas, para no depender del fichero diario."""
            import datetime
            today = datetime.date.today().isoformat()
            ids = [r["id_product"] for r in con.execute(
                "SELECT DISTINCT id_product FROM cards WHERE id_product IS NOT NULL")]
            rows, fails = [], 0
            for pid in ids:
                try:
                    guide = (api.product(pid) or {}).get("priceGuide") or {}
                    if guide:
                        rows.append({
                            "id_product": pid, "low": guide.get("LOW"),
                            "trend": guide.get("TREND"), "avg": guide.get("AVG"),
                            "avg1": guide.get("AVG1"), "avg7": guide.get("AVG7"),
                            "avg30": guide.get("AVG30"),
                        })
                except Exception:  # noqa: BLE001
                    fails += 1
            if rows:
                db.upsert_prices(con, rows, today)
            return {"refreshed": len(rows), "failed": fails}

        # -------------------------------------------------- DELETE
        def do_DELETE(self):
            url = urllib.parse.urlparse(self.path)
            try:
                if url.path.startswith("/api/card/"):
                    db.delete_card(con, int(url.path.rsplit("/", 1)[-1]))
                    return self._json({"ok": True})
                return self._error("Ruta desconocida", 404)
            except Exception as exc:  # noqa: BLE001
                return self._error(exc, 500)

    return Handler


def serve(con, config, host="127.0.0.1", port=8765):
    return ThreadingHTTPServer((host, port), make_handler(con, config))
