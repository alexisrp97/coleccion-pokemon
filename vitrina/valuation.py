"""Cálculo de valor, tendencia y avisos de cada carta."""

from . import db, search as search_mod

BASES = ["avg7", "trend", "avg1", "avg30", "avg", "low"]

CATEGORIES = {
    "pokemon": "Pokémon",
    "onepiece": "One Piece",
    "futbol": "Fútbol",
    "basquet": "Básquet",
    "beisbol": "Béisbol",
}

# Cardmarket sólo cubre juegos de cartas coleccionables, no cromos deportivos.
CM_CATEGORIES = {"pokemon", "onepiece"}


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def manual_sales_avg(sales):
    vals = [_f(s["price"]) for s in sales]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def daily_sales_series(history, limit=5):
    """Las últimas medias diarias de venta (AVG1) que hemos ido guardando.

    Cardmarket no publica ventas individuales; AVG1 es el precio medio de las
    unidades vendidas ese día, así que la serie diaria es lo más parecido a un
    histórico de ventas reales.
    """
    out = []
    for row in history:
        v = _f(row.get("avg1")) or _f(row.get("trend"))
        if v is not None:
            out.append({"date": row["snapshot_date"], "price": v})
        if len(out) >= limit:
            break
    return out


def unit_value(card, price_row, sales, basis="avg7"):
    """Valor unitario y de dónde sale."""
    if card.get("manual_price") is not None:
        return _f(card["manual_price"]), "manual"

    if price_row:
        v = _f(price_row.get(basis))
        if v is None:  # si falta la base elegida, cae a la siguiente disponible
            for b in BASES:
                v = _f(price_row.get(b))
                if v is not None:
                    basis = b
                    break
        if v is not None:
            mult = _f(card.get("grade_multiplier")) or 1.0
            return v * mult, f"cardmarket:{basis}" + ("" if mult == 1.0 else f" x{mult:g}")

    avg = manual_sales_avg(sales)
    if avg is not None:
        return avg, "ventas propias"
    return 0.0, "sin datos"


def trend_pct(series):
    """Compara las 2 lecturas más recientes con las anteriores."""
    if len(series) < 3:
        return None
    recent = series[:2]
    older = series[2:]
    a = sum(s["price"] for s in recent) / len(recent)
    b = sum(s["price"] for s in older) / len(older)
    if not b:
        return None
    return (a - b) / b * 100


def flags(card, price_row, series, unit):
    out = []
    pg, pt = card.get("pop_grade"), card.get("pop_total")

    if card.get("graded") and pg:
        if pg <= 10:
            out.append({"t": f"POP {pg}", "tone": "hot"})
        elif pg <= 50:
            out.append({"t": f"POP bajo · {pg}", "tone": "hot"})
        elif pg <= 250:
            out.append({"t": f"POP contenido · {pg}", "tone": "warm"})
        if pt:
            share = pg / pt * 100
            if share <= 5:
                out.append({"t": f"Sólo {share:.1f}% en esta nota", "tone": "warm"})

    tr = trend_pct(series)
    if tr is not None and abs(tr) >= 8:
        out.append({"t": f"{'▲' if tr > 0 else '▼'} {abs(tr):.0f}% reciente",
                    "tone": "up" if tr > 0 else "down"})

    if price_row:
        low, trend = _f(price_row.get("low")), _f(price_row.get("trend"))
        if low and trend and trend / low >= 2.2:
            out.append({"t": "Hay copias muy por debajo del trend", "tone": "warm"})

    p = _f(card.get("purchase"))
    if p and unit:
        d = (unit - p) / p * 100
        out.append({"t": f"{'+' if d >= 0 else ''}{d:.0f}% sobre compra",
                    "tone": "up" if d >= 0 else "down"})

    if card.get("category") in CM_CATEGORIES and not card.get("id_product"):
        out.append({"t": "Sin enlazar a Cardmarket", "tone": "mute"})
    return out


def evaluate(con, card, basis="avg7"):
    """Devuelve el dict de la carta con todo lo calculado."""
    price_row = db.latest_price(con, card.get("id_product"))
    history = db.price_history(con, card.get("id_product"), limit=40)
    manual = db.sales_for(con, card["id"], limit=5)

    series = daily_sales_series(history, limit=5)
    if not series and manual:
        series = [{"date": s["date"], "price": s["price"]} for s in manual]

    unit, source = unit_value(card, price_row, manual, basis)
    qty = int(card.get("quantity") or 1)

    out = dict(card)
    out.update({
        "deltas": search_mod.deltas(con, card.get("id_product")),
        "unit_value": round(unit, 2),
        "total_value": round(unit * qty, 2),
        "value_source": source,
        "price_row": price_row,
        "series": series,
        "manual_sales": manual,
        "trend_pct": trend_pct(series),
        "flags": flags(card, price_row, series, unit),
    })
    return out


def portfolio(con, basis="avg7"):
    cards = [evaluate(con, c, basis) for c in db.all_cards(con)]
    total = sum(c["total_value"] for c in cards)
    invested = sum((c["purchase"] or 0) * (c["quantity"] or 1) for c in cards)
    by_cat = {}
    for c in cards:
        k = c["category"]
        e = by_cat.setdefault(k, {"id": k, "label": CATEGORIES.get(k, k), "n": 0, "value": 0.0})
        e["n"] += 1
        e["value"] = round(e["value"] + c["total_value"], 2)
    return {
        "cards": cards,
        "total": round(total, 2),
        "invested": round(invested, 2),
        "profit": round(total - invested, 2),
        "units": sum(int(c["quantity"] or 1) for c in cards),
        "by_category": list(by_cat.values()),
        "basis": basis,
    }
