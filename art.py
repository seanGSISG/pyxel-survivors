"""Sprite rendering with interchangeable art sets.

"wiki":  the real Vampire Survivors sprites, packed by tools/build_atlas.py
         into wiki/atlas (personal local use; never committed).
"90s":   original generated 90s-theme sprites, packed by tools/sprite_gen/
         build_theme.py into themes/nineties (same atlas format, committed).
"pixel": the code-generated 16-colour art in sprites.py / icons.py (2x scale).

The wiki set is used when its atlas exists, unless the config asks otherwise.
Every draw call is centred on (x, y) and falls back to pixel art per key.
"""

import json
import pathlib

import pyxel

import icons
import sprites

ATLAS = pathlib.Path(__file__).parent / "wiki" / "atlas"
ATLASES = {"wiki": ATLAS, "90s": pathlib.Path(__file__).parent / "themes" / "nineties"}
KEYCOL = 21  # palette index reserved as the atlas transparency key
PIXEL_SCALE = 2

MODE = "pixel"
_pages, _sil, _index = [], [], {}
_names = {}  # themed display text from the atlas set's optional names.json
_body = {}  # key -> (w, h) of the character, where frames are padded for movement

# Pixel-art stand-ins for wiki enemies, chosen by keywords in the enemy id.
_ENEMY_FALLBACK = [
    ("reaper", "reaper", {}), ("bat", "bat", {}), ("pipeestrello", "bat", {}),
    ("skelewing", "bat", {2: 7}), ("harpy", "bat", {2: 9}), ("ghost", "ghost", {}),
    ("skull", "ghost", {6: 7}), ("medusa", "ghost", {6: 11}), ("sneaky", "ghost", {6: 11}),
    ("mudman", "mud", {}), ("golem", "mud", {4: 13}), ("elemental", "mud", {4: 6}),
    ("werewolf", "wolf", {}), ("minotaur", "wolf", {5: 4}), ("demon", "wolf", {5: 8}),
    ("manti", "mant", {}), ("venus", "flower", {}), ("flower", "flower", {}),
    ("zombie", "zomb", {}), ("mummy", "skel", {7: 15, 13: 9}), ("skeleton", "skel", {}),
    ("witch", "zomb", {4: 2, 11: 15}), ("knight", "skel", {7: 13}), ("merman", "zomb", {4: 12}),
    ("reaper_trainee", "reaper", {1: 5}),
]


def available():
    """Art modes this install can load: atlas sets whose atlas exists, then pixel."""
    return [m for m, root in ATLASES.items() if (root / "atlas.json").exists()] + ["pixel"]


def init(prefer="wiki"):
    """Load the atlas into the palette/images if available. Returns the mode.

    "wiki" falls back to the 90s theme when the local wiki atlas is missing
    (every public clone and the web build), then to pixel art.
    """
    global MODE, _index, _names, _body
    MODE, _index, _names, _body = "pixel", {}, {}, {}
    _pages.clear()
    _sil.clear()
    if prefer == "wiki" and "wiki" not in available():
        prefer = "90s"
    root = ATLASES.get(prefer)
    if not root or not (root / "atlas.json").exists():
        return MODE
    meta = root / "atlas.json"
    atlas = json.loads(meta.read_text())
    while len(pyxel.colors) < KEYCOL:
        pyxel.colors.append(0)
    pyxel.colors[KEYCOL:] = [0xFF00FF] + [int(c, 16) for c in atlas["palette"]]
    n = 1 + max(r[0] for rects in atlas["sprites"].values() for r in rects)
    for i in range(n):
        _pages.append(pyxel.Image.from_image(str(root / f"page_{i}.png")))
        _sil.append(pyxel.Image.from_image(str(root / f"page_{i}_s.png")))
    _index = atlas["sprites"]
    _body = atlas.get("body", {})
    if (root / "names.json").exists():
        _names = json.loads((root / "names.json").read_text())
    MODE = prefer
    return MODE


def label(kind, key, field, default):
    """Display text for a gamedata entry: the theme's own if it names one, else `default`."""
    return _names.get(kind, {}).get(key, {}).get(field, default)


def name(kind, spec, field="name"):
    """Themed display name (or other text field) of a gamedata spec."""
    return label(kind, spec["id"], field, spec[field])


def has(key):
    return key in _index


def size(key):
    """(w, h) of a sprite in screen pixels, or None."""
    if key in _body:
        return tuple(_body[key])
    if has(key):
        r = _index[key][0]
        return r[3], r[4]
    return None


def nframes(key):
    return len(_index[key]) if has(key) else 1


