"""Capa de base de datos: SQLite, sin dependencias externas."""

import sqlite3
import os
import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    category         TEXT NOT NULL DEFAULT 'pokemon',
    collection       TEXT NOT NULL DEFAULT '',
    name             TEXT NOT NULL,
    number           TEXT DEFAULT '',
    rarity           TEXT DEFAULT '',
    lang             TEXT DEFAULT 'ES',
    quantity         INTEGER NOT NULL DEFAULT 1,
    condition        TEXT DEFAULT 'NM',
    graded           INTEGER NOT NULL DEFAULT 0,
    grader           TEXT DEFAULT 'PSA',
    grade            TEXT DEFAULT '',
    cert             TEXT DEFAULT '',
    pop_grade        INTEGER,
    pop_total        INTEGER,
    purchase         REAL,
    purchase_date    TEXT DEFAULT '',
    id_product       INTEGER,              -- idProduct de Cardmarket
    grade_multiplier REAL NOT NULL DEFAULT 1.0,
    manual_price     REAL,                 -- precio fijado a mano; manda sobre todo
    url              TEXT DEFAULT '',
    notes            TEXT DEFAULT '',
    created_at       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sales (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id  INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    price    REAL NOT NULL,
    date     TEXT DEFAULT '',
    source   TEXT DEFAULT 'manual',
    note     TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sales_card ON sales(card_id);

-- Catálogo de productos de Cardmarket (fichero de catálogo descargado)
CREATE TABLE IF NOT EXISTS cm_products (
    id_product   INTEGER PRIMARY KEY,
    name         TEXT DEFAULT '',
    expansion    TEXT DEFAULT '',
    category     TEXT DEFAULT '',
    game         TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_cm_name ON cm_products(name);

-- Una fila por producto y día: así se construye el historial de ventas propio
CREATE TABLE IF NOT EXISTS cm_prices (
    id_product    INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    low           REAL, trend REAL, avg REAL,
    avg1          REAL, avg7 REAL, avg30 REAL,
    PRIMARY KEY (id_product, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_cmp_prod ON cm_prices(id_product, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

CARD_FIELDS = [
    "category", "collection", "name", "number", "rarity", "lang", "quantity",
    "condition", "graded", "grader", "grade", "cert", "pop_grade", "pop_total",
    "purchase", "purchase_date", "id_product", "grade_multiplier", "manual_price",
    "url", "notes",
]


def connect(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con


# ---------------------------------------------------------------- cartas

def all_cards(con):
    return [dict(r) for r in con.execute("SELECT * FROM cards ORDER BY id")]


def get_card(con, card_id):
    r = con.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    return dict(r) if r else None


def save_card(con, data):
    """Inserta o actualiza. Devuelve el id."""
    values = {k: data.get(k) for k in CARD_FIELDS}
    values["name"] = (values.get("name") or "").strip()
    if not values["name"]:
        raise ValueError("La carta necesita un nombre.")
    values["quantity"] = int(values.get("quantity") or 1)
    values["graded"] = 1 if values.get("graded") else 0
    values["grade_multiplier"] = float(values.get("grade_multiplier") or 1.0)
    for k in ("pop_grade", "pop_total", "id_product"):
        values[k] = int(values[k]) if str(values.get(k) or "").strip() else None
    for k in ("purchase", "manual_price"):
        values[k] = float(values[k]) if str(values.get(k) or "").strip() else None
    for k in ("collection", "number", "rarity", "lang", "condition", "grader",
              "grade", "cert", "url", "notes", "purchase_date", "category"):
        values[k] = (values.get(k) or "")

    cid = data.get("id")
    if cid:
        sets = ", ".join(f"{k} = :{k}" for k in CARD_FIELDS)
        values["id"] = int(cid)
        con.execute(f"UPDATE cards SET {sets} WHERE id = :id", values)
    else:
        values["created_at"] = datetime.date.today().isoformat()
        cols = CARD_FIELDS + ["created_at"]
        cur = con.execute(
            f"INSERT INTO cards ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})",
            values,
        )
        cid = cur.lastrowid
    con.commit()
    return int(cid)


def delete_card(con, card_id):
    con.execute("DELETE FROM sales WHERE card_id = ?", (card_id,))
    con.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    con.commit()


# ---------------------------------------------------------------- ventas manuales

def sales_for(con, card_id, limit=5):
    rows = con.execute(
        "SELECT * FROM sales WHERE card_id = ? ORDER BY date DESC, id DESC LIMIT ?",
        (card_id, limit),
    )
    return [dict(r) for r in rows]


def replace_sales(con, card_id, sales):
    con.execute("DELETE FROM sales WHERE card_id = ?", (card_id,))
    for s in sales or []:
        price = str(s.get("price", "")).replace(",", ".").strip()
        if not price:
            continue
        try:
            price = float(price)
        except ValueError:
            continue
        con.execute(
            "INSERT INTO sales (card_id, price, date, source, note) VALUES (?,?,?,?,?)",
            (card_id, price, s.get("date") or "", s.get("source") or "manual", s.get("note") or ""),
        )
    con.commit()


# ---------------------------------------------------------------- precios Cardmarket

def latest_price(con, id_product):
    if not id_product:
        return None
    r = con.execute(
        "SELECT * FROM cm_prices WHERE id_product = ? ORDER BY snapshot_date DESC LIMIT 1",
        (id_product,),
    ).fetchone()
    return dict(r) if r else None


def price_history(con, id_product, limit=30):
    if not id_product:
        return []
    rows = con.execute(
        "SELECT * FROM cm_prices WHERE id_product = ? ORDER BY snapshot_date DESC LIMIT ?",
        (id_product, limit),
    )
    return [dict(r) for r in rows]


def upsert_prices(con, rows, snapshot_date):
    """rows: iterable de dicts con id_product y campos de precio."""
    n = 0
    con.executemany(
        """INSERT INTO cm_prices (id_product, snapshot_date, low, trend, avg, avg1, avg7, avg30)
           VALUES (:id_product, :snapshot_date, :low, :trend, :avg, :avg1, :avg7, :avg30)
           ON CONFLICT(id_product, snapshot_date) DO UPDATE SET
             low=excluded.low, trend=excluded.trend, avg=excluded.avg,
             avg1=excluded.avg1, avg7=excluded.avg7, avg30=excluded.avg30""",
        [dict(r, snapshot_date=snapshot_date) for r in rows],
    )
    n = con.total_changes
    con.commit()
    return n


def upsert_products(con, rows):
    con.executemany(
        """INSERT INTO cm_products (id_product, name, expansion, category, game)
           VALUES (:id_product, :name, :expansion, :category, :game)
           ON CONFLICT(id_product) DO UPDATE SET
             name=excluded.name, expansion=excluded.expansion,
             category=excluded.category, game=excluded.game""",
        list(rows),
    )
    con.commit()


def search_products(con, q, limit=25):
    like = f"%{q.strip()}%"
    rows = con.execute(
        """SELECT p.*, (SELECT trend FROM cm_prices c WHERE c.id_product = p.id_product
                        ORDER BY snapshot_date DESC LIMIT 1) AS trend
           FROM cm_products p WHERE p.name LIKE ? ORDER BY length(p.name) LIMIT ?""",
        (like, limit),
    )
    return [dict(r) for r in rows]


def ensure_users(con):
    # primero la tabla (con TODAS las columnas actuales, por si nace de cero);
    # las ALTER de después son sólo para bases antiguas que ya existían sin ellas.
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL, hash TEXT NOT NULL, created TEXT NOT NULL,
        email TEXT, public INTEGER DEFAULT 0, premium INTEGER DEFAULT 0,
        stripe_customer TEXT, email_ok INTEGER DEFAULT 0, push_sub TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS tokens(
        token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created TEXT NOT NULL)""")
    con.commit()
    for cambio in ("ALTER TABLE users ADD COLUMN email TEXT",
                   "ALTER TABLE users ADD COLUMN public INTEGER DEFAULT 0",
                   "ALTER TABLE users ADD COLUMN premium INTEGER DEFAULT 0",
                   "ALTER TABLE users ADD COLUMN stripe_customer TEXT",
                   "ALTER TABLE users ADD COLUMN email_ok INTEGER DEFAULT 0",
                   "ALTER TABLE users ADD COLUMN push_sub TEXT"):
        try:
            con.execute(cambio)
            con.commit()
        except Exception:
            pass


def set_meta(con, key, value):
    con.execute(
        "INSERT INTO meta (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    con.commit()


def get_meta(con, key, default=None):
    r = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return r["value"] if r else default
