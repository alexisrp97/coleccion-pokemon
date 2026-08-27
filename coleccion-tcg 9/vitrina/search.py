"""Buscador único: catálogo local + API de Cardmarket en la misma lista.

Cuando escribes el nombre de una carta, se consultan a la vez:

  · el catálogo descargado de Cardmarket (instantáneo, funciona sin conexión)
  · la API de Cardmarket, si has puesto credenciales (autoritativo y al día)
  · tus propias cartas ya registradas (para no duplicar nombres)

Los resultados se juntan y se quitan duplicados por idProduct. Al elegir uno,
la carta queda enlazada a ese idProduct: es lo que permite comparar su precio
real todos los días, porque a partir de ahí cada sincronización guarda una
línea nueva de precio para ese producto exacto.
"""

import datetime

from . import db

GAME_HINT = {"pokemon": ("pokemon", "pokémon"), "onepiece": ("one piece", "onepiece")}


def _score(name, q):
    """Cuanto más se parezca al principio del nombre, más arriba."""
    n, ql = name.lower(), q.lower()
    if n == ql:
        return 0
    if n.startswith(ql):
        return 1
    if ql in n:
        return 2
    return 3


def _from_api_product(p):
    """Normaliza un producto tal y como lo devuelve la API 2.0."""
    exp = p.get("expansion")
    if isinstance(exp, dict):
        exp = exp.get("enName") or exp.get("name")
    guide = p.get("priceGuide") or {}
    return {
        "id_product": int(p.get("idProduct")),
        "name": (p.get("enName") or p.get("name") or "").strip(),
        "expansion": (exp or p.get("expansionName") or "").strip(),
        "number": str(p.get("number") or ""),
        "rarity": (p.get("rarity") or ""),
        "category": (p.get("categoryName") or ""),
        "game": "",
        "low": guide.get("LOW") or guide.get("LOWEX"),
        "trend": guide.get("TREND"),
        "avg7": guide.get("AVG7"),
        "avg1": guide.get("AVG1"),
        "avg30": guide.get("AVG30"),
        "avg": guide.get("AVG"),
        "origin": "api",
    }


def search(con, q, category=None, api=None, limit=20):
    """Devuelve resultados mezclados y una nota de qué fuentes respondieron."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"results": [], "sources": [], "notes": []}

    results, seen, sources, notes = [], set(), [], []

    # --- catálogo local ---------------------------------------------------
    local = db.search_products(con, q, limit=60)
    if local:
        sources.append("catálogo local")
    hint = GAME_HINT.get(category or "")
    for p in local:
        if hint and p.get("category") and not any(h in p["category"].lower() for h in hint):
            if not any(h in (p.get("game") or "").lower() for h in hint):
                continue
        row = db.latest_price(con, p["id_product"]) or {}
        results.append({
            "id_product": p["id_product"], "name": p["name"],
            "expansion": p.get("expansion") or p.get("game") or "",
            "number": "", "rarity": "", "category": p.get("category") or "",
            "low": row.get("low"), "trend": row.get("trend"), "avg7": row.get("avg7"),
            "avg1": row.get("avg1"), "avg30": row.get("avg30"),
            "snapshot_date": row.get("snapshot_date"),
            "origin": "catálogo",
        })
        seen.add(p["id_product"])
    if not local:
        notes.append("El catálogo local está vacío: descarga el fichero de productos y sincroniza.")

    # --- API en vivo ------------------------------------------------------
    if api is not None and getattr(api, "configured", False):
        try:
            found = api.find_products(q)
            sources.append("API de Cardmarket")
            today = datetime.date.today().isoformat()
            fresh = []
            for p in found[:40]:
                try:
                    item = _from_api_product(p)
                except (TypeError, ValueError):
                    continue
                if not item["id_product"]:
                    continue
                # se cachea lo que llega, así el precio ya queda registrado hoy
                if any(item.get(k) is not None for k in ("low", "trend", "avg7")):
                    fresh.append({
                        "id_product": item["id_product"], "low": item["low"],
                        "trend": item["trend"], "avg": item["avg"], "avg1": item["avg1"],
                        "avg7": item["avg7"], "avg30": item["avg30"],
                    })
                if item["id_product"] in seen:
                    for r in results:  # completa lo que el catálogo no trae
                        if r["id_product"] == item["id_product"]:
                            r["number"] = r["number"] or item["number"]
                            r["rarity"] = r["rarity"] or item["rarity"]
                            r["origin"] = "catálogo + API"
                            for k in ("low", "trend", "avg7", "avg1", "avg30"):
                                if item.get(k) is not None:
                                    r[k] = item[k]
                                    r["snapshot_date"] = today
                    continue
                item["snapshot_date"] = today
                results.append(item)
                seen.add(item["id_product"])
            if fresh:
                db.upsert_products(con, [{
                    "id_product": r["id_product"], "name": r["name"],
                    "expansion": r["expansion"], "category": r["category"], "game": "",
                } for r in results if r["id_product"] in {f["id_product"] for f in fresh}])
                db.upsert_prices(con, fresh, today)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"La API de Cardmarket no respondió: {exc}")
    elif category in ("pokemon", "onepiece"):
        notes.append("Sin credenciales de Cardmarket: se busca sólo en el catálogo descargado.")

    # --- tus propias cartas ----------------------------------------------
    mine = con.execute(
        """SELECT id, name, collection, number, rarity, id_product, category
           FROM cards WHERE name LIKE ? ORDER BY name LIMIT 10""", (f"%{q}%",)
    ).fetchall()
    for m in mine:
        results.append({
            "id_product": m["id_product"], "name": m["name"],
            "expansion": m["collection"], "number": m["number"] or "",
            "rarity": m["rarity"] or "", "category": m["category"],
            "origin": "ya en tu colección", "card_id": m["id"],
        })
    if mine:
        sources.append("tu colección")

    results.sort(key=lambda r: (_score(r["name"], q), len(r["name"])))
    return {"results": results[:limit], "sources": sources, "notes": notes}


def deltas(con, id_product):
    """Variación del precio real frente a ayer, hace 7 y hace 30 días."""
    hist = db.price_history(con, id_product, limit=60)
    if not hist:
        return None

    def val(row):
        for k in ("avg1", "trend", "avg7", "avg"):
            if row.get(k) is not None:
                return float(row[k])
        return None

    series = [(r["snapshot_date"], val(r)) for r in hist]
    series = [(d, v) for d, v in series if v is not None]
    if not series:
        return None

    today_date, today_val = series[0]
    out = {"date": today_date, "value": round(today_val, 2)}
    for label, idx in (("d1", 1), ("d7", 7), ("d30", 30)):
        if len(series) > idx:
            past = series[idx][1]
            if past:
                out[label] = round((today_val - past) / past * 100, 1)
                out[label + "_value"] = round(past, 2)
    out["points"] = len(series)
    return out
