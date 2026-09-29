"""Weapon instances, projectiles and their per-kind behaviour.

A Weapon owns cooldown/burst timing and computes its final stats from the
wiki data (base + per-level deltas) plus the player's passive multipliers.
Each shot spawns a Proj whose `kind` selects an update/draw function below.
Some kinds (auras, birds, lasers, shields, movement weapons) run a custom
per-frame update instead of the generic cooldown/burst loop.

Spatial constants are authored for 16px sprites and scaled by PX.
"""

import math
import random
import re

import pyxel

import art
import data
import sprites

FPS = 30
PX = 1.5
TAU = math.tau


def sec(s):
    return max(1, int(round(s * FPS)))


# weapon id -> behaviour kind (update/draw functions below)
KIND = {
    "whip": "whip", "bloody_tear": "tear", "magic_wand": "wand", "holy_wand": "holy",
    "knife": "knife", "thousand_edge": "edge", "axe": "axe", "death_spiral": "spiral",
    "cross": "cross", "heaven_sword": "heaven", "king_bible": "bible",
    "unholy_vespers": "vespers", "fire_wand": "fire", "hellfire": "hellfire",
    "garlic": "garlic", "soul_eater": "soul", "santa_water": "water", "la_borra": "borra",
    "lightning_ring": "ring", "thunder_loop": "thunder", "runetracer": "rune",
    "no_future": "nofuture", "pentagram": "penta", "gorgeous_moon": "penta",
    "peachone": "bird", "ebony_wings": "bird", "vandalier": "bird",
    "phiera_der_tuphello": "gun", "eight_the_sparrow": "gun", "phieraggi": "lasers",
    "gatti_amari": "cat", "vicious_hunger": "cat", "song_of_mana": "song", "mannajja": "song",
    "shadow_pinion": "pinion", "valkyrie_turner": "pinion", "clock_lancet": "lancet",
    "infinite_corridor": "lancet", "laurel": "shield", "crimson_shroud": "shield",
    "vento_sacro": "vento", "fuwalafuwaloo": "vento", "bone": "bone", "cherry_bomb": "cherry",
    "carrello": "cart", "celestial_dusting": "flower", "la_robba": "robba",
    "bracelet": "bracelet", "bi_bracelet": "bracelet", "tri_bracelet": "bracelet",
}
# kinds that release a whole volley at once instead of one shot per interval
VOLLEY = {"bible", "vespers", "fire", "hellfire", "spiral", "bracelet", "penta", "cart"}
# player stats a weapon ignores (wiki "Ignores ..." notes)
IGNORES = {
    "whip": {"speed", "dur"}, "bloody_tear": {"speed", "dur"},
    "laurel": {"might", "area", "speed", "dur", "amount"},
    "crimson_shroud": {"speed", "dur", "amount"},
    "clock_lancet": {"might", "amount", "speed", "area"},
    "infinite_corridor": {"might", "amount", "speed", "area"},
    "pentagram": {"might", "area", "speed", "dur", "amount"},
    "gorgeous_moon": {"might", "area", "speed", "dur", "amount"},
    "song_of_mana": {"amount", "speed"}, "mannajja": {"amount", "speed"},
    "carrello": {"dur"}, "celestial_dusting": {"speed"},
}
# built-in crits: id -> (chance, multiplier)
CRIT = {"bloody_tear": (0.1, 2.0), "heaven_sword": (0.1, 2.5),
        "vento_sacro": (0.05, 2.0), "fuwalafuwaloo": (0.05, 2.0)}
# per-level effects the generic level deltas don't carry
_EXTRA = [
    (re.compile(r"Shield invulnerability increased by ([\d.]+)"), "inv", 1.0),
    (re.compile(r"additional charge"), "charges", None),
]


class _NoArc:
    """Stand-in when the game has no Arcana system."""

    def amount_bonus(self, w): return 0
    def cooldown_factor(self, w): return 1.0
    def bounces(self, w): return 0
    def crit(self, w): return None
    def freeze_chance(self, w): return 0.0
    def on_hit(self, pr, e): pass
    def on_expire(self, pr): pass


_NOARC = _NoArc()


def arc(g):
    return getattr(g, "arc", None) or _NOARC


class Weapon:
    def __init__(self, wid):
        self.id = wid
        self.level = 1
        self.timer = sec(0.5)
        self.queue = 0
        self.burst_t = 0
        self.volley = 0
        self.dmg_done = 0.0
        self.kills = 0
        self.orbit_t = 0
        self.hits = {}  # persistent per-enemy hit clock (auras, lasers, song)
        self.alive = 0  # live projectiles (pool cap)
        self.fx = {}  # kind-specific persistent state
        self._extra = (None, None)

    @property
    def spec(self):
        return data.WEAPONS[self.id]

    @property
    def kind(self):
        return KIND.get(self.id, "wand")

    @property
    def burst(self):
        return 0 if self.kind in VOLLEY else max(1, round(self.spec["base"]["interval"] * FPS))

    @property
    def maxed(self):
        return self.level >= self.spec["max_level"]

    def extras(self):
        """Level effects parsed from the wiki level text (cached per level)."""
        if self._extra[0] == self.level:
            return self._extra[1]
        ex = {"cd": 0.0, "inv": 0.0, "charges": 0, "keep": 0.0, "explode": 0.4}
        for text in self.spec["level_desc"][1:self.level]:
            for rx, key, mul in _EXTRA:
                m = rx.search(text)
                if m:
                    ex[key] += 1 if mul is None else float(m.group(1)) * mul
            m = re.search(r"(\d+)% chance not to erase", text)
            if m:
                ex["keep"] = int(m.group(1)) / 100
            m = re.search(r"(\d+)% chance to explode", text)
            if m:
                ex["explode"] = int(m.group(1)) / 100
        self._extra = (self.level, ex)
        return ex

    def stats(self, ps, g=None):
        """Final stats after levels and passive multipliers."""
        spec = self.spec
        s = dict(spec["base"])
        for lv in spec["levels"][: self.level - 1]:
            for k, v in lv.items():
                s[k] = s.get(k, 0) + v
        ex = self.extras()
        s["cd"] += ex["cd"]
        ign = IGNORES.get(self.id, ())
        if "might" not in ign:
            s["dmg"] *= ps["might"]
        s["cd"] = max(0.05, s["cd"] * ps["cooldown"])
        if "area" not in ign:
            s["area"] *= ps["area"]
        if "speed" not in ign:
            s["speed"] *= ps["speed"]
        s["dur"] = s.get("dur", 0) * (1 if "dur" in ign else ps["duration"])
        amount = s["amount"]
        if "amount" not in ign:
            amount += ps["amount"] + (arc(g).amount_bonus(self) if g is not None else 0)
        s["amount"] = max(1, int(amount))
        s.update(inv=0.5 + ex["inv"], charges=1 + ex["charges"], keep=ex["keep"],
                 explode=ex["explode"])
        if self.id == "crimson_shroud":
            s["charges"] = 3
        return s

    def update(self, g):
        st = self.stats(g.pstats, g)
        if self.kind == "penta" and not self.fx.get("armed"):  # first wipe after a full cooldown
            self.fx["armed"] = True
            self.timer = sec(st["cd"])
        fn = CUSTOM_UPDATE.get(self.kind)
        if fn:
            fn(self, g, st)
        else:
            generic_update(self, g, st)

    # ---- Laurel / Crimson Shroud hooks consulted by the game --------------
    def blocks_hit(self, g):
        """True if a shield charge absorbs the incoming hit."""
        if self.kind != "shield" or self.fx.get("charges", 0) <= 0:
            return False
        self.fx["charges"] -= 1
        st = self.stats(g.pstats, g)
        p_invuln(g, sec(st["inv"]))
        self.fx["pop"] = 10
        if self.id == "crimson_shroud":  # retaliation blast
            boom(g, self, g.p.x, g.p.y, 30 * g.pstats["might"] + 5 * g.pstats["armor"],
                 44 * PX * g.pstats["area"], 8, kb=2.0)
        g.sfx("zap")
        return True

    def cap_damage(self, dmg):
        return min(dmg, 10) if self.id == "crimson_shroud" else dmg


