"""90s-theme weapon effects, used by weapons.py only when art.MODE == "90s".

Each function redraws one projectile or weapon visual in the theme's terms (the
whip is a snapping slap bracelet, the wand a laser dot, lightning a plasma arc)
on the same geometry as its weapons.py counterpart, so hits land where the
picture is. A kind with no entry here keeps the shared drawing.
"""

import math
import random

import pyxel

from weapons import PX, TAU, spr

LIME, PINK, CYAN, PURPLE, YELLOW, ORANGE = 24, 27, 28, 29, 30, 31  # atlas neon colours
GREEN, RED, MAROON, CREAM, GREY, INDIGO = 23, 35, 36, 37, 34, 32
PARTY = (PINK, CYAN, YELLOW, LIME, ORANGE, PURPLE)


# ------------------------------------------------------------------ shapes


def star(x, y, r, points, col, rot=0.0, inner=0.45):
    """Filled spiky star, the comic-book burst."""
    pts = []
    for k in range(points * 2):
        a = rot + k * math.pi / points
        rr = r if k % 2 == 0 else r * inner
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    for k in range(len(pts)):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        pyxel.tri(x, y, a[0], a[1], b[0], b[1], col)


def twinkle(x, y, size, col):
    pyxel.line(x - size, y, x + size, y, col)
    pyxel.line(x, y - size, x, y + size, col)
    pyxel.pset(x, y, 7)


def note(x, y, col):
    """A quaver, 5 x 8 px."""
    pyxel.rect(x, y + 5, 3, 3, col)
    pyxel.line(x + 2, y, x + 2, y + 5, col)
    pyxel.line(x + 2, y, x + 4, y + 2, col)


def trail(pr, n, step, cols):
    """Dots strung out behind a moving projectile."""
    for j in range(n):
        f = (j + 1) * step
        pyxel.pset(pr.x - pr.vx * f, pr.y - pr.vy * f, cols[(j + pr.t) % len(cols)])


def heading(pr):
    ln = math.hypot(pr.vx, pr.vy) or 1
    return pr.vx / ln, pr.vy / ln


# ------------------------------------------------------------- projectiles


def d_whip(pr, g):
    """Slap bracelet: a striped band that snaps out straight, then curls at the tip."""
    t = pr.t
    if t > 4:
        return
    p = g.p
    side, area = pr.a, pr.extra
    tear = pr.kind == "tear"
    a, b = (RED, YELLOW) if tear else (LIME, YELLOW)
    reach = 56 * PX * area * min(1.0, (t + 1) / 2)
    x0, cy = p.x + side * 6 * PX, p.y + pr.oy
    segs = 9
    for k in range(segs):
        f0, f1 = k / segs, (k + 1) / segs
        bow0 = math.sin(f0 * math.pi) * 7 * PX * area * (1 - t * 0.2)
        bow1 = math.sin(f1 * math.pi) * 7 * PX * area * (1 - t * 0.2)
        xa, xb = x0 + side * reach * f0, x0 + side * reach * f1
        for o in (-3, -2, -1, 0, 1, 2):
            pyxel.line(xa, cy - bow0 + o, xb, cy - bow1 + o, 0 if o in (-3, 2) else (a if k % 2 else b))
    tipx = x0 + side * reach
    if t >= 2:  # the band curls back on itself
        pyxel.circ(tipx - side * 4, cy - 4, 5, 0)
        pyxel.circ(tipx - side * 4, cy - 4, 4, a)
        pyxel.circ(tipx - side * 4, cy - 4, 2, b)
    if t < 2:
        star(tipx, cy, 7 * area, 6, 7, rot=t)
        star(tipx, cy, 4 * area, 6, b, rot=t + 0.5)


