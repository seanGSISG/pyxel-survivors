"""Weapon instances, projectiles and their per-kind behaviour.

A Weapon owns cooldown/burst timing and computes its final stats from the
data table plus the player's passive multipliers. Each shot spawns a Proj
whose `kind` selects an update/draw function below.
"""

import math
import random

import pyxel

import data
import sprites

FPS = 30


def sec(s):
    return max(1, int(round(s * FPS)))


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
        self.orbit_t = 0  # garlic tick, bible volley id
        self.hits = {}  # persistent per-enemy hit clock (garlic)

    @property
    def spec(self):
        return data.WEAPONS[self.id]

    @property
    def maxed(self):
        return self.level >= len(self.spec["levels"]) + 1

    def stats(self, ps):
        """Final stats after levels and passive multipliers."""
        spec = self.spec
        s = dict(spec["base"])
        for lv in spec["levels"][: self.level - 1]:
            for k, v in lv.items():
                s[k] = s.get(k, 0) + v
        s["dmg"] *= ps["might"]
        s["cd"] = max(0.05, s["cd"] * ps["cooldown"])
        s["area"] *= ps["area"]
        s["speed"] *= ps["speed"]
        s["dur"] = s.get("dur", 0) * ps["duration"]
        s["amount"] = int(s["amount"] + ps["amount"])
        return s

    def update(self, g):
        st = self.stats(g.pstats)
        kind = self.spec["kind"]
        if kind in ("garlic", "soul"):
            aura_update(self, g, st)
            return
        if kind == "vespers":
            if not any(p.w is self for p in g.projs):
                self.volley += 1
                for i in range(st["amount"]):
                    spawn(self, g, st, i, st["amount"])
            return
        if self.queue > 0:
            self.burst_t -= 1
            if self.burst_t <= 0:
                n = st["amount"]
                spawn(self, g, st, n - self.queue, n)
                self.queue -= 1
                self.burst_t = self.spec.get("burst", 3)
            return
        self.timer -= 1
        if self.timer <= 0:
            self.volley += 1
            if self.spec.get("burst", 3) == 0:
                for i in range(st["amount"]):
                    spawn(self, g, st, i, st["amount"])
            else:
                self.queue = st["amount"]
                self.burst_t = 0
            self.timer = sec(st["cd"])
            # Bible's cooldown starts after its orbit ends.
            if kind == "bible":
                self.timer += sec(st["dur"])
            g.sfx_fire(kind)


