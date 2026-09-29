"""8x8 item icons, drawn once into image bank 2 and blitted at any scale."""

import pyxel

import sprites

SLOT = {}  # key -> (u, v)


def _spr(d, name, ox, oy):
    u, v, w, h = sprites.POS[name]
    d.blt(ox, oy, 0, u, v, w, h, 0)


def _whip(d, ox, oy, c=7):
    d.line(ox + 1, oy + 7, ox + 2, oy + 5, 4)
    d.line(ox + 2, oy + 5, ox + 4, oy + 2, c)
    d.line(ox + 4, oy + 2, ox + 7, oy + 1, c)
    d.pset(ox + 7, oy + 2, c)


def _wand(d, ox, oy, star=10, stick=4):
    d.line(ox + 1, oy + 7, ox + 5, oy + 3, stick)
    d.pset(ox + 6, oy + 1, star)
    d.line(ox + 5, oy + 2, ox + 7, oy + 2, star)
    d.line(ox + 6, oy + 1, ox + 6, oy + 3, star)


def _knife(d, ox, oy):
    d.line(ox + 3, oy + 4, ox + 7, oy + 0, 7)
    d.line(ox + 3, oy + 5, ox + 6, oy + 2, 13)
    d.line(ox + 0, oy + 7, ox + 2, oy + 5, 4)


def _flame(d, ox, oy, r, c1=8, c2=9, c3=10):
    d.circ(ox + 4, oy + 4, r, c1)
    d.circ(ox + 4, oy + 5, r - 1, c2)
    d.pset(ox + 4, oy + 5, c3)


def _bulb(d, ox, oy, c=7, s=15):
    d.circ(ox + 4, oy + 5, 3, c)
    d.pset(ox + 3, oy + 4, s)
    d.line(ox + 4, oy + 0, ox + 4, oy + 2, 11)


def _flask(d, ox, oy, c=12):
    d.rect(ox + 1, oy + 3, 6, 5, c)
    d.rect(ox + 3, oy + 0, 2, 3, 6)
    d.pset(ox + 2, oy + 4, 7)


def _ring(d, ox, oy, c=10):
    d.circb(ox + 4, oy + 4, 3, c)
    d.line(ox + 5, oy + 0, ox + 3, oy + 4, 7)
    d.line(ox + 3, oy + 4, ox + 5, oy + 4, 7)
    d.line(ox + 5, oy + 4, ox + 3, oy + 7, 7)


