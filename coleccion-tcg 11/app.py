#!/usr/bin/env python3
"""Colección TCG — inventario local con precios de Cardmarket.

Uso rápido:
    python3 tcg.py                 abre la vitrina en el navegador
    python3 tcg.py sync            importa los ficheros de data/
    python3 tcg.py list            lista la colección en el terminal
    python3 tcg.py total           sólo el valor total
    python3 tcg.py export cartas.csv
"""

import argparse
import csv
import json
import os
import sys
import threading
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from vitrina import art, cardmarket, db, server, valuation  # noqa: E402

DEFAULTS = {
    "base_dir": BASE_DIR,
    "db_path": os.path.join(BASE_DIR, "coleccion.db"),
    "data_dir": os.path.join(BASE_DIR, "data"),
    "basis": "avg7",
    "port": 8765,
    "app_token": "", "app_secret": "", "access_token": "", "access_secret": "",
    "psa_token": "",
}


def load_config():
    cfg = dict(DEFAULTS)
    path = os.path.join(BASE_DIR, "config.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    return cfg


def lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def cmd_serve(con, cfg, args):
    port = int(args.port or cfg["port"])
    host = "127.0.0.1" if args.solo else "0.0.0.0"
    cfg = dict(cfg); cfg["cuentas"] = bool(args.cuentas)
    httpd = server.serve(con, cfg, host=host, port=port)
    url = f"http://127.0.0.1:{port}/"
    print(f"collector.app en {url}   (Ctrl+C para parar)")
    if host == "0.0.0.0":
        ip = lan_ip()
        if ip:
            print(f"Desde el móvil u otro ordenador de la misma wifi:  http://{ip}:{port}/")
        if cfg.get("cuentas"):
            print("Modo CUENTAS: cada persona se registra y tiene su propia colección.")
        else:
            print("La base de datos es compartida: lo que añada cada uno lo ven todos.")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")


def cmd_art(con, cfg, args):
    art.ensure_dirs(cfg["base_dir"])
    if args.category and args.category != "pokemon":
        folder = os.path.join(art.art_dir(cfg["base_dir"]), args.category)
        print(f"Sólo Pokémon tiene descarga automática (PokéAPI).")
        print(f"Para {args.category}, deja tus imágenes en {folder}")
        return
    print("Descargando ilustraciones oficiales desde PokéAPI…")
    n = art.fetch_pokemon(cfg["base_dir"], args.names or None)
    print(f"{n} imágenes listas en art/pokemon/")


def cmd_importar(con, cfg, args):
    """Mete en la base de datos una copia .json de la app del navegador."""
    with open(args.path, encoding="utf-8") as fh:
        data = json.load(fh)
    payload = data.get("db", data)
    cards = payload.get("cards", [])
    hist = payload.get("history", {})
    n = 0
    for c in cards:
        c = dict(c)
        c.pop("id", None)
        c.pop("photo", None)
        c.pop("cache", None)
        sales = c.pop("sales", [])
        try:
            cid = db.save_card(con, c)
        except ValueError:
            continue
        if sales:
            db.replace_sales(con, cid, sales)
        n += 1
    rows = 0
    for key, series in hist.items():
        if key.startswith("ptcg:"):
            continue
        try:
            pid = int(key)
        except ValueError:
            continue
        for r in series:
            db.upsert_prices(con, [{
                "id_product": pid, "low": r.get("low"), "trend": r.get("trend"),
                "avg": r.get("avg"), "avg1": r.get("avg1"),
                "avg7": r.get("avg7"), "avg30": r.get("avg30"),
            }], r.get("d") or "")
            rows += 1
    print(f"{n} cartas y {rows} precios importados desde {args.path}")


def cmd_fotos(con, cfg, args):
    """Descarga al disco la foto de cada carta enlazada."""
    cards = db.all_cards(con)
    todo = [c for c in cards if c.get("url") or c.get("ptcg_id") or c.get("id_product")]
    if not todo:
        print("No hay cartas enlazadas a ningún catálogo todavía.")
        return
    ok = 0
    for c in todo:
        dest = art.card_image_path(cfg["base_dir"], c)
        if not dest:
            continue
        if os.path.exists(dest) and not args.force:
            ok += 1
            continue
        url = c.get("image") or ""
        if not url and c.get("ptcg_id"):
            url = f"https://images.pokemontcg.io/{c['ptcg_id'].rsplit('-', 1)[0]}/{c['ptcg_id'].rsplit('-', 1)[1]}.png"
        if not url:
            print(f"  {c['name']}: sin imagen conocida")
            continue
        n = art.fetch_card_image(cfg["base_dir"], url, dest)
        print(f"  {c['name']}: {'%d kB' % (n // 1024) if n else 'no se pudo'}")
        ok += 1 if n else 0
    print(f"{ok} fotos en art/{art.CARD_DIR}/")


def cmd_sync(con, cfg, args):
    s = cardmarket.sync_folder(con, cfg["data_dir"])
    for line in s["files"]:
        print(" ", line)
    for line in s["errors"]:
        print("  aviso:", line)
    print(f"{s['prices']} precios · {s['products']} productos")


def cmd_list(con, cfg, args):
    p = valuation.portfolio(con, cfg["basis"])
    for c in sorted(p["cards"], key=lambda c: -c["total_value"]):
        grade = f"{c['grader']} {c['grade']}" if c["graded"] else c["condition"]
        print(f"{c['total_value']:>10.2f} €  {c['name'][:34]:<34} {c['collection'][:22]:<22} "
              f"{grade:<8} x{c['quantity']}")
    print("-" * 92)
    print(f"{p['total']:>10.2f} €  TOTAL ({p['units']} unidades, base {p['basis']})")


def cmd_total(con, cfg, args):
    print(f"{valuation.portfolio(con, cfg['basis'])['total']:.2f} €")


def cmd_export(con, cfg, args):
    p = valuation.portfolio(con, cfg["basis"])
    cols = ["category", "collection", "name", "number", "lang", "quantity", "graded",
            "grader", "grade", "cert", "pop_grade", "pop_total", "purchase",
            "unit_value", "total_value", "value_source"]
    with open(args.path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for c in p["cards"]:
            w.writerow(c)
    print(f"{len(p['cards'])} cartas escritas en {args.path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("serve", help="abre la vitrina en el navegador")
    s.add_argument("--port", type=int)
    s.add_argument("--no-browser", action="store_true")
    s.add_argument("--solo", action="store_true", help="sólo este ordenador, sin compartir en la wifi")
    s.add_argument("--cuentas", action="store_true", help="web pública: cada persona con su cuenta y su colección")
    s.set_defaults(fn=cmd_serve)

    a = sub.add_parser("art", help="prepara los fondos de cada sección")
    a.add_argument("category", nargs="?", default="pokemon")
    a.add_argument("names", nargs="*", help="pokémon concretos (por defecto, los más conocidos)")
    a.set_defaults(fn=cmd_art)

    i = sub.add_parser("importar", help="carga una copia .json de la app del navegador")
    i.add_argument("path")
    i.set_defaults(fn=cmd_importar)

    f = sub.add_parser("fotos", help="descarga al disco la foto de tus cartas")
    f.add_argument("--force", action="store_true", help="vuelve a bajar las que ya estén")
    f.set_defaults(fn=cmd_fotos)

    sub.add_parser("sync", help="importa los ficheros de data/").set_defaults(fn=cmd_sync)
    sub.add_parser("list", help="lista la colección").set_defaults(fn=cmd_list)
    sub.add_parser("total", help="valor total").set_defaults(fn=cmd_total)

    e = sub.add_parser("export", help="exporta a CSV")
    e.add_argument("path")
    e.set_defaults(fn=cmd_export)

    args = ap.parse_args()
    cfg = load_config()
    con = db.connect(cfg["db_path"])

    if not args.cmd:
        args.port, args.no_browser = None, False
        return cmd_serve(con, cfg, args)
    args.fn(con, cfg, args)


if __name__ == "__main__":
    main()