def draw(key, x, y, frame=0, flip=False, scale=1.0, rotate=0.0, silhouette=False):
    """Draw an atlas sprite centred on (x, y). Returns False if not in the atlas."""
    if not has(key):
        return False
    rects = _index[key]
    page, u, v, w, h = rects[frame % len(rects)]
    img = (_sil if silhouette else _pages)[page]
    pyxel.blt(x - w / 2, y - h / 2, img, u, v, -w if flip else w, h, KEYCOL, rotate, scale)
    return True


# ------------------------------------------------------------ game objects


def enemy_fallback(eid):
    for word, spr, pal in _ENEMY_FALLBACK:
        if word in eid:
            return spr, pal
    return "skel", {5: 1}


def enemy_size(eid, scale=1.0):
    s = size(f"enemy:{eid}")
    if s:
        return s[0] * scale, s[1] * scale
    return 16 * PIXEL_SCALE * scale, 16 * PIXEL_SCALE * scale


def draw_enemy(eid, x, y, t, flip, scale=1.0, flash=False, frozen=False, pal=None):
    key = f"enemy:{eid}"
    if has(key):
        f = t // 6
        if flash:
            draw(key, x, y, f, flip, scale, silhouette=True)
            return
        draw(key, x, y, f, flip, scale)
        if frozen:
            pyxel.pal(7, 12)
            pyxel.dither(0.5)
            draw(key, x, y, f, flip, scale, silhouette=True)
            pyxel.dither(1.0)
            pyxel.pal()
        return
    spr, fpal = enemy_fallback(eid)
    for a, b in {**fpal, **(pal or {})}.items():
        pyxel.pal(a, b)
    if flash:
        for c in range(1, 16):
            pyxel.pal(c, 7)
    elif frozen:
        for c in range(1, 16):
            pyxel.pal(c, 6 if c in (7, 15, 10, 14, 13) else 12)
    name = "reaper0" if spr == "reaper" else f"{spr}{(t // 8) % 2}"
    sprites.draw(name, x, y, flip=flip, scale=PIXEL_SCALE * scale)
    pyxel.pal()


CHAR_PALS = [{}, {8: 12, 4: 10, 7: 6}, {8: 7, 7: 12, 4: 9}, {8: 5, 7: 6, 4: 1},
             {8: 9, 4: 8}, {8: 3, 4: 10}, {8: 2, 4: 0}, {8: 14, 4: 9}]


def char_pal(cid):
    return CHAR_PALS[sum(map(ord, cid)) % len(CHAR_PALS)] if cid != "antonio_belpaese" else {}


def char_size(cid):
    s = size(f"char:{cid}")
    return s if s else (16 * PIXEL_SCALE, 16 * PIXEL_SCALE)


def draw_char(cid, x, y, moving, t, flip, hurt=False, scale=1.0):
    key = f"char:{cid}"
    if has(key):
        f = (t // 6) if moving else 0
        draw(key, x, y, f, flip, scale, silhouette=hurt)
        return
    for a, b in char_pal(cid).items():
        pyxel.pal(a, b)
    if hurt:
        for c in range(1, 16):
            pyxel.pal(c, 8)
    f = (t // 6) % 2 if moving else 0
    sprites.draw(f"player{f}", x, y, flip=flip, scale=PIXEL_SCALE * scale)
    pyxel.pal()


def icon(key, x, y, scale=1):
    """Item icon (weapon / passive / pickup / arcana) centred on (x, y), ~16 px."""
    for k in (f"wicon:{key}", f"passive:{key}", f"pickup:{key}", f"arcana_icon:{key}"):
        if has(k):
            draw(k, x, y, scale=scale)
            return
    if key in icons.SLOT:
        icons.draw(key, x, y, 2 * scale)
        return
    # generic pixel-mode badge: a tinted gem with the item's initials
    col = (8, 9, 10, 11, 12, 14, 6, 13)[sum(map(ord, key)) % 8]
    pyxel.circ(x, y, 7 * scale, 1)
    pyxel.circb(x, y, 7 * scale, col)
    words = key.replace("_", " ").split()
    s = (words[0][0] + (words[1][0] if len(words) > 1 else words[0][1])).upper()
    pyxel.text(x - 3, y - 2, s, 7)


def pickup(kind, x, y, t=0):
    key = f"pickup:{kind}"
    if has(key):
        draw(key, x, y, t // 6)
        return True
    return False


def light(kind, x, y, t=0, flash=False):
    key = f"light:{kind}"
    if has(key):
        draw(key, x, y, t // 5, silhouette=flash)
        return True
    return False