class Proj:
    __slots__ = (
        "kind", "w", "x", "y", "vx", "vy", "dmg", "life", "pierce", "r",
        "hit", "t", "a", "ox", "oy", "kb", "interval", "extra",
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


def collide(p, g):
    """Damage enemies overlapping p. Returns False once pierce is spent."""
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
        g.damage_enemy(e, p.dmg, p.w, p.x, p.y, p.kb)
        if not p.interval:
            p.pierce -= 1
            if p.pierce <= 0:
                return False
    return True


def crit(g, w, dmg, chance):
    """Bloody Tear (x2, heals 8) / Heaven Sword (x2.5) crits, luck-scaled."""
    if random.random() < chance * g.pstats["luck"]:
        if w.id == "bloody_tear":
            g.heal(8)
            return dmg * 2
        return dmg * 2.5
    return dmg


# --------------------------------------------------------------- spawning


def spawn(w, g, st, i, n):
    p = g.p
    kind = w.spec["kind"]
    dmg = st["dmg"]
    if kind in ("whip", "tear"):
        side = p.face_x if i % 2 == 0 else -p.face_x
        pr = Proj(kind, w, p.x, p.y, dmg=dmg, life=6, pierce=999,
                  r=0, kb=1.0)
        pr.a = side
        pr.oy = -6 + (i // 2) * 10 - (i % 2) * 4
        pr.extra = st["area"]
        g.projs.append(pr)
    elif kind in ("wand", "holy"):
        targets = g.nearest_enemies(p.x, p.y, max(1, n))
        if not targets:
            return
        e = targets[i % len(targets)]
        ang = math.atan2(e.y - p.y, e.x - p.x) + random.uniform(-0.05, 0.05)
        v = 3.2 * st["speed"]
        g.projs.append(Proj(kind, w, p.x, p.y, math.cos(ang) * v,
                            math.sin(ang) * v, dmg, sec(3), st["pierce"],
                            3 * st["area"], 1.0))
    elif kind in ("knife", "edge"):
        fx, fy = p.face_x8, p.face_y8
        ln = math.hypot(fx, fy) or 1
        fx, fy = fx / ln, fy / ln
        v = 5.5 * st["speed"]
        jx, jy = -fy * random.uniform(-6, 6), fx * random.uniform(-6, 6)
        pr = Proj(kind, w, p.x + jx, p.y + jy, fx * v, fy * v, dmg,
                  sec(1.2), st["pierce"], 3 * st["area"], 0.5)
        pr.a = math.degrees(math.atan2(fy, fx))
        g.projs.append(pr)
    elif kind == "axe":
        spread = (i - (n - 1) / 2) * 1.1 + random.uniform(-0.4, 0.4)
        pr = Proj(kind, w, p.x, p.y, spread * st["speed"],
                  -5.2 * st["speed"], dmg, sec(3), st["pierce"],
                  7 * st["area"], 1.0)
        g.projs.append(pr)
    elif kind == "spiral":
        for k in range(9):
            ang = w.volley * 0.35 + k * math.tau / 9
            pr = Proj(kind, w, p.x, p.y, math.cos(ang) * 2.4 * st["speed"],
                      math.sin(ang) * 2.4 * st["speed"], dmg, sec(2.5),
                      999, 9 * st["area"], 1.0)
            pr.a = ang
            g.projs.append(pr)
    elif kind in ("cross", "heaven"):
        targets = g.nearest_enemies(p.x, p.y, max(1, n))
        if targets:
            e = targets[i % len(targets)]
            ang = math.atan2(e.y - p.y, e.x - p.x)
        else:
            ang = random.uniform(0, math.tau)
        pr = Proj(kind, w, p.x, p.y, math.cos(ang), math.sin(ang), dmg,
                  sec(3.5), 999, 6 * st["area"], 1.0, interval=sec(0.5))
        pr.extra = 5.0 * st["speed"]  # current signed speed along (vx, vy)
        g.projs.append(pr)
    elif kind in ("bible", "vespers"):
        life = 10 ** 9 if kind == "vespers" else sec(st["dur"])
        pr = Proj(kind, w, p.x, p.y, dmg=dmg, life=life, pierce=999,
                  r=5 * st["area"], kb=1.0, interval=sec(0.5))
        pr.a = i * math.tau / n
        pr.extra = 38 * st["area"]  # orbit radius
        pr.ox = st["speed"]  # orbit speed multiplier
        g.projs.append(pr)
    elif kind in ("fire", "hellfire"):
        e = g.random_enemy_near(p.x, p.y)
        if e:
            ang = math.atan2(e.y - p.y, e.x - p.x)
        else:
            ang = random.uniform(0, math.tau)
        ang += (i - (n - 1) / 2) * 0.12
        big = kind == "hellfire"
        v = (1.6 if big else 2.2) * st["speed"]
        pr = Proj(kind, w, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v,
                  dmg, sec(4), 999 if big else 1,
                  (12 if big else 5) * st["area"], 1.0 if not big else 0.5)
        g.projs.append(pr)
    elif kind in ("water", "borra"):
        e = g.random_enemy_near(p.x, p.y, 120)
        if e and i == 0:
            tx, ty = e.x, e.y
        else:
            ang = random.uniform(0, math.tau)
            d = random.uniform(30, 90)
            tx, ty = p.x + math.cos(ang) * d, p.y + math.sin(ang) * d
        pr = Proj(kind, w, p.x, p.y, dmg=dmg, life=sec(st["dur"]) + 12,
                  pierce=999, r=0, kb=0.2, interval=sec(0.5))
        pr.ox, pr.oy = tx, ty  # target
        pr.extra = 14 * st["area"]  # puddle radius
        g.projs.append(pr)
    elif kind in ("ring", "thunder"):
        e = g.random_enemy_on_screen()
        if not e:
            return
        pr = Proj(kind, w, e.x, e.y, dmg=dmg, life=8, pierce=999,
                  r=8 * st["area"], kb=0.3)
        g.projs.append(pr)
        if kind == "thunder":
            pr2 = Proj(kind, w, e.x, e.y, dmg=dmg, life=8, pierce=999,
                       r=8 * st["area"], kb=0.3)
            pr2.t = -6  # delayed second strike
            g.projs.append(pr2)
    elif kind in ("rune", "nofuture"):
        ang = random.uniform(0, math.tau)
        v = 4.0 * st["speed"]
        pr = Proj(kind, w, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v,
                  dmg, sec(st["dur"]), 999, 5 * st["area"], 0.6,
                  interval=sec(0.4))
        pr.extra = st["area"]
        g.projs.append(pr)


# ---------------------------------------------------------------- updates


def aura_update(w, g, st):
    """Garlic / Soul Eater: damage everything in radius every `cd`."""
    p = g.p
    r = 22 * st["area"]
    w.orbit_t += 1
    interval = sec(st["cd"])
    for e in g.query(p.x, p.y, r):
        key = id(e)
        if g.frame < w.hits.get(key, 0):
            continue
        w.hits[key] = g.frame + interval
        g.damage_enemy(e, st["dmg"], w, p.x, p.y, 0.7)
        if w.id == "soul_eater" and not e.prop:
            g.heal(0.4)
    if w.orbit_t % 120 == 0:  # forget dead enemies
        alive = {id(e) for e in g.enemies}
        w.hits = {k: v for k, v in w.hits.items() if k in alive}
    w.extra_r = r


def update_proj(pr, g):
    """Advance one projectile. Returns False when it should be removed."""
    pr.t += 1
    pr.life -= 1
    if pr.life <= 0:
        return False
    k = pr.kind
    p = g.p
    if k in ("whip", "tear"):
        if pr.t == 2:  # hitbox active on frame 2 only
            area = pr.extra
            w, h = 56 * area, 14 * area
            x0 = p.x if pr.a > 0 else p.x - w
            y0 = p.y + pr.oy - h / 2
            chance = 0.25 if k == "tear" else 0
            for e in g.query_rect(x0, y0, w, h):
                dmg = crit(g, pr.w, pr.dmg, chance) if chance else pr.dmg
                g.damage_enemy(e, dmg, pr.w, p.x, p.y, 1.0)
        return True
    if k in ("bible", "vespers"):
        pr.a += 0.11 * pr.ox
        pr.x = p.x + math.cos(pr.a) * pr.extra
        pr.y = p.y + math.sin(pr.a) * pr.extra
        return collide(pr, g)
    if k == "axe":
        pr.vy += 0.22
        pr.x += pr.vx
        pr.y += pr.vy
        return collide(pr, g)
    if k in ("cross", "heaven"):
        pr.extra -= 0.16
        pr.x += pr.vx * pr.extra
        pr.y += pr.vy * pr.extra
        return collide_crit(pr, g, 0.2 if k == "heaven" else 0)
    if k in ("water", "borra"):
        if pr.t < 12:  # flask in flight
            pr.x += (pr.ox - pr.x) / (13 - pr.t)
            pr.y += (pr.oy - pr.y) / (13 - pr.t)
            return True
        if pr.t == 12:
            pr.x, pr.y = pr.ox, pr.oy
            pr.r = pr.extra
            g.sfx("splash")
        if k == "borra":
            dx, dy = p.x - pr.x, p.y - pr.y
            d = math.hypot(dx, dy) or 1
            pr.x += dx / d * 0.5
            pr.y += dy / d * 0.5
            pr.r = min(pr.extra * 2, pr.r + 0.03)
        collide(pr, g)
        return True
    if k in ("ring", "thunder"):
        if pr.t == 1:
            collide(pr, g)
            g.sfx("zap")
        return True
    if k in ("rune", "nofuture"):
        pr.x += pr.vx
        pr.y += pr.vy
        left, top = g.cam_x, g.cam_y
        bounced = False
        if pr.x < left + 4 or pr.x > left + g.W - 4:
            pr.vx = -pr.vx
            pr.x = min(max(pr.x, left + 4), left + g.W - 4)
            bounced = True
        if pr.y < top + 12 or pr.y > top + g.H - 4:
            pr.vy = -pr.vy
            pr.y = min(max(pr.y, top + 12), top + g.H - 4)
            bounced = True
        if bounced and k == "nofuture":
            boom = Proj("boom", pr.w, pr.x, pr.y, dmg=pr.dmg, life=8,
                        pierce=999, r=18 * pr.extra, kb=1.0)
            g.projs.append(boom)
        return collide(pr, g)
    if k == "boom":
        if pr.t == 1:
            collide(pr, g)
        return True
    # straight movers: wand, knife, fire, spiral
    pr.x += pr.vx
    pr.y += pr.vy
    if k == "spiral":
        pr.a += 0.35
    if abs(pr.x - p.x) > g.W or abs(pr.y - p.y) > g.H:
        return False
    return collide(pr, g)


def collide_crit(pr, g, chance):
    if not chance:
        return collide(pr, g)
    base = pr.dmg
    pr.dmg = crit(g, pr.w, base, chance)
    ok = collide(pr, g)
    pr.dmg = base
    return ok


# ------------------------------------------------------------------ draws


def draw_proj(pr, g):
    k = pr.kind
    x, y = pr.x, pr.y
    t = pr.t
    if k in ("whip", "tear"):
        p = g.p
        area = pr.extra
        w = 56 * area
        side = pr.a
        cy = p.y + pr.oy
        col = 8 if k == "tear" else 7
        fade = [7, col, 2, 1, 1, 1][min(t - 1, 5)] if t > 0 else col
        for j in range(3):
            yy = cy - 3 + j * 3 * area
            x0 = p.x + side * 6
            x1 = p.x + side * w
            if t <= 3:
                pyxel.line(x0, yy + (1 - j) * 2, x1, yy, fade if j != 1 else 7)
        if t <= 2:
            pyxel.tri(p.x + side * 6, cy - 2, p.x + side * w, cy - 5 * area,
                      p.x + side * w, cy + 5 * area, col)
            pyxel.line(p.x + side * 8, cy, p.x + side * w, cy, 7)
    elif k in ("wand", "holy"):
        c = 12 if k == "wand" else 10
        pyxel.circ(x, y, 2.5, c)
        pyxel.circ(x, y, 1, 7)
        pyxel.pset(x - pr.vx, y - pr.vy, 6)
        pyxel.pset(x - pr.vx * 2, y - pr.vy * 2, 5)
    elif k in ("knife", "edge"):
        ln = math.hypot(pr.vx, pr.vy) or 1
        ux, uy = pr.vx / ln, pr.vy / ln
        pyxel.line(x - ux * 5, y - uy * 5, x + ux * 3, y + uy * 3, 7)
        pyxel.line(x - ux * 7, y - uy * 7, x - ux * 5, y - uy * 5, 4)
        if k == "edge":
            pyxel.pset(x + ux * 4, y + uy * 4, 6)
    elif k == "axe":
        sprites.draw("axe", x, y, rotate=t * 24)
    elif k == "spiral":
        # scythe: a spinning crescent blade on a short haft
        for j in range(9):
            aa = pr.a + j * 0.3
            rr = 7 - abs(j - 4) * 0.5
            px, py = x + math.cos(aa) * rr, y + math.sin(aa) * rr
            pyxel.pset(px, py, 7)
            pyxel.pset(x + math.cos(aa) * (rr - 1.5), y + math.sin(aa) * (rr - 1.5), 13)
        pyxel.line(x, y, x - math.cos(pr.a + 1.2) * 6, y - math.sin(pr.a + 1.2) * 6, 4)
    elif k in ("cross", "heaven"):
        sprites.draw("cross", x, y, rotate=t * 30,
                     scale=pr.r / 6 if k == "cross" else pr.r / 5)
    elif k in ("bible", "vespers"):
        if k == "vespers":
            pyxel.pal(12, 2)
        sprites.draw("bible", x, y, scale=max(1.0, pr.r / 5))
        pyxel.pal()
    elif k in ("fire", "hellfire"):
        r = pr.r
        pyxel.circ(x, y, r, 8)
        pyxel.circ(x - pr.vx * 0.5, y - pr.vy * 0.5, r * 0.7, 9)
        pyxel.circ(x, y, r * 0.4, 10)
        for j in range(2):
            pyxel.pset(x - pr.vx * (3 + j * 2) + random.uniform(-2, 2),
                       y - pr.vy * (3 + j * 2) + random.uniform(-2, 2), 9)
    elif k in ("water", "borra"):
        if t < 12:
            pyxel.rect(x - 2, y - 3, 4, 5, 12)
            pyxel.pset(x, y - 4, 7)
        else:
            r = pr.r
            pyxel.dither(0.55)
            pyxel.elli(x - r, y - r * 0.6, r * 2, r * 1.2, 12 if k == "water" else 6)
            pyxel.dither(1.0)
            for j in range(4):
                a = t * 0.2 + j * 1.6
                pyxel.circb(x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.3,
                            1 + (t + j * 3) % 4, 6)
            pyxel.ellib(x - r, y - r * 0.6, r * 2, r * 1.2, 6)
    elif k in ("ring", "thunder"):
        if t < 1:
            return
        c = 10 if t < 4 else 9
        yy = y - 200
        xx = x
        while yy < y:
            nx = x + random.uniform(-6, 6)
            ny = min(y, yy + random.uniform(10, 24))
            pyxel.line(xx, yy, nx, ny, 7 if t < 3 else c)
            pyxel.line(xx + 1, yy, nx + 1, ny, c)
            xx, yy = nx, ny
        pyxel.circb(x, y, pr.r * (0.5 + t * 0.08), c)
        if t < 3:
            pyxel.circ(x, y, pr.r * 0.6, 7)
    elif k in ("rune", "nofuture"):
        sprites.draw("rune", x, y, scale=pr.extra)
        pyxel.pset(x - pr.vx, y - pr.vy, 6)
        pyxel.pset(x - pr.vx * 2, y - pr.vy * 2, 5)
    elif k == "boom":
        r = pr.r * (0.4 + t * 0.08)
        pyxel.circ(x, y, r, 9 if t < 4 else 8)
        pyxel.circb(x, y, r + 1, 10)


def draw_aura(w, g):
    r = getattr(w, "extra_r", 0)
    if not r:
        return
    p = g.p
    pyxel.dither(0.12)
    pyxel.circ(p.x, p.y, r, 14 if w.id == "soul_eater" else 7)
    pyxel.dither(1.0)
    wob = math.sin(g.frame * 0.2) * 1.5
    pyxel.circb(p.x, p.y, r + wob, 14 if w.id == "soul_eater" else 15)
