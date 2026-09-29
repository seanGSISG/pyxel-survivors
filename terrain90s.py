"""90s-theme stage terrain, used by main.py only when art.MODE == "90s".

Each stage keeps the layout of its main.py terrain_<stage> counterpart: corridor
and tower walls sit on the same lines, so only the look changes.

mad_forest -> arcade carpet, inlaid_library -> sewer tunnel, dairy_plant -> city
rooftop, gallo_tower -> neon mall, cappella_magna -> CRT grid.
"""

import math

import pyxel

W, H = 480, 270
T0, T1, T2, T3, T4 = 16, 17, 18, 19, 20  # terrain palette slots (T3 = shadows)
OOZE, LIME, PINK, CYAN, PURPLE, YELLOW, ORANGE = 23, 24, 27, 28, 29, 30, 31  # atlas neon colours
SIGNS = (PINK, CYAN, YELLOW, PURPLE, ORANGE, LIME)

PALETTE = {
    "mad_forest": [0x1A1033, 0x251A48, 0x6A2A7A, 0x0C0719, 0x1F6F78],
    "inlaid_library": [0x2B3330, 0x353F3A, 0x2C5220, 0x131816, 0x6F7F6A],
    "dairy_plant": [0x34343F, 0x3F3F4C, 0x55556A, 0x1A1A22, 0x8A8AA0],
    "gallo_tower": [0x2A4A52, 0x335861, 0x1E363C, 0x12222A, 0xE87AC0],
    "cappella_magna": [0x0A0C1E, 0x14224A, 0x1F3F8A, 0x000004, 0x3FD0FF],
}
# Base-palette approximations, for the stage-select swatches.
SWATCH = {"mad_forest": [2, 14, 3, 1], "inlaid_library": [5, 13, 3, 11],
          "dairy_plant": [5, 13, 6, 1], "gallo_tower": [3, 12, 14, 1],
          "cappella_magna": [1, 5, 12, 6]}


def hash2(x, y):
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return n ^ (n >> 16)