def draw_raw(d, key, ox, oy):
    """Draw icon `key` onto target d (pyxel module or Image) at (ox, oy)."""
    if key == "whip":
        _whip(d, ox, oy)
    elif key == "bloody_tear":
        _whip(d, ox, oy, 8)
        d.pset(ox + 6, oy + 5, 8)
        d.pset(ox + 6, oy + 6, 8)
    elif key == "magic_wand":
        _wand(d, ox, oy, 12, 4)
    elif key == "holy_wand":
        _wand(d, ox, oy, 10, 7)
        d.circb(ox + 6, oy + 2, 2, 10)
    elif key == "knife":
        _knife(d, ox, oy)
    elif key == "thousand_edge":
        d.line(ox + 1, oy + 2, ox + 7, oy + 2, 7)
        d.line(ox + 0, oy + 4, ox + 6, oy + 4, 6)
        d.line(ox + 1, oy + 6, ox + 7, oy + 6, 7)
        d.pset(ox, oy + 2, 4)
        d.pset(ox, oy + 6, 4)
    elif key == "axe":
        d.line(ox + 4, oy + 2, ox + 4, oy + 7, 4)
        d.rect(ox + 1, oy + 0, 6, 3, 13)
        d.line(ox + 1, oy + 1, ox + 6, oy + 1, 7)
    elif key == "death_spiral":
        d.circb(ox + 4, oy + 4, 3, 13)
        d.line(ox + 4, oy + 1, ox + 7, oy + 0, 7)
        d.line(ox + 1, oy + 7, ox + 4, oy + 4, 4)
        d.pset(ox + 4, oy + 4, 11)
    elif key == "cross":
        _spr(d, "cross", ox, oy)
    elif key == "heaven_sword":
        d.line(ox + 4, oy + 0, ox + 4, oy + 6, 7)
        d.line(ox + 3, oy + 1, ox + 3, oy + 5, 6)
        d.line(ox + 1, oy + 5, ox + 7, oy + 5, 10)
        d.pset(ox + 4, oy + 7, 9)
    elif key == "king_bible":
        _spr(d, "bible", ox, oy)
    elif key == "unholy_vespers":
        pyxel.pal(12, 2)
        _spr(d, "bible", ox, oy)
        pyxel.pal()
    elif key == "fire_wand":
        d.line(ox + 1, oy + 7, ox + 4, oy + 4, 4)
        _flame(d, ox + 1, oy - 2, 2)
    elif key == "hellfire":
        _flame(d, ox, oy, 3)
    elif key == "garlic":
        _bulb(d, ox, oy)
    elif key == "soul_eater":
        _bulb(d, ox, oy, 14, 7)
    elif key == "santa_water":
        _flask(d, ox, oy)
    elif key == "la_borra":
        _flask(d, ox, oy, 2)
    elif key == "lightning_ring":
        _ring(d, ox, oy)
    elif key == "thunder_loop":
        _ring(d, ox, oy, 9)
        d.circb(ox + 4, oy + 4, 2, 10)
    elif key == "runetracer":
        _spr(d, "rune", ox, oy)
    elif key == "no_future":
        pyxel.pal(12, 8)
        pyxel.pal(6, 14)
        _spr(d, "rune", ox, oy)
        pyxel.pal()
    # passives
    elif key == "spinach":
        d.elli(ox + 1, oy + 1, 6, 6, 3)
        d.line(ox + 1, oy + 7, ox + 6, oy + 2, 11)
    elif key == "armor":
        d.rect(ox + 1, oy + 0, 6, 5, 13)
        d.tri(ox + 1, oy + 5, ox + 6, oy + 5, ox + 3.5, oy + 7, 13)
        d.line(ox + 2, oy + 1, ox + 2, oy + 4, 7)
    elif key == "hollow_heart":
        pyxel.pal(8, 2)
        _spr(d, "heart", ox, oy)
        pyxel.pal()
        d.rect(ox + 2, oy + 2, 4, 2, 0)
    elif key == "pummarola":
        d.circ(ox + 4, oy + 4, 3, 8)
        d.pset(ox + 3, oy + 3, 14)
        d.line(ox + 3, oy + 0, ox + 5, oy + 1, 11)
    elif key == "empty_tome":
        d.rect(ox + 1, oy + 0, 6, 8, 4)
        d.rect(ox + 2, oy + 1, 4, 6, 15)
        d.line(ox + 2, oy + 3, ox + 5, oy + 3, 13)
    elif key == "candelabrador":
        d.rect(ox + 3, oy + 3, 2, 5, 7)
        d.pset(ox + 3, oy + 1, 10)
        d.pset(ox + 4, oy + 2, 9)
        d.line(ox + 1, oy + 7, ox + 6, oy + 7, 10)
    elif key == "bracer":
        d.circb(ox + 4, oy + 4, 3, 4)
        d.circb(ox + 4, oy + 4, 2, 9)
    elif key == "spellbinder":
        d.circ(ox + 4, oy + 4, 3, 2)
        d.pset(ox + 3, oy + 3, 14)
        d.circb(ox + 4, oy + 4, 3, 10)
    elif key == "duplicator":
        d.circb(ox + 3, oy + 4, 2, 10)
        d.circb(ox + 5, oy + 4, 2, 9)
    elif key == "wings":
        d.tri(ox + 0, oy + 1, ox + 7, oy + 4, ox + 2, oy + 7, 7)
        d.line(ox + 1, oy + 3, ox + 5, oy + 4, 6)
    elif key == "attractorb":
        d.circ(ox + 4, oy + 4, 3, 12)
        d.circb(ox + 4, oy + 4, 3, 6)
        d.pset(ox + 3, oy + 3, 7)
    elif key in ("clover", "little_clover"):
        for dx, dy in ((2, 2), (5, 2), (2, 5), (5, 5)):
            d.circ(ox + dx, oy + dy, 1, 11)
        d.pset(ox + 4, oy + 4, 3)
        d.line(ox + 4, oy + 5, ox + 5, oy + 7, 3)
    elif key == "crown":
        d.rect(ox + 1, oy + 4, 6, 3, 10)
        d.tri(ox + 1, oy + 4, ox + 1, oy + 1, ox + 3, oy + 4, 10)
        d.tri(ox + 3, oy + 4, ox + 4, oy + 1, ox + 5, oy + 4, 10)
        d.tri(ox + 5, oy + 4, ox + 7, oy + 1, ox + 7, oy + 4, 10)
        d.pset(ox + 4, oy + 5, 8)
    # pickups / misc
    elif key in ("chicken", "rosary", "clock", "coin", "heart"):
        _spr(d, key, ox, oy)
    elif key == "vacuum":
        _spr(d, "magnet", ox, oy)
    elif key in ("coinbag", "richbag", "gold"):
        c = 10 if key != "richbag" else 7
        d.circ(ox + 4, oy + 5, 3, 4)
        d.rect(ox + 3, oy + 0, 2, 2, 4)
        d.pset(ox + 4, oy + 5, c)
        d.pset(ox + 3, oy + 4, c)
    elif key == "nduja":
        d.elli(ox + 1, oy + 2, 6, 5, 8)
        d.pset(ox + 4, oy + 1, 11)
        d.pset(ox + 2, oy + 3, 14)
    elif key == "skull":
        d.circ(ox + 4, oy + 3, 3, 7)
        d.rect(ox + 2, oy + 5, 5, 3, 7)
        d.pset(ox + 3, oy + 3, 0)
        d.pset(ox + 5, oy + 3, 0)
        d.pset(ox + 3, oy + 7, 0)
        d.pset(ox + 5, oy + 7, 0)


KEYS = [
    "whip", "bloody_tear", "magic_wand", "holy_wand", "knife", "thousand_edge",
    "axe", "death_spiral", "cross", "heaven_sword", "king_bible", "unholy_vespers",
    "fire_wand", "hellfire", "garlic", "soul_eater", "santa_water", "la_borra",
    "lightning_ring", "thunder_loop", "runetracer", "no_future",
    "spinach", "armor", "hollow_heart", "pummarola", "empty_tome", "candelabrador",
    "bracer", "spellbinder", "duplicator", "wings", "attractorb", "clover", "crown",
    "chicken", "rosary", "clock", "coin", "heart", "vacuum", "coinbag", "richbag",
    "gold", "nduja", "little_clover", "skull",
]


def load():
    img = pyxel.images[2]
    img.cls(0)
    for i, key in enumerate(KEYS):
        u, v = (i % 32) * 8, (i // 32) * 8
        draw_raw(img, key, u, v)
        SLOT[key] = (u, v)


def draw(key, x, y, scale=1):
    """Draw icon centred on (x, y)."""
    u, v = SLOT[key]
    pyxel.blt(x - 4, y - 4, 2, u, v, 8, 8, 0, 0, scale)