class Proj:
    __slots__ = (
        "kind", "w", "x", "y", "vx", "vy", "dmg", "life", "pierce", "r",
        "hit", "t", "a", "ox", "oy", "kb", "interval", "extra", "bounces",
        "b", "c", "counted",
    )

    def __init__(self, kind, w, x, y, vx=0.0, vy=0.0, dmg=0.0, life=30,
                 pierce=1, r=4.0, kb=1.0, interval=0):
        self.kind = kind
        self.w = w
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.dmg = dmg
        self.life = life
        self.pierce = pierce
        self.r = r
        self.hit = {}
        self.t = 0
        self.a = 0.0
        self.ox = self.oy = 0.0
        self.kb = kb
        self.interval = interval
        self.extra = 0.0
        self.bounces = 0
        self.b = 0.0
        self.c = 0
        self.counted = False


# ------------------------------------------------------------ shared helpers


def add(g, pr):
    g.projs.append(pr)
    if pr.w is not None:
        pr.w.alive += 1
        pr.counted = True
        pr.bounces = arc(g).bounces(pr.w)
    return pr


def finish(pr, g):
    if pr.counted:
        pr.w.alive -= 1
        pr.counted = False
    if pr.w is not None:
        arc(g).on_expire(pr)


def p_invuln(g, frames):
    fn = getattr(g, "p_invuln", None)
    if fn:
        fn(frames)
    else:
        g.p.inv = max(getattr(g.p, "inv", 0), frames)


def freeze(g, e, frames):
    fn = getattr(g, "freeze_enemy", None)
    if fn:
        fn(e, frames)


def hit(g, w, e, dmg, sx, sy, kb, pr=None):
    """Damage e from weapon w, applying crits, freeze chance and Arcana hooks."""
    if e.dead:
        return
    a = arc(g)
    if w is not None:
        c = a.crit(w)
        chance, mul = c if c is not None else CRIT.get(w.id, (0, 0))
        if chance and random.random() < chance * g.pstats["luck"]:
            dmg *= mul
            if w.id == "bloody_tear":
                g.heal(8)
        fc = a.freeze_chance(w)
        if fc and random.random() < fc * g.pstats["luck"]:
            freeze(g, e, sec(1.0))
    g.damage_enemy(e, dmg, w, sx, sy, kb)
    if pr is not None:
        a.on_hit(pr, e)
    if e.dead and w is not None and w.id == "vicious_hunger" and random.random() < 0.15:
        g.gold += 1  # the eye turns victims into gold
        g.sfx("coin")


def collide(p, g):
    """Damage enemies overlapping p. Returns False once pierce (and bounces) run out."""
    for e in g.query(p.x, p.y, p.r):
        key = id(e)
        if p.interval:
            if g.frame < p.hit.get(key, 0):
                continue
            p.hit[key] = g.frame + p.interval
        else:
            if key in p.hit:
                continue
            p.hit[key] = 1
        hit(g, p.w, e, p.dmg, p.x, p.y, p.kb, p)
        if not p.interval:
            p.pierce -= 1
            if p.pierce <= 0:
                if p.bounces > 0:
                    p.bounces -= 1
                    p.pierce = 1
                    retarget(p, g)
                    return True
                return False
    return True


def retarget(p, g):
    """Waltz of Pearls style bounce: aim at the nearest enemy not yet hit."""
    spd = math.hypot(p.vx, p.vy) or 3 * PX
    for e in g.nearest_enemies(p.x, p.y, 6):
        if id(e) not in p.hit:
            a = math.atan2(e.y - p.y, e.x - p.x)
            p.vx, p.vy = math.cos(a) * spd, math.sin(a) * spd
            return
    p.vx, p.vy = -p.vx, -p.vy


def bounce_collide(p, g):
    """Hit enemies on a per-enemy interval and ricochet off them."""
    for e in g.query(p.x, p.y, p.r):
        key = id(e)
        if g.frame < p.hit.get(key, 0):
            continue
        p.hit[key] = g.frame + p.interval
        hit(g, p.w, e, p.dmg, p.x, p.y, p.kb, p)
        nx, ny = p.x - e.x, p.y - e.y
        d = math.hypot(nx, ny) or 1
        nx, ny = nx / d, ny / d
        dot = p.vx * nx + p.vy * ny
        if dot < 0:
            p.vx -= 2 * dot * nx
            p.vy -= 2 * dot * ny
    return True


def bounce_edges(p, g, pad=4):
    """Reflect off the screen edges. Returns True if it bounced."""
    left, top = g.cam_x + pad, g.cam_y + pad
    right, bottom = g.cam_x + g.W - pad, g.cam_y + g.H - pad
    b = False
    if p.x < left or p.x > right:
        p.vx = -p.vx
        p.x = min(max(p.x, left), right)
        b = True
    if p.y < top or p.y > bottom:
        p.vy = -p.vy
        p.y = min(max(p.y, top), bottom)
        b = True
    return b


def offscreen(p, g, pad=24):
    return (p.x < g.cam_x - pad or p.x > g.cam_x + g.W + pad
            or p.y < g.cam_y - pad or p.y > g.cam_y + g.H + pad)


def boom(g, w, x, y, dmg, r, col=9, kb=1.0):
    pr = Proj("boom", w, x, y, dmg=dmg, life=10, pierce=999, r=r, kb=kb)
    pr.c = col
    g.projs.append(pr)  # explosions don't count against the pool
    return pr


def beam_hits(g, x0, y0, ang, length, width):
    """Enemies along a line segment (sampled with circle queries)."""
    ux, uy = math.cos(ang), math.sin(ang)
    step = max(6.0, width * 1.5)
    seen, out = set(), []
    d = step / 2
    while d < length:
        for e in g.query(x0 + ux * d, y0 + uy * d, width):
            if id(e) not in seen:
                seen.add(id(e))
                out.append(e)
        d += step
    return out


def face_dir(p):
    fx, fy = p.face_x8, p.face_y8
    if not (fx or fy):
        fx = p.face_x
    ln = math.hypot(fx, fy) or 1
    return fx / ln, fy / ln


def spr(key, x, y, rotate=0.0, scale=1.0, flip=False, frame=0):
    """Real weapon sprite if the atlas has it; `frame` picks among its variants."""
    if not art.has(key):
        return False
    u = art._index[key][frame % len(art._index[key])]
    pyxel.blt(x - u[3] / 2, y - u[4] / 2, art._pages[u[0]], u[1], u[2],
              -u[3] if flip else u[3], u[4], art.KEYCOL, rotate, scale)
    return True


def tick(w, g, st, rate=1.0):
    """Advance w's cooldown. True when it elapses (timer restarts)."""
    w.timer -= rate / max(0.1, arc(g).cooldown_factor(w))
    if w.timer <= 0:
        w.timer = sec(st["cd"])
        return True
    return False


# ------------------------------------------------------------ update loops


def generic_update(w, g, st, rate=1.0):
    kind = w.kind
    if w.queue > 0:
        w.burst_t -= 1
        if w.burst_t <= 0:
            n = st["amount"]
            spawn(w, g, st, n - w.queue, n)
            w.queue -= 1
            w.burst_t = w.burst
        return
    if tick(w, g, st, rate):
        w.volley += 1
        n = st["amount"]
        if w.burst == 0:
            for i in range(n):
                spawn(w, g, st, i, n)
        else:
            w.queue = n
            w.burst_t = 0
        if kind in ("bible", "vespers"):  # cooldown starts after the orbit ends
            w.timer += sec(st["dur"])
        g.sfx_fire(kind)


def moving_update(w, g, st):
    """Vento Sacro / Celestial Dusting: faster cooldown while moving."""
    p = g.p
    w.fx["walk"] = w.fx.get("walk", 0) + 1 if p.moving else 0
    rate = 1 + g.pstats["move"] if p.moving else 1.0
    generic_update(w, g, st, rate)


def aura_update(w, g, st):
    """Garlic / Soul Eater: damage everything in radius every `cd`."""
    p = g.p
    r = 22 * PX * st["area"]
    w.orbit_t += 1
    interval = sec(st["cd"])
    soul = w.id == "soul_eater"
    for e in g.query(p.x, p.y, r):
        key = id(e)
        if g.frame < w.hits.get(key, 0):
            continue
        w.hits[key] = g.frame + interval
        hit(g, w, e, st["dmg"], p.x, p.y, st["kb"] * 0.7)
        if soul and not e.prop:
            g.heal(0.2)
    if w.orbit_t % 120 == 0:  # forget dead enemies
        alive = {id(e) for e in g.enemies}
        w.hits = {k: v for k, v in w.hits.items() if k in alive}
    w.fx["r"] = r


