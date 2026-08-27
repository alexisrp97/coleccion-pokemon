"""Fondos de cada sección.

Tres capas, de más a menos concreta:

1. TUS IMÁGENES. Todo lo que dejes en art/<categoria>/ se usa como fondo de
   esa sección: art/futbol/, art/basquet/, art/beisbol/, art/onepiece/,
   art/pokemon/. Sirven jpg, png y webp. Se sirven desde tu propio disco.

2. POKÉMON AUTOMÁTICO. `python3 tcg.py art` descarga la ilustración oficial
   de los Pokémon más conocidos desde PokéAPI, que es pública y gratuita y no
   pide clave. Sólo existe equivalente para Pokémon: no hay ninguna fuente
   libre de fotos de futbolistas, jugadores de la NBA o de la MLB, porque son
   imágenes con derechos de autor y derechos de imagen. Para esas secciones,
   pon tú las que quieras usar (escaneos de tus propias cartas, por ejemplo)
   en su carpeta.

3. MOTIVO DIBUJADO. Si una sección no tiene imágenes, se dibuja un patrón
   propio en SVG: las líneas de un campo, la duela de una pista, las costuras
   de una pelota de béisbol, el oleaje. Así la app nunca se queda sin
   escenario.
"""

import json
import os
import urllib.parse
import urllib.request

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

CATEGORIES = ["pokemon", "onepiece", "futbol", "basquet", "beisbol"]

# Paleta por sección: el fieltro de fondo se mantiene, cambia el acento.
PALETTES = {
    "pokemon":  {"accent": "#f2b705", "deep": "#0e2a21", "glow": "#1d4a33"},
    "onepiece": {"accent": "#d94f3d", "deep": "#0b2233", "glow": "#123c56"},
    "futbol":   {"accent": "#5fbf8a", "deep": "#0c2718", "glow": "#154227"},
    "basquet":  {"accent": "#e08a3c", "deep": "#2a1a10", "glow": "#4a2c17"},
    "beisbol":  {"accent": "#c9553f", "deep": "#241612", "glow": "#43261e"},
    "all":      {"accent": "#c9a227", "deep": "#0d2a21", "glow": "#17402f"},
}

FAMOUS_POKEMON = [
    "pikachu", "charizard", "mewtwo", "mew", "eevee", "snorlax", "gengar",
    "lucario", "gyarados", "dragonite", "blastoise", "venusaur", "umbreon",
    "rayquaza", "greninja", "sylveon", "arcanine", "tyranitar",
]

POKEAPI = "https://pokeapi.co/api/v2/pokemon/"


# ---------------------------------------------------------------- carpetas

def art_dir(base):
    return os.path.join(base, "art")


def ensure_dirs(base):
    for cat in CATEGORIES:
        os.makedirs(os.path.join(art_dir(base), cat), exist_ok=True)
    return art_dir(base)


def images_for(base, category):
    folder = os.path.join(art_dir(base), category)
    if not os.path.isdir(folder):
        return []
    files = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith(EXTS) and not f.startswith("."))
    return [f"/art/{category}/{urllib.parse.quote(f)}" for f in files]


# ---------------------------------------------------------------- PokéAPI

def fetch_pokemon(base, names=None, timeout=20, log=print):
    """Descarga la ilustración oficial de cada Pokémon en art/pokemon/."""
    names = names or FAMOUS_POKEMON
    folder = os.path.join(ensure_dirs(base), "pokemon")
    got = 0
    for name in names:
        dest = os.path.join(folder, f"{name}.png")
        if os.path.exists(dest):
            log(f"  {name}: ya estaba")
            got += 1
            continue
        try:
            with urllib.request.urlopen(POKEAPI + name, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            url = (data.get("sprites", {}).get("other", {})
                       .get("official-artwork", {}).get("front_default"))
            if not url:
                log(f"  {name}: sin ilustración oficial")
                continue
            with urllib.request.urlopen(url, timeout=timeout) as r:
                blob = r.read()
            with open(dest, "wb") as fh:
                fh.write(blob)
            got += 1
            log(f"  {name}: {len(blob)//1024} kB")
        except Exception as exc:  # noqa: BLE001
            log(f"  {name}: {exc}")
    return got


# ---------------------------------------------------------------- fotos de cartas

CARD_DIR = "cards"
PROXY = "https://images.weserv.nl/?url={}&w=500"


def card_image_path(base, card):
    """Ruta local donde vive la foto de una carta."""
    key = card.get("ptcg_id") or (card.get("id_product") and f"cm{card['id_product']}")
    if not key:
        return None
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(key))
    return os.path.join(art_dir(base), CARD_DIR, safe + ".jpg")