def cells(cx, cy, size):
    for gx in range(cx // size - 1, (cx + W) // size + 2):
        for gy in range(cy // size - 1, (cy + H) // size + 2):
            yield gx, gy


def draw(app, cx, cy):
    globals()[app.stage["id"]](app, cx, cy)


def mad_forest(app, cx, cy):
    """Arcade carpet: dim geometric shapes, squiggles and confetti on indigo."""
    for gx, gy in cells(cx, cy, 96):
        h = hash2(gx, gy)
        if h % 3:
            continue
        x, y, k = gx * 96 + h % 50, gy * 96 + (h >> 6) % 50, (h >> 10) % 3
        if k == 0:
            pyxel.circ(x, y, 20 + (h >> 12) % 14, T1)
        elif k == 1:
            pyxel.tri(x, y - 26, x - 26, y + 20, x + 26, y + 20, T1)
        else:
            pyxel.rect(x - 18, y - 18, 36, 36, T1)
    for gx, gy in cells(cx, cy, 24):
        h = hash2(gx + 7919, gy - 104729)
        x, y, r = gx * 24 + h % 18, gy * 24 + (h >> 5) % 18, h % 97
        if r < 10:
            for k in range(3):
                pyxel.line(x + k * 4, y + (k % 2) * 4, x + k * 4 + 4, y + ((k + 1) % 2) * 4, T2)
        elif r < 17:
            pyxel.trib(x, y - 4, x - 4, y + 3, x + 4, y + 3, T4)
        elif r < 23:
            pyxel.circb(x, y, 3, T2 if h & 256 else T4)
        elif r < 28:
            for k, c in enumerate((PINK, CYAN, YELLOW)):
                pyxel.pset(x + (h >> (8 + k * 3)) % 9, y + (h >> (9 + k * 3)) % 9, c)
        elif r < 29:  # a dropped token
            pyxel.circ(x, y, 2, 9)
            pyxel.pset(x - 1, y - 1, YELLOW)


def inlaid_library(app, cx, cy):
    """Sewer tunnel: concrete slabs, an ooze channel down the middle, brick walls."""
    band = H * 0.55 + 24
    for gy in range(cy // 24 - 1, (cy + H) // 24 + 2):
        y = gy * 24
        pyxel.line(cx, y, cx + W, y, T3)
        off = (gy * 37) % 48
        for gx in range((cx - off) // 48 - 1, (cx + W) // 48 + 2):
            x, h = gx * 48 + off, hash2(gx, gy)
            pyxel.line(x, y, x, y + 23, T3)
            if h % 4 == 0:
                pyxel.rect(x + 1, y + 1, 47, 23, T1)
            elif h % 23 == 0:  # drain grate
                pyxel.rect(x + 16, y + 6, 16, 12, T3)
                for k in range(3):
                    pyxel.line(x + 17, y + 8 + k * 4, x + 30, y + 8 + k * 4, T4)
    pyxel.rect(cx, -20, W, 40, T2)  # ooze channel
    pyxel.line(cx, -21, cx + W, -21, T4)
    pyxel.line(cx, 20, cx + W, 20, T4)
    flow = app.frame // 3
    for gx in range((cx - flow) // 40 - 1, (cx + W - flow) // 40 + 2):
        for k in range(3):
            h = hash2(gx, k)
            x = gx * 40 + flow + h % 30
            pyxel.line(x, -13 + k * 13 + h % 3, x + 3 + h % 5, -13 + k * 13 + h % 3, OOZE)
    for s in (-1, 1):  # brick walls
        y0 = band if s > 0 else -band - 60
        pyxel.rect(cx, y0, W, 60, T3)
        for row in range(8):
            y = y0 + row * 8
            pyxel.line(cx, y, cx + W, y, T0)
            off = 8 if row % 2 else 0
            for gx in range((cx - off) // 16 - 1, (cx + W) // 16 + 2):
                pyxel.line(gx * 16 + off, y, gx * 16 + off, y + 7, T0)
        for gx in range(cx // 120 - 1, (cx + W) // 120 + 2):  # outflow pipes
            x, yp = gx * 120 + 40 + hash2(gx, s) % 40, y0 + 30
            pyxel.circ(x, yp, 9, T4)
            pyxel.circ(x, yp, 7, 0)
            pyxel.rect(x - 2, yp + 3, 4, 4 + (app.frame // 6 + gx) % 5, LIME)
        pyxel.rect(cx, y0 + (0 if s > 0 else 56), W, 4, T4)


def dairy_plant(app, cx, cy):
    """City rooftop: tar and gravel, duct runs, parapets, vents and spinning fans."""
    for gx in range(cx // 160 - 1, (cx + W) // 160 + 2):  # duct runs
        pyxel.rect(gx * 160, cy, 18, H, T2)
        pyxel.line(gx * 160 + 3, cy, gx * 160 + 3, cy + H, T4)
        for gy in range(cy // 40 - 1, (cy + H) // 40 + 2):
            pyxel.line(gx * 160, gy * 40, gx * 160 + 17, gy * 40, T3)
    for gy in range(cy // 140 - 1, (cy + H) // 140 + 2):  # parapets
        pyxel.rect(cx, gy * 140, W, 14, T2)
        pyxel.line(cx, gy * 140, cx + W, gy * 140, T4)
        pyxel.line(cx, gy * 140 + 13, cx + W, gy * 140 + 13, T3)
    for gx, gy in cells(cx, cy, 24):
        h = hash2(gx, gy)
        x, y, r = gx * 24 + h % 16, gy * 24 + (h >> 5) % 16, h % 211
        if r < 40:  # gravel
            pyxel.pset(x, y, T1)
            pyxel.pset(x + 3, y + 2, T4 if r < 8 else T1)
        elif r < 44:  # puddle
            pyxel.elli(x, y, 14, 7, T3)
            pyxel.line(x + 3, y + 2, x + 8, y + 2, 5)
        elif r < 47:  # vent
            pyxel.rect(x, y, 13, 10, T2)
            pyxel.rectb(x, y, 13, 10, T4)
            for k in range(3):
                pyxel.line(x + 2, y + 2 + k * 3, x + 10, y + 2 + k * 3, T3)
        elif r < 49:  # exhaust fan
            pyxel.circ(x, y, 8, T2)
            pyxel.circ(x, y, 6, T3)
            a = app.frame * 0.3 + h % 7
            for k in range(4):
                b = a + k * math.tau / 4
                pyxel.line(x, y, x + math.cos(b) * 5, y + math.sin(b) * 5, T4)


def gallo_tower(app, cx, cy):
    """Neon mall: a tiled concourse between two rows of shopfronts."""
    for gx, gy in cells(cx, cy, 32):
        x, y = gx * 32, gy * 32
        pyxel.rect(x, y, 32, 32, T0 if (gx + gy) % 2 else T1)
        pyxel.rectb(x, y, 32, 32, T2)
        if hash2(gx, gy) % 9 == 0:  # tile inlay
            pyxel.line(x + 16, y + 10, x + 22, y + 16, T4)
            pyxel.line(x + 22, y + 16, x + 16, y + 22, T4)
            pyxel.line(x + 16, y + 22, x + 10, y + 16, T4)
            pyxel.line(x + 10, y + 16, x + 16, y + 10, T4)
    edge = W * 0.3 + 30
    for s in (-1, 1):
        x0 = edge if s > 0 else -edge - 80
        pyxel.rect(x0, cy, 80, H, T3)
        for gy in range(cy // 72 - 1, (cy + H) // 72 + 2):
            h = hash2(gy, s)
            y, c = gy * 72, SIGNS[h % len(SIGNS)]
            pyxel.line(x0, y, x0 + 79, y, T2)
            pyxel.rect(x0 + 12, y + 22, 56, 42, 1)  # shop window
            pyxel.rectb(x0 + 12, y + 22, 56, 42, T2)
            pyxel.line(x0 + 16, y + 58, x0 + 30, y + 28, 5)
            if h % 5 == 0 and (app.frame // 5 + h) % 9 == 0:
                continue  # this sign flickers
            pyxel.rectb(x0 + 14, y + 7, 52, 11, c)
            for k in range(5):  # unreadable lettering
                hk = hash2(h, k)
                pyxel.rect(x0 + 19 + k * 9, y + 10, 5 + hk % 3, 5, c if hk % 4 else 7)
        pyxel.rect(x0 + (0 if s > 0 else 76), cy, 4, H, T4)


def cappella_magna(app, cx, cy):
    """CRT grid: glowing lattice, data columns and a slow scan sweep."""
    for gx in range(cx // 24 - 1, (cx + W) // 24 + 2):
        pyxel.line(gx * 24, cy, gx * 24, cy + H, T2 if gx % 5 == 0 else T1)
    for gy in range(cy // 24 - 1, (cy + H) // 24 + 2):
        pyxel.line(cx, gy * 24, cx + W, gy * 24, T2 if gy % 5 == 0 else T1)
    for gx, gy in cells(cx, cy, 120):
        x, y, h = gx * 120, gy * 120, hash2(gx, gy)
        pyxel.line(x - 3, y, x + 3, y, T4)
        pyxel.line(x, y - 3, x, y + 3, T4)
        if h % 3 == 0:  # glitch blocks
            for k in range(4):
                hk = hash2(h, k + app.frame // 20)
                pyxel.rect(x + 30 + hk % 60, y + 30 + (hk >> 7) % 60, 4 + hk % 9, 3, T2)
    for gx in range(cx // 240 - 1, (cx + W) // 240 + 2):  # data columns
        x = gx * 240 + 60
        pyxel.rect(x, cy, 28, H, T1)
        pyxel.line(x, cy, x, cy + H, T2)
        pyxel.line(x + 27, cy, x + 27, cy + H, T2)
        fall = app.frame // 4
        for gy in range(cy // 12 - 1, (cy + H) // 12 + 2):
            for k in range(3):
                if hash2(gx * 3 + k, gy - fall) % 6 == 0:
                    pyxel.rect(x + 4 + k * 8, gy * 12 + 2, 4, 6, T4 if k == 1 else T2)
    pyxel.dither(0.35)
    pyxel.rect(cx, cy + (app.frame * 2) % (H + 60) - 30, W, 5, T2)
    pyxel.dither(1.0)