def bird_update(w, g, st):
    """Peachone / Ebony Wings / Vandalier: a bird bombards revolving zones."""
    p, fx = g.p, w.fx
    if "ang" not in fx:
        dirs = {"peachone": [1], "ebony_wings": [-1], "vandalier": [1, -1]}[w.id]
        fx.update(bx=p.x, by=p.y - 20, dirs=dirs, ang=[i * math.pi for i in range(len(dirs))],
                  q=0, zones=[])
    for k, d in enumerate(fx["dirs"]):
        fx["ang"][k] += d * 0.035 * st["speed"]
    R = 50 * PX
    fx["zones"] = [(p.x + math.cos(a) * R, p.y + math.sin(a) * R * 0.75) for a in fx["ang"]]
    # the bird trails the first zone, slower than the player
    tx = p.x + math.cos(fx["ang"][0] + math.pi) * 22 * PX
    ty = p.y - 16 * PX + math.sin(g.frame * 0.1) * 3
    fx["bx"] += (tx - fx["bx"]) * 0.06
    fx["by"] += (ty - fx["by"]) * 0.06
    if tick(w, g, st):
        fx["q"] += st["amount"]
        g.sfx("shot")
    if fx["q"] > 0 and w.alive < st["pool"]:
        fx["q"] -= 1
        zx, zy = fx["zones"][fx["q"] % len(fx["zones"])]
        j = 10 * PX * st["area"]
        pr = Proj("bomb", w, fx["bx"], fx["by"], dmg=st["dmg"], life=16, pierce=999,
                  r=0, kb=st["kb"])
        pr.ox, pr.oy = zx + random.uniform(-j, j), zy + random.uniform(-j, j)
        pr.extra = 5 * PX * st["area"]
        pr.c = {"peachone": 7, "ebony_wings": 2}.get(w.id, 14 if fx["q"] % 2 else 12)
        add(g, pr)


def lasers_update(w, g, st):
    """Phieraggi: rotating lasers, up for a second each cooldown."""
    p, fx = g.p, w.fx
    fx["ang"] = fx.get("ang", 0.0) + 0.05 * st["speed"]
    if tick(w, g, st):
        fx["on"] = sec(1.0)
        g.sfx("zap")
    fx["n"] = st["amount"]
    fx["len"] = 0.45 * g.W
    fx["wid"] = 3 * PX * st["area"]
    if fx.get("on", 0) <= 0:
        return
    fx["on"] -= 1
    if g.frame % 3:
        return
    interval = sec(0.3)
    for k in range(fx["n"]):
        a = fx["ang"] + k * TAU / fx["n"]
        for e in beam_hits(g, p.x, p.y, a, fx["len"], fx["wid"]):
            key = id(e)
            if g.frame < w.hits.get(key, 0):
                continue
            w.hits[key] = g.frame + interval
            hit(g, w, e, st["dmg"], p.x, p.y, st["kb"])


def pinion_update(w, g, st):
    """Shadow Pinion / Valkyrie Turner: drop drills while moving, fire on stop."""
    p, fx = g.p, w.fx
    was = fx.get("moving", False)
    fx["moving"] = p.moving
    if fx.get("cool", 0) > 0:
        fx["cool"] -= 1
    if p.moving:
        fx["spawn"] = fx.get("spawn", 0) - g.pstats["move"]
        cap = min(st["pool"], st["amount"] * 5)
        if fx["spawn"] <= 0 and fx.get("cool", 0) <= 0 and w.alive < cap:
            fx["spawn"] = sec(0.35)
            ux, uy = face_dir(p)
            pr = Proj("pinion", w, p.x - ux * 14 * PX, p.y - uy * 14 * PX,
                      -ux * 0.3 * PX, -uy * 0.3 * PX, st["dmg"], sec(st["dur"] + 3), 999,
                      6 * PX * st["area"], st["kb"], interval=sec(0.5))
            pr.ox, pr.oy = -ux, -uy
            pr.b = 0.04 * PX * st["speed"]
            add(g, pr)
    elif was:  # just stopped: launch everything forward
        ux, uy = face_dir(p)
        v = 6 * PX * st["speed"]
        launched = 0
        for pr in g.projs:
            if pr.w is w and pr.c == 0:
                pr.c = 1
                pr.vx, pr.vy = ux * v, uy * v
                pr.life = sec(0.5 * st["area"] + 0.3)
                pr.interval = 0
                pr.hit = {}
                launched += 1
        if launched:
            fx["cool"] = sec(st["cd"] * 0.25)
            g.sfx("shot")


def shield_update(w, g, st):
    """Laurel / Crimson Shroud: refill shield charges every cooldown."""
    fx = w.fx
    fx["max"] = st["charges"]
    if fx.get("pop", 0) > 0:
        fx["pop"] -= 1
    if tick(w, g, st) and fx.get("charges", 0) < fx["max"]:
        fx["charges"] = fx["max"]


CUSTOM_UPDATE = {
    "garlic": aura_update, "soul": aura_update, "bird": bird_update,
    "lasers": lasers_update, "pinion": pinion_update, "shield": shield_update,
    "vento": moving_update, "flower": moving_update,
}


# ---------------------------------------------------------------- spawning


def spawn(w, g, st, i, n):
    if w.alive >= st["pool"]:
        return
    fn = SPAWN.get(w.kind)
    if fn:
        fn(w, g, st, i, n)