def d_wand(pr, g):
    """Laser pointer: a hard bright dot, a glow and a beam fading back along its path."""
    x, y = pr.x, pr.y
    holy = pr.kind == "holy"
    col = PARTY[pr.t // 2 % len(PARTY)] if holy else RED
    for j in range(1, 7):
        pyxel.dither(1 - j / 7)
        pyxel.line(x - pr.vx * (j - 1) * 0.6, y - pr.vy * (j - 1) * 0.6,
                   x - pr.vx * j * 0.6, y - pr.vy * j * 0.6, col)
    pyxel.dither(0.4)
    pyxel.circ(x, y, 3.5 * PX, PINK if not holy else col)
    pyxel.dither(1.0)
    pyxel.circ(x, y, 1.6 * PX, col)
    pyxel.circ(x, y, 0.8 * PX, 7)
    if pr.t % 4 < 2:
        twinkle(x, y, 4 if holy else 3, 7)


def d_knife(pr, g):
    """Lawn dart with speed lines."""
    ux, uy = heading(pr)
    for o in (-3, 3):
        pyxel.line(pr.x - ux * 14 - uy * o, pr.y - uy * 14 + ux * o,
                   pr.x - ux * (22 + pr.t % 3 * 2) - uy * o, pr.y - uy * (22 + pr.t % 3 * 2) + ux * o, 7)
    if not spr("wspr:knife", pr.x, pr.y, rotate=pr.a, scale=0.7):
        pyxel.line(pr.x - ux * 8, pr.y - uy * 8, pr.x + ux * 5, pr.y + uy * 5, 7)


def d_axe(pr, g):
    """Skateboard tumbling end over end, grinding sparks off its trucks."""
    spr("wspr:axe", pr.x, pr.y, rotate=pr.t * 24, scale=1.2)
    for j in range(3):
        a = math.radians(pr.t * 24) + j * 2.1
        pyxel.pset(pr.x - math.cos(a) * (9 + j * 2), pr.y - math.sin(a) * (9 + j * 2),
                   (YELLOW, ORANGE, 7)[(pr.t + j) % 3])


def d_spiral(pr, g):
    """Buzzsaw deck: the blade plus a ring of sparks thrown off its teeth."""
    spr("wspr:death_spiral", pr.x, pr.y, rotate=pr.t * 40, scale=1.3 * pr.extra)
    r = 9 * PX * pr.extra
    for j in range(6):
        a = pr.t * 0.7 + j * TAU / 6
        pyxel.line(pr.x + math.cos(a) * r, pr.y + math.sin(a) * r,
                   pr.x + math.cos(a + 0.5) * (r + 4), pr.y + math.sin(a + 0.5) * (r + 4),
                   YELLOW if j % 2 else ORANGE)


def d_cross(pr, g):
    """Boomerang (or glow disc) with a whoosh arc behind it."""
    heaven = pr.kind == "heaven"
    key = "wspr:heaven_sword" if heaven else "wspr:cross"
    sc = pr.b * (1.8 if heaven else 1.0)
    ux, uy = heading(pr)
    pyxel.dither(0.45)
    for j in range(1, 4):
        pyxel.circb(pr.x - ux * j * 5, pr.y - uy * j * 5, (6 - j) * sc, YELLOW if heaven else CYAN)
    pyxel.dither(1.0)
    spr(key, pr.x, pr.y, rotate=pr.t * 30, scale=sc)
    if heaven and pr.t % 3 == 0:
        twinkle(pr.x + random.uniform(-8, 8), pr.y + random.uniform(-8, 8), 2, YELLOW)


RING_COLS = (12, RED, LIME, PURPLE, ORANGE, YELLOW)  # frame order of the candy ring sprite


def d_bible(pr, g):
    """Candy ring: bobs as it orbits, glints, and sheds sugar in its own colour."""
    key = "wspr:king_bible" if pr.kind == "bible" else "wspr:unholy_vespers"
    col = RING_COLS[pr.c % len(RING_COLS)]
    for j in range(1, 5):
        a = pr.a - j * 0.16 * (1 if pr.ox >= 0 else -1)
        pyxel.pset(g.p.x + math.cos(a) * pr.extra + (j * 7 + pr.t) % 3 - 1,
                   g.p.y + math.sin(a) * pr.extra + (j * 5 + pr.t) % 3 - 1, col if j % 2 else 7)
    bob = math.sin(pr.t * 0.4 + pr.c) * 1.5
    spr(key, pr.x, pr.y + bob, scale=max(0.8, pr.r / (6 * PX)), frame=pr.c)
    if (pr.t + pr.c * 5) % 18 < 4:
        twinkle(pr.x + 3, pr.y + bob - 5, 3, 7)


def d_fire(pr, g):
    """Bottle rocket: a paper tube on a stick, spitting a fan of sparks. Roman candle: a star."""
    x, y = pr.x, pr.y
    ux, uy = heading(pr)
    for j in range(7):
        f = 2 + j * 1.6
        s = random.uniform(-1, 1) * (1 + j * 0.6)
        pyxel.pset(x - ux * f * 2 - uy * s, y - uy * f * 2 + ux * s, (7, YELLOW, YELLOW, ORANGE, ORANGE, RED, GREY)[j])
    if pr.kind == "hellfire":
        r = pr.r
        pyxel.dither(0.5)
        pyxel.circ(x, y, r, ORANGE)
        pyxel.dither(1.0)
        star(x, y, r * 0.9, 5, (YELLOW, CYAN, PINK)[pr.t // 3 % 3], rot=pr.t * 0.3)
        star(x, y, r * 0.45, 5, 7, rot=-pr.t * 0.3)
        return
    pyxel.line(x - ux * 10, y - uy * 10, x + ux * 2, y + uy * 2, 26)  # the stick
    for o in (-1, 0, 1):
        pyxel.line(x - ux * 2 - uy * o, y - uy * 2 + ux * o, x + ux * 6 - uy * o, y + uy * 6 + ux * o,
                   RED if o else 7)
    pyxel.circ(x + ux * 7, y + uy * 7, 1.5, YELLOW)


def d_water(pr, g):
    """Soda: the can drops in, then a fizzing puddle with bubbles that rise and pop."""
    x, y, t = pr.x, pr.y, pr.t
    slush = pr.kind == "borra"
    if t < 12:
        if not spr("wicon:la_borra" if slush else "wicon:santa_water", x, y - 3 * PX, rotate=t * 25):
            pyxel.rect(x - 2 * PX, y - 3 * PX, 4 * PX, 5 * PX, 12)
        return
    r = pr.r
    body, rim = (6, 7) if slush else (ORANGE, YELLOW)
    pyxel.dither(0.6)
    pyxel.elli(x - r, y - r * 0.6, r * 2, r * 1.2, body)
    pyxel.dither(1.0)
    pyxel.ellib(x - r, y - r * 0.6, r * 2, r * 1.2, rim)
    for j in range(7):
        life = (t * 2 + j * 9) % 24
        bx = x + math.sin(j * 2.4) * r * 0.75 + math.sin(t * 0.3 + j) * 1.5
        by = y + math.cos(j * 1.7) * r * 0.35 - life * 0.5
        if life > 20:  # pop
            twinkle(bx, by, 2, 7)
        elif slush:
            pyxel.rect(bx, by, 2, 2, 7)
        else:
            pyxel.circb(bx, by, 1 + j % 2, 7)


def d_ring(pr, g):
    """Plasma globe: a forked arc from overhead and a glowing ball where it lands."""
    t, x, y = pr.t, pr.x, pr.y
    thunder = pr.kind == "thunder"
    a, b = (YELLOW, CYAN) if thunder else (PURPLE, PINK)
    if t < 1:
        pyxel.circb(x, y, pr.r * (1 - t / 6.0), a)
        return
    if t < 6:
        for fork in range(2 if t < 4 else 1):
            xx, yy = x + (fork * 50 - 20), y - 200
            while yy < y:
                pull = (y - yy) / 200
                nx = x + random.uniform(-9, 9) + (fork * 50 - 20) * pull
                ny = min(y, yy + random.uniform(8, 22))
                pyxel.line(xx, yy, nx, ny, 7 if t < 3 else b)
                pyxel.line(xx + 1, yy, nx + 1, ny, a)
                xx, yy = nx, ny
    grow = pr.r * (0.5 + t * 0.08)
    pyxel.dither(max(0.0, 0.5 - t * 0.05))
    pyxel.circ(x, y, grow, a)
    pyxel.dither(1.0)
    pyxel.circb(x, y, grow, b)
    for j in range(5):  # tendrils crawling inside the globe
        ang = j * TAU / 5 + t * 0.5
        pyxel.line(x, y, x + math.cos(ang) * grow * 0.9, y + math.sin(ang) * grow * 0.9, b if j % 2 else 7)
    if t < 3:
        pyxel.circ(x, y, pr.r * 0.5, 7)


def d_rune(pr, g):
    """Bouncy ball with a rainbow streak. The hyper ball burns white with static."""
    x, y = pr.x, pr.y
    if pr.kind == "nofuture":
        pyxel.line(x - pr.vx * 3, y - pr.vy * 3, x, y, CYAN)
        pyxel.line(x - pr.vx * 2, y - pr.vy * 2 + 1, x, y + 1, 7)
        pyxel.circ(x, y, 3 * PX, CYAN)
        pyxel.circ(x, y, 2 * PX, 7)
        for j in range(3):
            a = random.uniform(0, TAU)
            pyxel.line(x + math.cos(a) * 4, y + math.sin(a) * 4, x + math.cos(a) * 8, y + math.sin(a) * 8, CYAN)
        return
    for j in range(1, 6):
        pyxel.circ(x - pr.vx * j * 0.8, y - pr.vy * j * 0.8, max(1, 3 - j * 0.5), PARTY[(j + pr.t // 2) % len(PARTY)])
    if not spr("wspr:runetracer", x, y, rotate=pr.t * 30, scale=pr.extra):
        pyxel.circ(x, y, 3 * PX * pr.extra, RED)
    pyxel.pset(x - 1, y - 2, 7)


def d_boom(pr, g):
    """Comic-book burst."""
    r = pr.r * (0.4 + pr.t * 0.07)
    c = pr.c or ORANGE
    if pr.t < 6:
        star(pr.x, pr.y, r * 1.15, 9, c, rot=pr.t * 0.2)
        star(pr.x, pr.y, r * 0.8, 9, YELLOW, rot=pr.t * 0.2 + 0.35)
        star(pr.x, pr.y, r * 0.4, 7, 7, rot=-pr.t * 0.3)
    else:
        for j in range(9):
            a = j * TAU / 9 + 0.2
            pyxel.line(pr.x + math.cos(a) * r * 0.8, pr.y + math.sin(a) * r * 0.8,
                       pr.x + math.cos(a) * r * 1.15, pr.y + math.sin(a) * r * 1.15, YELLOW if j % 2 else c)


def d_penta(pr, g):
    """Reset button: the picture collapses to a line, like a TV switching off. Disco ball: beams."""
    t, x, y = pr.t, pr.x, pr.y
    R = min(g.W, g.H) * 0.45 * min(1.0, t / 12)
    if pr.w is not None and pr.w.id == "gorgeous_moon":
        for k in range(10):
            a = t * 0.06 + k * TAU / 10
            pyxel.dither(0.35)
            pyxel.tri(x, y, x + math.cos(a) * R * 1.6, y + math.sin(a) * R * 1.6,
                      x + math.cos(a + 0.12) * R * 1.6, y + math.sin(a + 0.12) * R * 1.6, PARTY[k % len(PARTY)])
            pyxel.dither(1.0)
        pyxel.circ(x, y, 7, GREY)
        for k in range(5):
            pyxel.pset(x - 4 + (k * 3 + t // 2) % 9, y - 4 + (k * 5) % 9, 7)
        return
    pyxel.circb(x, y, R, RED)
    pyxel.circb(x, y, R - 2, MAROON)
    if t >= 12:
        squeeze = max(1, (20 - t) * 3)  # the raster collapsing to a line, then a dot
        pyxel.dither(0.55)
        pyxel.rect(g.cam_x, y - squeeze, g.W, squeeze * 2, 7)
        pyxel.dither(1.0)
        pyxel.line(g.cam_x, y, g.cam_x + g.W, y, 7)
    if t % 8 < 5:
        pyxel.text(x - 10, y - 2, "RESET", 7 if t % 2 else RED)


def d_bomb(pr, g):
    """Water balloon dropped by the RC planes: it wobbles down, then bursts in a splash."""
    if pr.t < 8:
        wob = 1 + (pr.t % 2)
        pyxel.elli(pr.x - 2 * PX, pr.y - 2 * PX - wob / 2, 4 * PX, 4 * PX + wob, pr.c)
        pyxel.pset(pr.x - 1, pr.y - 2, 7)
        pyxel.pset(pr.x, pr.y - 3 * PX - 1, 7)
        return
    k = pr.t - 8
    r = pr.extra * (0.6 + k * 0.08)
    for j in range(10):
        a = j * TAU / 10
        pyxel.circ(pr.x + math.cos(a) * r, pr.y + math.sin(a) * r * 0.8 + k * k * 0.15, max(0.5, 2.5 - k * 0.3),
                   pr.c if j % 2 else 7)
    if k < 3:
        pyxel.circ(pr.x, pr.y, r * 0.5, 7)


def d_gun(pr, g):
    """Squirt gun: a teardrop of water with a highlight and a few drips behind."""
    ux, uy = heading(pr)
    pyxel.tri(pr.x - ux * 6 * PX, pr.y - uy * 6 * PX, pr.x - uy * 2 * PX, pr.y + ux * 2 * PX,
              pr.x + uy * 2 * PX, pr.y - ux * 2 * PX, pr.c)
    pyxel.circ(pr.x, pr.y, 2 * PX, pr.c)
    pyxel.pset(pr.x + ux - uy, pr.y + uy + ux, 7)
    trail(pr, 3, 1.2, (pr.c, 7))


def d_song(pr, g):
    """Karaoke: a column of rising notes swaying to a beat, over equaliser bars."""
    p = g.p
    hw = pr.extra
    cols = (PURPLE, PINK, 7) if (pr.w is not None and pr.w.id == "mannajja") else (CYAN, YELLOW, PINK)
    top = g.cam_y
    pyxel.dither(0.1)
    pyxel.rect(p.x - hw, top, hw * 2, g.H, cols[0])
    pyxel.dither(1.0)
    for j in range(14):
        yy = top + g.H - (j * 47 + pr.t * 5) % g.H
        xx = p.x + math.sin(pr.t * 0.3 + j * 1.7) * hw * 0.8
        note(xx, yy, cols[j % 3])
    bars = 8
    for j in range(bars):
        h = 4 + abs(math.sin(pr.t * 0.5 + j * 1.3)) * 22
        pyxel.dither(0.5)
        pyxel.rect(p.x - hw + j * hw * 2 / bars + 1, top + g.H - h, hw * 2 / bars - 2, h, cols[j % 3])
        pyxel.dither(1.0)


def d_pinion(pr, g):
    """Rollerblades: a wheel spinning off a trail of sparks. Rocket skates leave flame."""
    x, y = pr.x, pr.y
    if pr.w is not None and pr.w.id == "valkyrie_turner":
        for j in range(4):
            pyxel.circ(x - pr.vx * j * 0.7 + random.uniform(-1, 1), y - pr.vy * j * 0.7 + random.uniform(-1, 1),
                       max(1, (4 - j) * PX * 0.8), (7, YELLOW, ORANGE, RED)[j])
        return
    spr("wspr:shadow_pinion", x, y, rotate=pr.t * 45)
    for j in range(4):
        pyxel.pset(x - pr.vx * (1 + j) + random.uniform(-2, 2), y - pr.vy * (1 + j) + 3 + random.uniform(-1, 1),
                   (7, YELLOW, ORANGE, ORANGE)[j])


def d_lance(pr, g):
    """Pause button: a dashed freeze beam ending in a pause symbol."""
    if pr.t > 6:
        return
    p = g.p
    L = 0.55 * g.W
    dx, dy = math.cos(pr.a), math.sin(pr.a)
    for k in range(0, int(L), 10):
        a, b = k + pr.t * 3 % 10, min(L, k + pr.t * 3 % 10 + 6)
        pyxel.line(p.x + dx * a, p.y + dy * a, p.x + dx * b, p.y + dy * b, 7 if pr.t < 3 else CYAN)
        pyxel.line(p.x + dx * a + 1, p.y + dy * a, p.x + dx * b + 1, p.y + dy * b, CYAN)
    ex, ey = p.x + dx * L, p.y + dy * L
    pyxel.circ(ex, ey, 7, 1)
    pyxel.circb(ex, ey, 7, CYAN)
    pyxel.rect(ex - 3, ey - 3, 2, 7, 7)
    pyxel.rect(ex + 1, ey - 3, 2, 7, 7)


def d_slash(pr, g):
    """Jump rope: a striped rope swung out in an arc, handle at the far end."""
    p = g.p
    k = pr.t
    if k > 6:
        return
    L = pr.extra * min(1, k / 3)
    x0, y = p.x + pr.a * 4 * PX, p.y + pr.oy
    h = pr.b * 0.5 * max(0.2, 1 - k / (pr.t + pr.life))
    n = 10
    for j in range(n):
        f0, f1 = j / n, (j + 1) / n
        y0, y1 = y - h * math.sin(f0 * math.pi), y - h * math.sin(f1 * math.pi)
        for o in (0, 1):
            pyxel.line(x0 + pr.a * L * f0, y0 + o, x0 + pr.a * L * f1, y1 + o, 7 if j % 2 else pr.c)
    pyxel.rect(x0 + pr.a * L - 2, y - 2, 5, 4, YELLOW)
    pyxel.rectb(x0 + pr.a * L - 2, y - 2, 5, 4, 0)


def d_fring(pr, g):
    """Crash helmet retaliation: a ring of warning chevrons."""
    p = g.p
    R = pr.extra
    for j in range(12):
        a = j * TAU / 12 + pr.t * 0.3
        x1, y1 = p.x + math.cos(a) * R, p.y + math.sin(a) * R
        x2, y2 = p.x + math.cos(a + 0.2) * (R + 5), p.y + math.sin(a + 0.2) * (R + 5)
        x3, y3 = p.x + math.cos(a + 0.4) * R, p.y + math.sin(a + 0.4) * R
        c = YELLOW if j % 2 else RED
        pyxel.line(x1, y1, x2, y2, c)
        pyxel.line(x2, y2, x3, y3, c)


def d_bracelet(pr, g):
    """Friendship band: three beads on a thread, each its own colour."""
    pts = []
    for j in range(3):
        a = pr.t * 0.6 + j * TAU / 3
        pts.append((pr.x + math.cos(a) * 2.5 * PX, pr.y + math.sin(a) * 2.5 * PX))
    for j in range(3):
        pyxel.line(pts[j][0], pts[j][1], pts[(j + 1) % 3][0], pts[(j + 1) % 3][1], 7)
    for j, (bx, by) in enumerate(pts):
        pyxel.circ(bx, by, 1.5 * PX, (pr.c, PINK, CYAN)[j])
        pyxel.pset(bx - 1, by - 1, 7)


def spun(key, spin, scale=1.0, streak=None):
    """A thrown sprite that tumbles, optionally with a streak of colour behind it."""
    def draw(pr, g):
        if streak:
            trail(pr, 4, 1.0, streak)
        spr(key, pr.x, pr.y, rotate=pr.t * spin * (1 if pr.vx >= 0 else -1), scale=scale * (pr.extra or 1.0))
    return draw


def d_cherry(pr, g):
    """Cherry bomb: tumbling, with a fuse that spits sparks."""
    spr("wspr:cherry_bomb", pr.x, pr.y, rotate=pr.t * 20)
    a = math.radians(pr.t * 20) - 1.2
    fx, fy = pr.x + math.cos(a) * 7, pr.y + math.sin(a) * 7
    for j in range(3):
        pyxel.pset(fx + random.uniform(-2, 2), fy + random.uniform(-2, 2), (7, YELLOW, ORANGE)[j])


def d_cat(pr, g):
    """Alley cat: trots with a bounce and kicks up dust."""
    vic = pr.w is not None and pr.w.id == "vicious_hunger"
    key = "wspr:vicious_hunger" if vic else "wspr:gatti_amari"
    moving = abs(pr.vx) + abs(pr.vy) > 0.2
    hop = abs(math.sin(pr.t * 0.5)) * 2 if moving else 0
    spr(key, pr.x, pr.y - hop, flip=pr.vx < 0, scale=1.2 if vic else 1.0)
    if moving and pr.t % 6 < 2:
        pyxel.pset(pr.x - (6 if pr.vx >= 0 else -6), pr.y + 6, GREY)


DRAW = {
    "whip": d_whip, "tear": d_whip, "wand": d_wand, "holy": d_wand, "knife": d_knife, "edge": d_knife,
    "axe": d_axe, "spiral": d_spiral, "cross": d_cross, "heaven": d_cross, "bible": d_bible,
    "vespers": d_bible, "fire": d_fire, "hellfire": d_fire, "water": d_water, "borra": d_water,
    "ring": d_ring, "thunder": d_ring, "rune": d_rune, "nofuture": d_rune, "boom": d_boom,
    "penta": d_penta, "bomb": d_bomb, "gun": d_gun, "cat": d_cat, "song": d_song, "pinion": d_pinion,
    "lance": d_lance, "slash": d_slash, "fring": d_fring, "bracelet": d_bracelet, "cherry": d_cherry,
    "bone": spun("wspr:bone", 30, 0.8, streak=(7, GREY)),
    "flower": spun("wspr:celestial_dusting", 15, streak=PARTY),
    "cart": spun("wspr:carrello", 25, 0.5, streak=(YELLOW, ORANGE)),
    "robba": spun("wspr:la_robba", 12, 0.6),
}


# ------------------------------------------------- weapon-owned visuals


def aura(w, g):
    """90s version of a weapon's standing visual. False when this weapon has none here."""
    k, p, fx = w.kind, g.p, w.fx
    if k in ("garlic", "soul"):
        r = fx.get("r", 0)
        if not r:
            return True
        soul = k == "soul"
        a, b = (PURPLE, PINK) if soul else (GREEN, LIME)
        pyxel.dither(0.08)  # faint: the horde has to stay readable through it
        pyxel.circ(p.x, p.y, r, a)
        pyxel.dither(1.0)
        for j in range(10):  # puffs drifting round the edge of the cloud
            ang = j * TAU / 10 + g.frame * 0.03
            pr_ = r * (0.92 + 0.08 * math.sin(g.frame * 0.15 + j))
            pyxel.dither(0.3)
            pyxel.circ(p.x + math.cos(ang) * pr_, p.y + math.sin(ang) * pr_, 4 + j % 3, a)
            pyxel.dither(1.0)
        for j in range(5):  # wavy stink lines rising
            bx = p.x + math.sin(j * 2.3) * r * 0.7
            rise = (g.frame + j * 13) % 40
            by = p.y + math.cos(j * 1.9) * r * 0.5 - rise * 0.5
            for s in range(4):
                pyxel.pset(bx + math.sin((rise + s * 3) * 0.4) * 2, by - s * 2, b)
        if soul:  # flies
            for j in range(4):
                ang = g.frame * 0.2 + j * 1.7
                pyxel.pset(p.x + math.cos(ang) * r * 0.6, p.y + math.sin(ang * 1.3) * r * 0.4, 0)
        return True
    if k == "bird" and "bx" in fx:
        col = {"peachone": 7, "ebony_wings": PURPLE}.get(w.id, YELLOW)
        for zx, zy in fx["zones"]:  # a target painted on the ground
            pyxel.dither(0.45)
            pyxel.circb(zx, zy, 9 * PX, col)
            pyxel.circb(zx, zy, 4 * PX, col)
            pyxel.line(zx - 11 * PX, zy, zx + 11 * PX, zy, col)
            pyxel.line(zx, zy - 11 * PX, zx, zy + 11 * PX, col)
            pyxel.dither(1.0)
        flip = fx["zones"][0][0] < fx["bx"] if fx["zones"] else False
        bank = math.sin(g.frame * 0.25) * 12
        spr(f"wspr:{w.id}", fx["bx"], fx["by"] + math.sin(g.frame * 0.2) * 2, rotate=-bank if flip else bank,
            flip=flip, scale=1.2)
        if g.frame % 3 == 0:  # propeller wash
            pyxel.pset(fx["bx"] + (10 if flip else -10), fx["by"] + random.uniform(-2, 2), 7)
        return True
    if k == "lasers" and fx.get("on", 0) > 0:
        n, L, wid = fx["n"], fx["len"], fx["wid"]
        for j in range(n):  # jets of water
            a = fx["ang"] + j * TAU / n
            ex, ey = p.x + math.cos(a) * L, p.y + math.sin(a) * L
            nx, ny = -math.sin(a), math.cos(a)
            for o in range(-int(wid // 2), int(wid // 2) + 1):
                c = 7 if abs(o) < wid / 5 else (CYAN if abs(o) < wid / 3 else 12)
                pyxel.line(p.x + nx * o, p.y + ny * o, ex + nx * o, ey + ny * o, c)
            for d in range(4):
                f = ((g.frame * 5 + d * 40 + j * 17) % 100) / 100
                pyxel.circ(p.x + math.cos(a) * L * f + nx * (wid / 2 + 3), p.y + math.sin(a) * L * f + ny * (wid / 2 + 3), 1, 7)
            pyxel.circ(ex, ey, wid * 0.7, 7)
        return True
    if k == "shield":
        ch = fx.get("charges", 0)
        if ch <= 0 and not fx.get("pop"):
            return True
        crash = w.id == "crimson_shroud"
        col = ({1: ORANGE, 2: RED, 3: RED} if crash else {1: CYAN, 2: LIME, 3: YELLOW}).get(ch, CYAN)
        r = 15 * PX + math.sin(g.frame * 0.15) * 1.5
        if fx.get("pop"):
            r += (10 - fx["pop"]) * 2
            col = 7
        pyxel.dither(0.18)
        pyxel.circ(p.x, p.y - 2, r, col)
        pyxel.dither(1.0)
        for j in range(24):  # a helmet shell: solid over the top, open below
            a = math.pi + j * math.pi / 23
            pyxel.line(p.x + math.cos(a) * r, p.y - 2 + math.sin(a) * r,
                       p.x + math.cos(a) * (r - 3), p.y - 2 + math.sin(a) * (r - 3), col if j % 4 else 7)
        pyxel.circb(p.x, p.y - 2, r, col)
        sweep = (g.frame * 0.12) % math.pi
        twinkle(p.x + math.cos(math.pi + sweep) * (r - 2), p.y - 2 + math.sin(math.pi + sweep) * (r - 2), 3, 7)
        return True
    return False