def fetch_card_image(base, url, dest, timeout=20):
    """Descarga la imagen; si el sitio la rechaza, la pide por el servicio de imágenes."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for candidate in (url, PROXY.format(urllib.parse.quote(url.split("//", 1)[-1], safe=""))):
        try:
            req = urllib.request.Request(candidate, headers={"User-Agent": "coleccion-tcg/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                blob = r.read()
            if len(blob) > 1000:
                with open(dest, "wb") as fh:
                    fh.write(blob)
                return len(blob)
        except Exception:  # noqa: BLE001
            continue
    return 0


# ---------------------------------------------------------------- motivos SVG

def _svg(body, size, color, opacity=0.5):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<g fill="none" stroke="{color}" stroke-opacity="{opacity}" '
            f'stroke-width="2" stroke-linecap="round">{body}</g></svg>')


def motif(category):
    """Patrón que se repite detrás de todo. Dibujado, no descargado."""
    accent = PALETTES.get(category, PALETTES["all"])["accent"]

    if category == "futbol":
        # líneas de campo: área, círculo central y bandas de siega
        body = ('<rect x="20" y="20" width="200" height="200" rx="2"/>'
                '<circle cx="120" cy="120" r="46"/><path d="M120 20v200"/>'
                '<path d="M20 76h44v88H20M220 76h-44v88h44"/>')
        return _svg(body, 240, accent, 0.35)

    if category == "basquet":
        # arco de triple y costuras de balón
        body = ('<path d="M0 30h240"/><path d="M60 30v70a60 60 0 0 0 120 0V30"/>'
                '<circle cx="120" cy="170" r="42"/><path d="M78 170h84M120 128v84"/>'
                '<path d="M92 138q28 32 0 64M148 138q-28 32 0 64"/>')
        return _svg(body, 240, accent, 0.32)

    if category == "beisbol":
        # costura doble de la pelota, repetida en diagonal
        body = ('<path d="M0 60q60 60 120 0t120 0"/>'
                '<path d="M0 180q60 60 120 0t120 0"/>'
                '<g stroke-width="3">'
                '<path d="M40 66l-8 12M80 76l-6 14M160 76l6 14M200 66l8 12"/>'
                '<path d="M40 186l-8 12M80 196l-6 14M160 196l6 14M200 186l8 12"/></g>')
        return _svg(body, 240, accent, 0.3)

    if category == "onepiece":
        # oleaje y rosa de los vientos
        body = ('<path d="M0 70q30 -22 60 0t60 0 60 0 60 0"/>'
                '<path d="M0 130q30 -22 60 0t60 0 60 0 60 0"/>'
                '<path d="M0 190q30 -22 60 0t60 0 60 0 60 0"/>'
                '<g stroke-width="1.5"><circle cx="120" cy="30" r="18"/>'
                '<path d="M120 8v44M98 30h44M105 15l30 30M135 15l-30 30"/></g>')
        return _svg(body, 240, accent, 0.3)

    # pokemon y "todo": hierba alta
    body = ('<path d="M20 220q6-46 22-64M40 220q-4-40 8-62M60 220q10-44 26-58"/>'
            '<path d="M140 220q6-46 22-64M160 220q-4-40 8-62M180 220q10-44 26-58"/>'
            '<path d="M80 120q6-40 22-56M100 120q-4-36 8-54"/>')
    return _svg(body, 240, accent, 0.28)