def sp_whip(w, g, st, i, n):
    p = g.p
    side = p.face_x if i % 2 == 0 else -p.face_x
    pr = Proj(w.kind, w, p.x, p.y, dmg=st["dmg"], life=6, pierce=999, r=0, kb=st["kb"])
    pr.a = side
    pr.oy = (-6 + (i // 2) * 10 - (i % 2) * 4) * PX
    pr.extra = st["area"]
    add(g, pr)


def sp_wand(w, g, st, i, n):
    p = g.p
    targets = g.nearest_enemies(p.x, p.y, max(1, n))
    if not targets:
        return
    e = targets[i % len(targets)]
    ang = math.atan2(e.y - p.y, e.x - p.x) + random.uniform(-0.05, 0.05)
    v = min(14.0, 3.2 * PX * st["speed"])
    add(g, Proj(w.kind, w, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v, st["dmg"],
                sec(3), st["pierce"], 3 * PX * st["area"], st["kb"]))


def sp_knife(w, g, st, i, n):
    p = g.p
    fx, fy = face_dir(p)
    v = min(16.0, 5.5 * PX * st["speed"])
    j = random.uniform(-6, 6) * PX
    pr = Proj(w.kind, w, p.x - fy * j, p.y + fx * j, fx * v, fy * v, st["dmg"],
              sec(1.2), st["pierce"], 3 * PX * st["area"], st["kb"])
    pr.a = math.degrees(math.atan2(fy, fx))
    add(g, pr)


def sp_axe(w, g, st, i, n):
    p = g.p
    spread = (i - (n - 1) / 2) * 1.1 + random.uniform(-0.4, 0.4)
    add(g, Proj("axe", w, p.x, p.y, spread * PX * st["speed"], -5.2 * PX * st["speed"],
                st["dmg"], sec(3), st["pierce"], 7 * PX * st["area"], st["kb"]))


def sp_spiral(w, g, st, i, n):
    p = g.p
    ang = w.volley * 0.35 + i * TAU / n
    v = 2.4 * PX * st["speed"]
    pr = Proj("spiral", w, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v, st["dmg"],
              sec(2.5), 999, 9 * PX * st["area"], st["kb"])
    pr.a = ang
    pr.extra = st["area"]
    add(g, pr)


def sp_cross(w, g, st, i, n):
    p = g.p
    targets = g.nearest_enemies(p.x, p.y, max(1, n))
    if targets:
        e = targets[i % len(targets)]
        ang = math.atan2(e.y - p.y, e.x - p.x)
    else:
        ang = random.uniform(0, TAU)
    pr = Proj(w.kind, w, p.x, p.y, math.cos(ang), math.sin(ang), st["dmg"], sec(3.5), 999,
              (9 if w.kind == "heaven" else 6) * PX * st["area"], st["kb"], interval=sec(0.5))
    pr.extra = 5.0 * PX * st["speed"]  # signed speed along (vx, vy)
    pr.b = st["area"]
    add(g, pr)


def sp_bible(w, g, st, i, n):
    p = g.p
    pr = Proj(w.kind, w, p.x, p.y, dmg=st["dmg"], life=sec(st["dur"]), pierce=999,
              r=5 * PX * st["area"], kb=st["kb"], interval=sec(0.5))
    pr.a = i * TAU / n
    pr.c = i  # place in the ring: themes with several sprite variants give each its own
    pr.extra = 38 * PX * st["area"]  # orbit radius
    pr.ox = st["speed"]
    add(g, pr)


def sp_fire(w, g, st, i, n):
    p = g.p
    e = g.random_enemy_near(p.x, p.y)
    ang = math.atan2(e.y - p.y, e.x - p.x) if e else random.uniform(0, TAU)
    ang += (i - (n - 1) / 2) * 0.12
    big = w.kind == "hellfire"
    v = (1.6 if big else 2.9) * PX * st["speed"]
    add(g, Proj(w.kind, w, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v, st["dmg"],
                sec(4), 999 if big else st["pierce"], (12 if big else 5) * PX * st["area"],
                st["kb"]))


def sp_water(w, g, st, i, n):
    p = g.p
    if w.kind == "borra":  # clockwise ring of bottles
        a = (w.volley * n + i) * 0.9
        d = random.uniform(30, 70) * PX
        tx, ty = p.x + math.cos(a) * d, p.y + math.sin(a) * d
    else:
        e = g.random_enemy_near(p.x, p.y, 120 * PX) if i == 0 else None
        if e:
            tx, ty = e.x, e.y
        else:
            a = random.uniform(0, TAU)
            d = random.uniform(30, 90) * PX
            tx, ty = p.x + math.cos(a) * d, p.y + math.sin(a) * d
    pr = Proj(w.kind, w, p.x, p.y, dmg=st["dmg"], life=sec(st["dur"]) + 12, pierce=999,
              r=0, kb=0.2, interval=sec(0.5))
    pr.ox, pr.oy = tx, ty
    pr.extra = 14 * PX * st["area"]
    add(g, pr)


def sp_ring(w, g, st, i, n):
    e = g.random_enemy_on_screen()
    if not e:
        return
    r = 8 * PX * st["area"]
    add(g, Proj(w.kind, w, e.x, e.y, dmg=st["dmg"], life=8, pierce=999, r=r, kb=st["kb"]))
    if w.kind == "thunder":  # second strike on the same spot
        pr2 = Proj("thunder", w, e.x, e.y, dmg=st["dmg"], life=14, pierce=999, r=r, kb=st["kb"])
        pr2.t = -6
        add(g, pr2)


def sp_rune(w, g, st, i, n):
    p = g.p
    ang = random.uniform(0, TAU)
    v = min(12.0, 4.0 * PX * st["speed"])
    pr = Proj(w.kind, w, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v, st["dmg"],
              sec(st["dur"]), 999, 5 * PX * st["area"], st["kb"], interval=sec(0.5))
    pr.extra = st["area"]
    add(g, pr)


def sp_penta(w, g, st, i, n):
    pr = Proj("penta", w, g.p.x, g.p.y, dmg=0, life=40, pierce=999, r=0, kb=0)
    pr.extra = st["keep"]
    add(g, pr)
    g.sfx("rosary")


def sp_gun(w, g, st, i, n):
    p = g.p
    if w.id == "eight_the_sparrow":  # toward the four screen corners
        base = math.atan2(g.H / 2, g.W / 2)
        angs = [base, math.pi - base, math.pi + base, -base]
        col = 12
    else:  # four ordinal directions
        angs = [math.pi / 4 + k * math.pi / 2 for k in range(4)]
        col = 8
    v = min(14.0, 6 * PX * st["speed"])
    for a in angs:
        pr = Proj("gun", w, p.x, p.y, math.cos(a) * v, math.sin(a) * v, st["dmg"], sec(1.6),
                  st["pierce"], 3 * PX * st["area"], st["kb"])
        pr.c = col
        add(g, pr)


def sp_cat(w, g, st, i, n):
    p = g.p
    left, top = g.cam_x + 12, g.cam_y + 12
    side = random.randrange(4)
    if side == 0:
        x, y = left, random.uniform(top, top + g.H - 24)
    elif side == 1:
        x, y = left + g.W - 24, random.uniform(top, top + g.H - 24)
    elif side == 2:
        x, y = random.uniform(left, left + g.W - 24), top
    else:
        x, y = random.uniform(left, left + g.W - 24), top + g.H - 24
    a = math.atan2(p.y - y, p.x - x) + random.uniform(-0.7, 0.7)
    v = 2.2 * PX * st["speed"]
    pr = Proj("cat", w, x, y, math.cos(a) * v, math.sin(a) * v, st["dmg"], sec(st["dur"]),
              999, 9 * PX * st["area"], st["kb"], interval=sec(0.5))
    pr.b = sec(1.5)
    add(g, pr)


def sp_song(w, g, st, i, n):
    pr = Proj("song", w, g.p.x, g.p.y, dmg=st["dmg"], life=sec(max(0.5, st["dur"])),
              pierce=999, r=0, kb=st["kb"])
    pr.extra = 16 * PX * st["area"]  # column half-width
    add(g, pr)
    g.sfx("zap")


def sp_lancet(w, g, st, i, n):
    p = g.p
    k = (w.volley - 1) % 12
    pr = Proj("lance", w, p.x, p.y, dmg=0, life=8, pierce=999, r=0, kb=0)
    pr.a = -math.pi / 2 + k * TAU / 12
    pr.extra = st["dur"]
    add(g, pr)
    if w.id == "infinite_corridor" and k == 0 and w.volley > 1:
        for e in list(g.enemies):
            if e.dead or e.prop or e.reaper or not on_screen(g, e):
                continue
            hit(g, w, e, e.hp / 2, p.x, p.y, 0)
        add(g, Proj("rainbow", w, p.x, p.y, life=20, pierce=999, r=0))
        g.sfx("rosary")


def sp_vento(w, g, st, i, n):
    p = g.p
    walk = min(5, w.fx.get("walk", 0) // 60)  # up to +5 from walking nonstop
    pr = Proj("slash", w, p.x, p.y, dmg=st["dmg"] + walk * g.pstats["might"],
              life=sec(st["dur"]) + 3, pierce=999, r=0, kb=st["kb"])
    pr.a = -p.face_x if (w.id == "fuwalafuwaloo" and i % 2) else p.face_x
    pr.oy = random.uniform(-14, 14) * PX
    pr.extra = 30 * PX * st["area"] * st["speed"]  # reach
    pr.b = 10 * PX * st["area"]  # height
    pr.c = 8 if w.id == "fuwalafuwaloo" else 6
    add(g, pr)
    if w.id == "fuwalafuwaloo" and i == 0:
        ring = Proj("fring", w, p.x, p.y, dmg=st["dmg"], life=12, pierce=999, r=0, kb=st["kb"])
        ring.extra = 34 * PX * st["area"]
        add(g, ring)


def sp_bone(w, g, st, i, n):
    p = g.p
    a = random.uniform(0, TAU)
    v = 3.2 * PX * st["speed"]
    add(g, Proj("bone", w, p.x, p.y, math.cos(a) * v, math.sin(a) * v, st["dmg"],
                sec(st["dur"]), 999, 4 * PX * st["area"], st["kb"], interval=sec(0.3)))


def sp_cherry(w, g, st, i, n):
    p = g.p
    t = g.nearest_enemies(p.x, p.y, 1)
    a = math.atan2(t[0].y - p.y, t[0].x - p.x) if t else random.uniform(0, TAU)
    a += random.uniform(-0.2, 0.2)
    v = 4 * PX * st["speed"]
    pr = Proj("cherry", w, p.x, p.y, math.cos(a) * v, math.sin(a) * v, st["dmg"],
              sec(st["dur"] + 0.5), 999, 5 * PX * st["area"], st["kb"], interval=sec(0.3))
    pr.b = st["explode"]
    pr.extra = st["area"]
    add(g, pr)


def sp_cart(w, g, st, i, n):
    if i:  # Amount is the bounce count, not extra carts
        return
    p = g.p
    v = 3.5 * PX * st["speed"]
    pr = Proj("cart", w, p.x, p.y, p.face_x * v, 0, st["dmg"], sec(10), 999,
              10 * PX * st["area"], st["kb"], interval=sec(0.4))
    pr.c = max(1, n - 1)  # bounces left
    pr.extra = st["area"]
    add(g, pr)


def sp_flower(w, g, st, i, n):
    p = g.p
    fx, fy = face_dir(p)
    a = math.atan2(-fy, -fx) + random.uniform(-0.5, 0.5)
    v = 3 * PX * st["speed"]
    pr = Proj("flower", w, p.x, p.y, math.cos(a) * v, math.sin(a) * v, st["dmg"],
              sec(1.5 + st["dur"]), 999, 5 * PX * st["area"], st["kb"], interval=sec(0.5))
    pr.extra = st["area"]
    add(g, pr)


def sp_robba(w, g, st, i, n):
    a = random.uniform(0.35, math.pi - 0.35)
    v = 4 * PX * st["speed"]
    pr = Proj("robba", w, g.cam_x + g.W / 2 + random.uniform(-20, 20), g.cam_y - 8,
              math.cos(a) * v, math.sin(a) * v, st["dmg"], sec(st["dur"] + 1.5), 999,
              7 * PX * st["area"], st["kb"], interval=sec(0.3))
    pr.c = random.randrange(3)
    add(g, pr)


def sp_bracelet(w, g, st, i, n):
    p = g.p
    e = g.random_enemy_near(p.x, p.y)
    base = math.atan2(e.y - p.y, e.x - p.x) if e else random.uniform(0, TAU)
    v = 5 * PX * st["speed"]
    a = base + (i - (n - 1) / 2) * 0.15
    pr = Proj("bracelet", w, p.x, p.y, math.cos(a) * v, math.sin(a) * v, st["dmg"],
              sec(st["dur"]) + 6, st["pierce"], 4 * PX * st["area"], st["kb"])
    pr.c = {"bracelet": 6, "bi_bracelet": 12, "tri_bracelet": 9}[w.id]
    add(g, pr)


SPAWN = {
    "whip": sp_whip, "tear": sp_whip, "wand": sp_wand, "holy": sp_wand,
    "knife": sp_knife, "edge": sp_knife, "axe": sp_axe, "spiral": sp_spiral,
    "cross": sp_cross, "heaven": sp_cross, "bible": sp_bible, "vespers": sp_bible,
    "fire": sp_fire, "hellfire": sp_fire, "water": sp_water, "borra": sp_water,
    "ring": sp_ring, "thunder": sp_ring, "rune": sp_rune, "nofuture": sp_rune,
    "penta": sp_penta, "gun": sp_gun, "cat": sp_cat, "song": sp_song, "lancet": sp_lancet,
    "vento": sp_vento, "bone": sp_bone, "cherry": sp_cherry, "cart": sp_cart,
    "flower": sp_flower, "robba": sp_robba, "bracelet": sp_bracelet,
}


def on_screen(g, e, pad=8):
    return (g.cam_x - pad <= e.x <= g.cam_x + g.W + pad
            and g.cam_y - pad <= e.y <= g.cam_y + g.H + pad)


# ---------------------------------------------------------------- updates


def update_proj(pr, g):
    """Advance one projectile. Returns False when it should be removed."""
    pr.t += 1
    pr.life -= 1
    if pr.life <= 0:
        _expire(pr, g)
        finish(pr, g)
        return False
    fn = UPDATE.get(pr.kind, u_straight)
    if fn(pr, g):
        return True
    finish(pr, g)
    return False


def _expire(pr, g):
    """End-of-life effects."""
    k = pr.kind
    if k == "cherry" and random.random() < pr.b * g.pstats["luck"]:
        boom(g, pr.w, pr.x, pr.y, pr.dmg, 12 * PX * pr.extra, 8)
        g.sfx("pop")
    elif k == "flower":
        boom(g, pr.w, pr.x, pr.y, pr.dmg, 10 * PX * pr.extra, 14, kb=0.3)
    elif k == "cart":
        boom(g, pr.w, pr.x, pr.y, pr.dmg, 24 * PX * pr.extra, 9)


def u_whip(pr, g):
    if pr.t == 2:  # hitbox active on frame 2 only
        p = g.p
        w, h = 56 * PX * pr.extra, 14 * PX * pr.extra
        x0 = p.x if pr.a > 0 else p.x - w
        y0 = p.y + pr.oy - h / 2
        for e in g.query_rect(x0, y0, w, h):
            hit(g, pr.w, e, pr.dmg, p.x, p.y, pr.kb, pr)
    return True


def u_bible(pr, g):
    p = g.p
    pr.a += 0.11 * pr.ox
    pr.x = p.x + math.cos(pr.a) * pr.extra
    pr.y = p.y + math.sin(pr.a) * pr.extra
    return collide(pr, g)


def u_axe(pr, g):
    pr.vy += 0.22 * PX
    pr.x += pr.vx
    pr.y += pr.vy
    return collide(pr, g)


def u_cross(pr, g):
    pr.extra -= 0.16 * PX
    pr.x += pr.vx * pr.extra
    pr.y += pr.vy * pr.extra
    if pr.extra < 0 and offscreen(pr, g, 40):
        return False
    return collide(pr, g)


def u_water(pr, g):
    p = g.p
    if pr.t < 12:  # flask in flight
        pr.x += (pr.ox - pr.x) / (13 - pr.t)
        pr.y += (pr.oy - pr.y) / (13 - pr.t)
        return True
    if pr.t == 12:
        pr.x, pr.y = pr.ox, pr.oy
        pr.r = pr.extra
        g.sfx("splash")
    if pr.kind == "borra":  # creep toward the player and grow
        dx, dy = p.x - pr.x, p.y - pr.y
        d = math.hypot(dx, dy) or 1
        pr.x += dx / d * 0.5 * PX
        pr.y += dy / d * 0.5 * PX
        pr.r = min(pr.extra * 1.5, pr.r + 0.04 * PX)
    collide(pr, g)
    return True


def u_ring(pr, g):
    if pr.t == 1:
        collide(pr, g)
        g.sfx("zap")
    return True


def u_rune(pr, g):
    pr.x += pr.vx
    pr.y += pr.vy
    if bounce_edges(pr, g) and pr.kind == "nofuture":
        boom(g, pr.w, pr.x, pr.y, pr.dmg, 18 * PX * pr.extra, 12)
    return collide(pr, g)


def u_boom(pr, g):
    if pr.t == 1:
        collide(pr, g)
    return True


def u_penta(pr, g):
    p = g.p
    pr.x, pr.y = p.x, p.y
    if pr.t != 14:
        return True
    w = pr.w
    moon = w is not None and w.id == "gorgeous_moon"
    for e in list(g.enemies):
        if e.dead or e.prop or e.reaper or not on_screen(g, e):
            continue
        if getattr(e, "res_kill", 0) >= 1:
            continue
        g.damage_enemy(e, max(e.hp, e.maxhp), w, p.x, p.y, 0)
        if moon and e.dead and hasattr(g, "drop_gem"):
            g.drop_gem(e.x, e.y, 1)
    if moon:
        for it in g.pickups:
            if it.kind == "gem":
                it.fly = True
    else:
        keep = pr.extra * g.pstats["luck"]
        for it in [it for it in g.pickups if it.kind != "chest" and on_screen(g, it)]:
            if random.random() >= keep:
                _remove_pickup(g, it)
    if hasattr(g, "flash_t"):
        g.flash_t = max(g.flash_t, 8)
    return True


def _remove_pickup(g, it):
    fn = getattr(g, "remove_pickup", None)
    if fn:
        fn(it)
        return
    if it in g.pickups:
        g.pickups.remove(it)
        if it.kind == "gem" and hasattr(g, "gem_count") and it is not getattr(g, "big_gem", None):
            g.gem_count -= 1


def u_bomb(pr, g):
    if pr.t < 8:
        pr.x += (pr.ox - pr.x) / (9 - pr.t)
        pr.y += (pr.oy - pr.y) / (9 - pr.t)
    elif pr.t == 8:
        pr.x, pr.y = pr.ox, pr.oy
        pr.r = pr.extra
        collide(pr, g)
    return True


def u_cat(pr, g):
    pr.b -= 1
    if pr.b <= 0:
        pr.b = sec(1.5)
        if random.random() < 0.5:
            a = math.atan2(pr.vy, pr.vx) + random.uniform(-1.2, 1.2)
            v = math.hypot(pr.vx, pr.vy)
            pr.vx, pr.vy = math.cos(a) * v, math.sin(a) * v
    pr.x += pr.vx
    pr.y += pr.vy
    bounce_edges(pr, g, 10)
    # two cats meeting may start a scuffle cloud
    if g.frame % 15 == 0 and pr.c == 0:
        for o in g.projs:
            if o is not pr and o.kind == "cat" and o.w is pr.w and o.c == 0 \
                    and abs(o.x - pr.x) < 14 * PX and abs(o.y - pr.y) < 14 * PX \
                    and random.random() < 0.3:
                pr.c = o.c = 1
                fight = Proj("scuffle", pr.w, (pr.x + o.x) / 2, (pr.y + o.y) / 2, dmg=pr.dmg,
                             life=sec(2), pierce=999, r=22 * PX, kb=0.5, interval=sec(0.3))
                g.projs.append(fight)
                break
    return collide(pr, g)


def u_scuffle(pr, g):
    collide(pr, g)
    return True


def u_song(pr, g):
    p, w = g.p, pr.w
    pr.x, pr.y = p.x, p.y
    hw = pr.extra
    interval = sec(1.0)
    slow = w is not None and w.id == "mannajja"
    for e in g.query_rect(p.x - hw, g.cam_y, hw * 2, g.H):
        key = id(e)
        if g.frame < w.hits.get(key, 0):
            continue
        w.hits[key] = g.frame + interval
        hit(g, w, e, pr.dmg, p.x, e.y, pr.kb, pr)
        if slow and hasattr(e, "spd") and not e.reaper:
            e.spd = max(0.2, e.spd * 0.95)
    return True


def u_pinion(pr, g):
    if pr.c == 0:  # trailing: accelerate slowly backwards
        pr.vx += pr.ox * pr.b
        pr.vy += pr.oy * pr.b
    pr.x += pr.vx
    pr.y += pr.vy
    return collide(pr, g)


def u_lance(pr, g):
    if pr.t == 1:
        p = g.p
        frames = sec(max(0.5, pr.extra))
        for e in beam_hits(g, p.x, p.y, pr.a, 0.55 * g.W, 4 * PX):
            if not e.prop:
                freeze(g, e, frames)
                arc(g).on_hit(pr, e)
        g.sfx("freeze")
    pr.x, pr.y = g.p.x, g.p.y
    return True


def u_follow(pr, g):
    pr.x, pr.y = g.p.x, g.p.y
    return True


def u_slash(pr, g):
    p = g.p
    L, h = pr.extra, pr.b
    x0 = p.x if pr.a > 0 else p.x - L
    for e in g.query_rect(x0, p.y + pr.oy - h / 2, L, h):
        if id(e) not in pr.hit:
            pr.hit[id(e)] = 1
            hit(g, pr.w, e, pr.dmg, p.x, p.y, pr.kb, pr)
    return True


def u_fring(pr, g):
    p = g.p
    R = pr.extra
    band = 10 * PX
    for e in g.query(p.x, p.y, R + band):
        if id(e) in pr.hit:
            continue
        if math.hypot(e.x - p.x, e.y - p.y) < R - band:
            continue
        pr.hit[id(e)] = 1
        hit(g, pr.w, e, pr.dmg, p.x, p.y, pr.kb, pr)
    return True


def u_bouncer(pr, g):
    """Bone / Cherry Bomb: straight line, ricochet off enemies and screen edges."""
    pr.x += pr.vx
    pr.y += pr.vy
    if pr.kind == "cherry":
        pr.vx *= 0.975
        pr.vy *= 0.975
    bounce_edges(pr, g)
    return bounce_collide(pr, g)


def u_cart(pr, g):
    pr.x += pr.vx
    left, right = g.cam_x + 10, g.cam_x + g.W - 10
    if pr.x < left or pr.x > right:
        pr.c -= 1
        if pr.c < 0:
            _expire(pr, g)
            return False
        pr.vx = -pr.vx
        pr.x = min(max(pr.x, left), right)
    return collide(pr, g)


def u_flower(pr, g):
    if pr.life < 20:
        pr.vx *= 0.9
        pr.vy *= 0.9
    pr.x += pr.vx
    pr.y += pr.vy
    bounce_edges(pr, g)
    return collide(pr, g)


def u_robba(pr, g):
    pr.x += pr.vx
    pr.y += pr.vy
    if pr.t > 10 and offscreen(pr, g, 16):
        return False
    return bounce_collide(pr, g)


def u_straight(pr, g):
    """Wand, knife, fire, spiral, guns, bracelets."""
    pr.x += pr.vx
    pr.y += pr.vy
    if pr.kind == "spiral":
        pr.a += 0.35
    if offscreen(pr, g, 30):
        return False
    return collide(pr, g)


UPDATE = {
    "whip": u_whip, "tear": u_whip, "bible": u_bible, "vespers": u_bible, "axe": u_axe,
    "cross": u_cross, "heaven": u_cross, "water": u_water, "borra": u_water,
    "ring": u_ring, "thunder": u_ring, "rune": u_rune, "nofuture": u_rune,
    "boom": u_boom, "penta": u_penta, "bomb": u_bomb, "cat": u_cat, "scuffle": u_scuffle,
    "song": u_song, "pinion": u_pinion, "lance": u_lance, "rainbow": u_follow,
    "slash": u_slash, "fring": u_fring, "bone": u_bouncer, "cherry": u_bouncer,
    "cart": u_cart, "flower": u_flower, "robba": u_robba,
}


# ------------------------------------------------------------------ draws


def draw_proj(pr, g):
    fn = (art.MODE == "90s" and fx90s.DRAW.get(pr.kind)) or DRAW.get(pr.kind)
    if fn:
        fn(pr, g)


def d_whip(pr, g):
    t = pr.t
    if t > 3:
        return
    p = g.p
    area = pr.extra
    w = 56 * PX * area
    side = pr.a
    cy = p.y + pr.oy
    col = 8 if pr.kind == "tear" else 7
    shade = 2 if pr.kind == "tear" else 13
    x0 = p.x + side * 6 * PX
    x1 = p.x + side * w
    hh = 6 * PX * area * (1.2 - t * 0.25)
    pyxel.tri(x0, cy - 1, x1, cy - hh, x1, cy + hh * 0.4, shade)
    pyxel.tri(x0, cy, x1, cy - hh * 0.6, x1, cy + hh * 0.2, col)
    pyxel.line(x0, cy, x1, cy - hh * 0.2, 7)


def d_wand(pr, g):
    x, y = pr.x, pr.y
    c = 12 if pr.kind == "wand" else 6
    pyxel.circ(x, y, 2.5 * PX, c)
    pyxel.circ(x, y, 1.2 * PX, 7)
    pyxel.line(x, y, x - pr.vx * 1.5, y - pr.vy * 1.5, c)
    pyxel.pset(x - pr.vx * 2.5, y - pr.vy * 2.5, 5)


def d_knife(pr, g):
    x, y = pr.x, pr.y
    if spr("wspr:knife", x, y, rotate=pr.a, scale=0.7):
        return
    ln = math.hypot(pr.vx, pr.vy) or 1
    ux, uy = pr.vx / ln, pr.vy / ln
    pyxel.line(x - ux * 5 * PX, y - uy * 5 * PX, x + ux * 3 * PX, y + uy * 3 * PX, 7)
    pyxel.line(x - ux * 7 * PX, y - uy * 7 * PX, x - ux * 5 * PX, y - uy * 5 * PX, 4)


def d_axe(pr, g):
    if not spr("wspr:axe", pr.x, pr.y, rotate=pr.t * 24, scale=1.2):
        sprites.draw("axe", pr.x, pr.y, rotate=pr.t * 24, scale=PX)


def d_spiral(pr, g):
    x, y = pr.x, pr.y
    if spr("wspr:death_spiral", x, y, rotate=math.degrees(pr.a), scale=1.3 * pr.extra):
        return
    for j in range(9):
        aa = pr.a + j * 0.3
        rr = (7 - abs(j - 4) * 0.5) * PX
        pyxel.pset(x + math.cos(aa) * rr, y + math.sin(aa) * rr, 8)
        pyxel.pset(x + math.cos(aa) * (rr - 1.5), y + math.sin(aa) * (rr - 1.5), 2)
    pyxel.line(x, y, x - math.cos(pr.a + 1.2) * 6 * PX, y - math.sin(pr.a + 1.2) * 6 * PX, 4)


def d_cross(pr, g):
    key = "wspr:cross" if pr.kind == "cross" else "wspr:heaven_sword"
    sc = pr.b * (1.0 if pr.kind == "cross" else 1.8)
    if not spr(key, pr.x, pr.y, rotate=pr.t * 30, scale=sc):
        sprites.draw("cross", pr.x, pr.y, rotate=pr.t * 30, scale=PX * sc)


def d_bible(pr, g):
    key = "wspr:king_bible" if pr.kind == "bible" else "wspr:unholy_vespers"
    if spr(key, pr.x, pr.y, scale=max(0.8, pr.r / (6 * PX)), frame=pr.c):
        return
    if pr.kind == "vespers":
        pyxel.pal(12, 8)
    sprites.draw("bible", pr.x, pr.y, scale=max(PX, pr.r / 5))
    pyxel.pal()


def d_fire(pr, g):
    x, y, r = pr.x, pr.y, pr.r
    pyxel.circ(x, y, r, 8)
    pyxel.circ(x - pr.vx * 0.5, y - pr.vy * 0.5, r * 0.7, 9)
    pyxel.circ(x, y, r * 0.4, 10)
    for j in range(2):
        pyxel.pset(x - pr.vx * (3 + j * 2) + random.uniform(-2, 2),
                   y - pr.vy * (3 + j * 2) + random.uniform(-2, 2), 9)


def d_water(pr, g):
    x, y, t = pr.x, pr.y, pr.t
    if t < 12:
        pyxel.rect(x - 2 * PX, y - 3 * PX, 4 * PX, 5 * PX, 12)
        pyxel.pset(x, y - 4 * PX, 7)
        return
    r = pr.r
    c = 12 if pr.kind == "water" else 6
    pyxel.dither(0.55)
    pyxel.elli(x - r, y - r * 0.6, r * 2, r * 1.2, c)
    pyxel.dither(1.0)
    for j in range(4):
        a = t * 0.2 + j * 1.6
        pyxel.circb(x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.3, 1 + (t + j * 3) % 4, 6)
    pyxel.ellib(x - r, y - r * 0.6, r * 2, r * 1.2, 7 if pr.kind == "borra" else 6)


def d_ring(pr, g):
    t = pr.t
    if t < 1:  # delayed second strike: closing circle
        pyxel.circb(pr.x, pr.y, pr.r * (1 - t / 6.0), 9)
        return
    x, y = pr.x, pr.y
    c = 10 if pr.kind == "ring" else 9
    if t < 5:
        yy, xx = y - 200, x
        while yy < y:
            nx = x + random.uniform(-6, 6)
            ny = min(y, yy + random.uniform(10, 24))
            pyxel.line(xx, yy, nx, ny, 7 if t < 3 else c)
            pyxel.line(xx + 1, yy, nx + 1, ny, c)
            xx, yy = nx, ny
    pyxel.circb(x, y, pr.r * (0.5 + t * 0.08), c)
    if t < 3:
        pyxel.circ(x, y, pr.r * 0.6, 7)


def d_rune(pr, g):
    x, y = pr.x, pr.y
    if pr.kind == "nofuture":
        pyxel.line(x - pr.vx * 2, y - pr.vy * 2, x, y, 6)
        pyxel.line(x - pr.vx * 1.2, y - pr.vy * 1.2 + 1, x, y + 1, 12)
        pyxel.circ(x, y, 2 * PX, 7)
        return
    if not spr("wspr:runetracer", x, y, scale=pr.extra):
        sprites.draw("rune", x, y, scale=PX * pr.extra)
    pyxel.pset(x - pr.vx, y - pr.vy, 6)
    pyxel.pset(x - pr.vx * 2, y - pr.vy * 2, 5)


def d_boom(pr, g):
    r = pr.r * (0.4 + pr.t * 0.07)
    c = pr.c or 9
    if pr.t < 5:
        pyxel.dither(0.35)
        pyxel.circ(pr.x, pr.y, r, c)
        pyxel.dither(1.0)
    pyxel.circb(pr.x, pr.y, r + 1, 10 if c in (8, 9) else 7)


def d_penta(pr, g):
    t = pr.t
    x, y = pr.x, pr.y
    R = min(g.W, g.H) * 0.45 * min(1.0, t / 12)
    rot = t * 0.05
    pts = [(x + math.cos(rot + k * TAU / 5 - math.pi / 2) * R,
            y + math.sin(rot + k * TAU / 5 - math.pi / 2) * R) for k in range(5)]
    moon = pr.w is not None and pr.w.id == "gorgeous_moon"
    c1, c2 = (10, 7) if moon else (2, 10)
    for k in range(5):
        a, b = pts[k], pts[(k + 2) % 5]
        pyxel.line(a[0], a[1], b[0], b[1], c1)
    pyxel.circb(x, y, R, c2)
    if 12 <= t <= 16:
        pyxel.dither(0.25)
        pyxel.circ(x, y, R, 7)
        pyxel.dither(1.0)


def d_bomb(pr, g):
    if pr.t < 8:
        pyxel.circ(pr.x, pr.y, 1.5 * PX, pr.c)
        pyxel.pset(pr.x, pr.y - 1, 7)
        return
    k = pr.t - 8
    r = pr.extra * (0.6 + k * 0.08)
    if k < 3:
        pyxel.circ(pr.x, pr.y, r * 0.6, pr.c)
    pyxel.circb(pr.x, pr.y, r, pr.c if k > 2 else 7)


def d_gun(pr, g):
    pyxel.circ(pr.x, pr.y, 2 * PX, pr.c)
    pyxel.circ(pr.x, pr.y, 1 * PX, 7)


def d_cat(pr, g):
    x, y = pr.x, pr.y
    flip = pr.vx < 0
    vic = pr.w is not None and pr.w.id == "vicious_hunger"
    key = "wspr:vicious_hunger" if vic else "wspr:gatti_amari"
    if spr(key, x, y, flip=flip, scale=1.2 if vic else 1.0):
        return
    if vic:
        pyxel.circ(x, y, 7 * PX, 10)
        pyxel.circb(x, y, 7 * PX, 9)
        pyxel.rect(x - 1, y - 5 * PX, 2 * PX, 10 * PX, 0)
        return
    pyxel.elli(x - 6 * PX, y - 3 * PX, 12 * PX, 7 * PX, 9)
    pyxel.circ(x + (-5 if flip else 5) * PX, y - 3 * PX, 3.5 * PX, 9)
    hx = x + (-5 if flip else 5) * PX
    pyxel.tri(hx - 3 * PX, y - 5 * PX, hx - 1 * PX, y - 9 * PX, hx, y - 5 * PX, 9)
    pyxel.tri(hx, y - 5 * PX, hx + 2 * PX, y - 9 * PX, hx + 3 * PX, y - 5 * PX, 9)


def d_scuffle(pr, g):
    for j in range(7):
        a = pr.t * 0.4 + j * 0.9
        rr = pr.r * (0.3 + 0.5 * ((j * 37 + pr.t) % 10) / 10)
        pyxel.circ(pr.x + math.cos(a) * rr, pr.y + math.sin(a) * rr * 0.7, 4 * PX, 7 if j % 2 else 13)
    if pr.t % 6 < 3:
        pyxel.text(pr.x - 6, pr.y - 3, "!#@", 8)


def d_song(pr, g):
    p = g.p
    hw = pr.extra
    mann = pr.w is not None and pr.w.id == "mannajja"
    cols = (2, 14, 7) if mann else (12, 6, 7)
    top = g.cam_y
    for j in range(40):
        yy = top + (j * 53 + pr.t * 7) % g.H
        ph = pr.t * 0.35 + j * 1.7
        xx = p.x + math.sin(ph) * hw * (1 - abs(yy - p.y) / g.H)
        pyxel.pset(xx, yy, cols[j % 3])
        if j % 4 == 0:
            pyxel.pset(xx + 1, yy, cols[2])
    pyxel.dither(0.08)
    pyxel.rect(p.x - hw, top, hw * 2, g.H, cols[0])
    pyxel.dither(1.0)


def d_pinion(pr, g):
    x, y = pr.x, pr.y
    valk = pr.w is not None and pr.w.id == "valkyrie_turner"
    ang = math.degrees(math.atan2(pr.vy, pr.vx))
    if valk:
        if pr.c:
            pyxel.line(x - pr.vx * 2, y - pr.vy * 2, x, y, 9)
            pyxel.line(x - pr.vx * 1.5, y - pr.vy * 1.5 + 1, x, y + 1, 10)
        else:
            f = pr.t % 6
            pyxel.circ(x, y, (3 + f % 2) * PX, 8)
            pyxel.circ(x, y - 1, 2 * PX, 9)
            pyxel.pset(x, y - 3 * PX, 10)
        return
    if not spr("wspr:shadow_pinion", x, y, rotate=ang + 90):
        pyxel.tri(x + math.cos(math.radians(ang)) * 6 * PX, y + math.sin(math.radians(ang)) * 6 * PX,
                  x - 3 * PX, y - 3 * PX, x + 3 * PX, y + 3 * PX, 2)


def d_lance(pr, g):
    if pr.t > 5:
        return
    p = g.p
    L = 0.55 * g.W
    ex, ey = p.x + math.cos(pr.a) * L, p.y + math.sin(pr.a) * L
    pyxel.line(p.x, p.y, ex, ey, 7 if pr.t < 3 else 6)
    pyxel.line(p.x + 1, p.y, ex + 1, ey, 6)


def d_rainbow(pr, g):
    p = g.p
    for k in range(6):
        pyxel.circb(p.x, p.y, 20 + k * 4 + pr.t * 2, (8, 9, 10, 11, 12, 2)[k])


def d_slash(pr, g):
    p = g.p
    k = pr.t
    L = pr.extra * min(1, k / 3)
    x0 = p.x + pr.a * 4 * PX
    y = p.y + pr.oy
    h = pr.b * 0.5 * max(0.2, 1 - k / (pr.t + pr.life))
    if k > 6:
        return
    # thin crescent stroke sweeping outward
    for j in range(6):
        f0, f1 = j / 6, (j + 1) / 6
        y0 = y - h * math.sin(f0 * math.pi)
        y1 = y - h * math.sin(f1 * math.pi)
        pyxel.line(x0 + pr.a * L * f0, y0, x0 + pr.a * L * f1, y1, 7 if k < 3 else pr.c)
    pyxel.line(x0, y + 1, x0 + pr.a * L, y + 1, pr.c)


def d_fring(pr, g):
    p = g.p
    R = pr.extra
    for j in range(10):
        a = j * TAU / 10 + pr.t * 0.3
        x1, y1 = p.x + math.cos(a) * R, p.y + math.sin(a) * R
        x2, y2 = p.x + math.cos(a + 0.35) * R, p.y + math.sin(a + 0.35) * R
        pyxel.line(x1, y1, x2, y2, 8)


def d_bone(pr, g):
    if not spr("wspr:bone", pr.x, pr.y, rotate=pr.t * 30, scale=0.8):
        pyxel.line(pr.x - 4, pr.y, pr.x + 4, pr.y, 7)
        pyxel.circ(pr.x - 4, pr.y, 1.5, 7)
        pyxel.circ(pr.x + 4, pr.y, 1.5, 7)


def d_cherry(pr, g):
    if not spr("wspr:cherry_bomb", pr.x, pr.y, rotate=pr.t * 20):
        pyxel.circ(pr.x, pr.y, 3 * PX, 8)
        pyxel.pset(pr.x, pr.y - 3 * PX, 11)


def d_cart(pr, g):
    if not spr("wspr:carrello", pr.x, pr.y, rotate=pr.t * 25 * (1 if pr.vx > 0 else -1),
               scale=0.5 * pr.extra):
        pyxel.rect(pr.x - 7 * PX, pr.y - 4 * PX, 14 * PX, 7 * PX, 4)
        pyxel.circ(pr.x - 4 * PX, pr.y + 3 * PX, 2 * PX, 13)
        pyxel.circ(pr.x + 4 * PX, pr.y + 3 * PX, 2 * PX, 13)
    if pr.t % 2:
        pyxel.pset(pr.x - pr.vx, pr.y + 4 * PX, 10)


def d_flower(pr, g):
    if not spr("wspr:celestial_dusting", pr.x, pr.y, rotate=pr.t * 15, scale=pr.extra):
        for k in range(5):
            a = k * TAU / 5 + pr.t * 0.2
            pyxel.circ(pr.x + math.cos(a) * 2.5 * PX, pr.y + math.sin(a) * 2.5 * PX, 1.5 * PX, 14)
        pyxel.circ(pr.x, pr.y, 1.2 * PX, 10)


def d_robba(pr, g):
    if spr("wspr:la_robba", pr.x, pr.y, rotate=pr.t * 12, scale=0.6):
        return
    c = (4, 9, 13)[pr.c]
    pyxel.rect(pr.x - 5 * PX, pr.y - 4 * PX, 10 * PX, 8 * PX, c)
    pyxel.rectb(pr.x - 5 * PX, pr.y - 4 * PX, 10 * PX, 8 * PX, 0)


def d_bracelet(pr, g):
    for j in range(3):
        a = pr.t * 0.6 + j * 2.1
        pyxel.circ(pr.x + math.cos(a) * 1.5 * PX, pr.y + math.sin(a) * 1.5 * PX, 1.5 * PX, pr.c)
    pyxel.pset(pr.x, pr.y, 7)


DRAW = {
    "whip": d_whip, "tear": d_whip, "wand": d_wand, "holy": d_wand, "knife": d_knife,
    "edge": d_knife, "axe": d_axe, "spiral": d_spiral, "cross": d_cross, "heaven": d_cross,
    "bible": d_bible, "vespers": d_bible, "fire": d_fire, "hellfire": d_fire,
    "water": d_water, "borra": d_water, "ring": d_ring, "thunder": d_ring, "rune": d_rune,
    "nofuture": d_rune, "boom": d_boom, "penta": d_penta, "bomb": d_bomb, "gun": d_gun,
    "cat": d_cat, "scuffle": d_scuffle, "song": d_song, "pinion": d_pinion,
    "lance": d_lance, "rainbow": d_rainbow, "slash": d_slash, "fring": d_fring,
    "bone": d_bone, "cherry": d_cherry, "cart": d_cart, "flower": d_flower,
    "robba": d_robba, "bracelet": d_bracelet,
}


# ------------------------------------------------- weapon-owned visuals


def draw_aura(w, g):
    """Persistent weapon visuals (auras, birds, lasers, shields). Call for every weapon."""
    if art.MODE == "90s" and fx90s.aura(w, g):
        return
    k = w.kind
    p = g.p
    fx = w.fx
    if k in ("garlic", "soul"):
        r = fx.get("r", 0)
        if not r:
            return
        soul = k == "soul"
        pyxel.dither(0.12)
        pyxel.circ(p.x, p.y, r, 2 if soul else 7)
        pyxel.dither(1.0)
        wob = math.sin(g.frame * 0.2) * 1.5
        pyxel.circb(p.x, p.y, r + wob, 14 if soul else 15)
        if soul:  # particles pulled inward
            for j in range(8):
                a = j * TAU / 8 + g.frame * 0.05
                rr = r * (1 - ((g.frame * 2 + j * 11) % 30) / 30)
                pyxel.pset(p.x + math.cos(a) * rr, p.y + math.sin(a) * rr, 14)
    elif k == "bird" and "bx" in fx:
        for zx, zy in fx["zones"]:
            pyxel.dither(0.3)
            pyxel.circb(zx, zy, 9 * PX, 7 if w.id == "peachone" else 2 if w.id == "ebony_wings" else 14)
            pyxel.dither(1.0)
        key = f"wspr:{w.id}"
        flip = fx["zones"][0][0] < fx["bx"] if fx["zones"] else False
        if not spr(key, fx["bx"], fx["by"], flip=flip, scale=1.2):
            c = 7 if w.id == "peachone" else 2 if w.id == "ebony_wings" else 11
            wing = 4 if (g.frame // 4) % 2 else -2
            pyxel.tri(fx["bx"] - 8, fx["by"] + wing, fx["bx"], fx["by"], fx["bx"] - 2, fx["by"] + 3, c)
            pyxel.tri(fx["bx"] + 8, fx["by"] + wing, fx["bx"], fx["by"], fx["bx"] + 2, fx["by"] + 3, c)
            pyxel.circ(fx["bx"], fx["by"], 2.5, c)
    elif k == "lasers" and fx.get("on", 0) > 0:
        n, L, wid = fx["n"], fx["len"], fx["wid"]
        for j in range(n):
            a = fx["ang"] + j * TAU / n
            ex, ey = p.x + math.cos(a) * L, p.y + math.sin(a) * L
            nx, ny = -math.sin(a), math.cos(a)
            for o in range(-int(wid // 2), int(wid // 2) + 1):
                c = 7 if abs(o) < wid / 4 else 12
                pyxel.line(p.x + nx * o, p.y + ny * o, ex + nx * o, ey + ny * o, c)
    elif k == "shield":
        ch = fx.get("charges", 0)
        if ch <= 0 and not fx.get("pop"):
            return
        if w.id == "crimson_shroud":
            col = {1: 11, 2: 9, 3: 8}.get(ch, 8)
        else:
            col = {1: 12, 2: 11, 3: 10}.get(ch, 12)
        r = 15 * PX + math.sin(g.frame * 0.15) * 1.5
        if fx.get("pop"):
            r += (10 - fx["pop"]) * 2
            col = 7
        pyxel.dither(0.25)
        pyxel.circ(p.x, p.y - 2, r, col)
        pyxel.dither(1.0)
        pyxel.circb(p.x, p.y - 2, r, col)


draw_weapon_fx = draw_aura

import fx90s  # noqa: E402  (last: it draws with the helpers defined above)
