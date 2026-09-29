"""Simulation: player stats, stages & waves, map events, combat, pickups,
level-ups, treasure chests. `World` is the `g` object weapons receive; the
App in main.py subclasses it and adds menus and rendering.
"""

import math
import random

import art
import data
from arcanas import Arcanas
from weapons import Proj, Weapon, sec, update_proj

W, H = 480, 270
FPS = 30
MIN = 60 * FPS
PX = 1.5  # world scale: 32px sprites on a 480x270 screen

REAPER = dict(id="reaper", name="The Reaper", hp=655350, xp=0, dmg=65535, speed=160,
              kb=0, kb_max=0, res_freeze=1, res_kill=1, hp_level=True, image="", skills="")
LIGHT_KIND = {"mad_forest": "brazier", "inlaid_library": "candelabrone",
              "dairy_plant": "lampost", "gallo_tower": "lantern", "cappella_magna": "blue_brazier"}

# Character growth bonuses from their descriptions: (stat, per, every N levels, cap)
CHAR_GROWTH = {
    "antonio_belpaese": [("might", 0.10, 10, 0.5)],
    "imelda_belpaese": [("growth", 0.10, 5, 0.3)],
    "pasqualina_belpaese": [("speed", 0.10, 5, 0.3)],
    "arca_ladonna": [("cooldown", -0.05, 10, -0.15)],
    "lama_ladonna": [("might", 0.05, 10, 0.2), ("move", 0.05, 10, 0.2), ("curse", 0.05, 10, 0.2)],
    "concetta_caciotta": [("area", 0.01, 1, 9)],
    "giovanna_grana": [("speed", 0.01, 1, 9)],
    "poppea_pecorina": [("duration", 0.01, 1, 9)],
    "pugnala_provola": [("might", 0.01, 1, 9)],
    "zi_assunta_belpaese": [("might", 0.005, 1, 9), ("speed", 0.005, 1, 9),
                            ("duration", 0.005, 1, 9), ("area", 0.005, 1, 9)],
    "divano_thelma": [("armor", 1, 5, 5)],
    "iguana_gallo_valletto": [("growth", 0.10, 5, 0.5)],
    "mortaccio": [("amount", 1, 20, 3)], "yatta_cavallo": [("amount", 1, 20, 3)],
    "bianca_ramba": [("amount", 1, 20, 3)], "osole_meeo": [("amount", 1, 20, 3)],
    "sir_ambrojoe": [("amount", 1, 20, 3)],
}
EXTRA_START_LEVEL = {"christine_davain", "divano_thelma", "iguana_gallo_valletto"}
CHAR_STAT_KEYS = {"recovery": "recovery", "armor": "armor", "movespeed": "move", "might": "might",
                  "speed": "speed", "duration": "duration", "area": "area", "cooldown": "cooldown",
                  "amount": "amount", "revival": "revival", "luck": "luck", "growth": "growth",
                  "greed": "greed", "curse": "curse"}


# ---------------------------------------------------------------- entities


class Player:
    def __init__(self, char):
        self.char = char
        self.x = self.y = 0.0
        self.hp = float(char["hp"])
        self.face_x = 1
        self.face_x8, self.face_y8 = 1, 0
        self.moving = False
        self.walk = 0
        self.inv = 0
        self.hurt = 0


class Enemy:
    __slots__ = (
        "eid", "name", "x", "y", "hp", "maxhp", "spd", "dmg", "xp", "kb", "r", "h", "flash",
        "kbt", "kbx", "kby", "boss", "prop", "vx", "vy", "ttl", "phase", "treasure",
        "reaper", "dead", "flip", "cx", "cy", "frozen", "scale", "res_freeze", "res_kill",
        "hunter",
    )

    def __init__(self, spec, x, y, g, boss=False):
        self.x, self.y = x, y
        self.flash = self.kbt = self.frozen = 0
        self.kbx = self.kby = self.vx = self.vy = 0.0
        self.ttl = -1
        self.phase = random.randint(0, 11)
        self.dead = self.flip = self.hunter = False
        self.cx = self.cy = 0
        self.treasure = None
        self.boss = boss
        if spec is None:  # light source
            self.eid, self.name = "light", "light"
            self.hp = self.maxhp = 10
            self.spd = self.dmg = self.xp = self.kb = 0
            self.r, self.h, self.scale = 7, 16, 1.0
            self.prop, self.reaper = True, False
            self.res_freeze = self.res_kill = 1
            return
        self.eid, self.name = spec["id"], spec["name"]
        self.prop = False
        self.reaper = spec["id"] == "reaper"
        ps = g.pstats
        hp = spec["hp"] * (g.level if (spec["hp_level"] or boss) else 1) * ps["curse"]
        self.hp = self.maxhp = max(1.0, hp)
        stage_spd = g.stage["enemy_speed"]
        self.spd = spec["speed"] * data.SPEED_UNIT * PX * stage_spd * (1 + (ps["curse"] - 1) * 0.5)
        if self.reaper:
            self.spd = data.PLAYER_SPEED * PX * g.stage["player_speed"] * 1.25
        self.dmg = spec["dmg"]
        self.xp = spec["xp"]
        self.kb = spec["kb"]
        self.res_freeze = spec.get("res_freeze", 0)
        self.res_kill = spec.get("res_kill", 0)
        w, h = art.enemy_size(self.eid)
        self.scale = 1.5 if boss and max(w, h) < 48 else 1.0
        self.r = max(5.0, min(w, h) * 0.32 * self.scale)
        self.h = h * self.scale


class Pickup:
    __slots__ = ("kind", "x", "y", "value", "fly", "vel", "t", "treasure")

    def __init__(self, kind, x, y, value=0):
        self.kind = kind
        self.x, self.y = x, y
        self.value = value
        self.fly = False
        self.vel = 0.0
        self.t = random.randint(0, 60)
        self.treasure = None


class Floater:
    __slots__ = ("x", "y", "s", "col", "life")

    def __init__(self, x, y, s, col, life=18):
        self.x, self.y, self.s, self.col, self.life = x, y, s, col, life


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "col", "life")

    def __init__(self, x, y, vx, vy, col, life):
        self.x, self.y, self.vx, self.vy, self.col, self.life = x, y, vx, vy, col, life


class Hazard:
    """Telegraphed ground explosion (Shooting Star, Shade Bomb)."""
    __slots__ = ("x", "y", "r", "t", "fuse", "dmg")

    def __init__(self, x, y, r, fuse, dmg):
        self.x, self.y, self.r, self.t, self.fuse, self.dmg = x, y, r, 0, fuse, dmg


# ------------------------------------------------------------------ world


class World:
    W, H = W, H
    CELL = 48

    def new_game(self, char_id, stage_id, arcana_ids=()):
        cfg = self.config
        self.char = next(c for c in data.CHARACTERS if c["id"] == char_id)
        self.stage = data.STAGES[stage_id]
        self.p = Player(self.char)
        self.t = int(cfg.get("minute", 0) * MIN)
        self.god = cfg.get("god", False)
        self.enemies, self.projs, self.pickups = [], [], []
        self.floaters, self.particles, self.hazards = [], [], []
        self.weapons = [Weapon(w) for w in self.char["weapons"] if w in data.WEAPONS]
        self.passives = {}
        for wid, lv in cfg.get("weapons", {}).items():
            w = self.weapon(wid) or Weapon(wid)
            w.level = lv
            if w not in self.weapons:
                self.weapons.append(w)
        for pid, lv in cfg.get("passives", {}).items():
            self.passives[pid] = lv
        self.level = cfg.get("level", 1)
        self.xp = 0.0
        self.xp_next = data.xp_needed(self.level)
        self.kills = self.gold = 0
        self.pending = 1 if char_id in EXTRA_START_LEVEL else 0
        self.chests_opened = 0
        self.luck_bonus = 0.0
        self.revivals_used = 0
        self.freeze_t = self.flash_t = self.nduja_t = self.shake = 0
        self.spawn_t = self.light_t = 0
        self.wave_min = -1
        self.events = []
        self.big_gem = None
        self.gem_count = self.enemy_count = self.reapers = 0
        self.banner, self.banner_t = "", 0
        self.grid = {}
        self.choices = []
        self.menu_delay = 0
        self.chest = None
        self.arcana_pick = None
        self.result = None
        self.hp_healed = 0.0
        self.pstats = {}
        self.arc = Arcanas(self, arcana_ids)
        self.recompute_stats()
        self.p.hp = self.pstats["maxhp"]
        self.revivals = int(self.pstats["revival"])
        for aid in self.arc.active:
            self.arc.on_add(aid)
        self.cam_x, self.cam_y = -W / 2, -H / 2
        if cfg.get("chest"):  # test hook: an evolution-capable chest nearby
            ch = Pickup("chest", 50, 0)
            ch.treasure = dict(evo="1", tier3="0", tier2="0", tier1="100")
            self.pickups.append(ch)

    # ------------------------------------------------------------- stats

    def weapon(self, wid):
        for w in self.weapons:
            if w.id == wid:
                return w
        return None

    @property
    def weapon_ids(self):
        return [f"{w.id}:{w.level}" for w in self.weapons]

    def recompute_stats(self):
        old_max = self.pstats.get("maxhp")
        ch = self.char
        ps = dict(might=1.0, armor=0.0, maxhp=float(ch["hp"]), recovery=0.0, cooldown=1.0,
                  area=1.0, speed=1.0, duration=1.0, amount=0.0, move=1.0,
                  magnet=float(data.MAGNET_BASE * PX), luck=1.0, growth=1.0, greed=1.0,
                  curse=1.0, revival=0.0, inv_bonus=0.0)
        for k, v in ch["bonus"].items():
            key = CHAR_STAT_KEYS.get(k)
            if key:
                ps[key] += v
            elif k == "magnet":
                ps["magnet"] *= 1 + v
        for stat, per, every, cap in CHAR_GROWTH.get(ch["id"], []):
            gain = per * (self.level // every)
            ps[stat] += max(gain, cap) if cap < 0 else min(gain, cap)
        mult_hp = 1.0
        for pid, lv in self.passives.items():
            spec = data.PASSIVES[pid]
            if pid == "hollow_heart":
                mult_hp *= 1.2 ** lv
            elif pid == "attractorb":
                ps["magnet"] *= data.ATTRACTORB_MULT[min(lv, 5)]
            elif pid == "armor":
                ps["armor"] += lv
            elif pid == "torronas_box":
                for s in ("might", "speed", "duration", "area"):
                    ps[s] += 0.04 * lv
                ps["curse"] += 0.04 * lv
            elif pid == "metaglio_left":
                ps["recovery"] += 0.1 * lv
                mult_hp *= 1 + 0.05 * lv
            elif pid == "karomas_mana":
                ps["curse"] += 0.1 * lv
            elif pid == "parm_aegis":
                ps["inv_bonus"] += 1.5 * lv
            else:
                for s in spec["stats"]:
                    ps[s] += spec["per"] * lv
        ps["maxhp"] *= mult_hp
        ps["luck"] += self.luck_bonus
        self.arc.stat_mods(ps)
        ps["cooldown"] = max(0.1, ps["cooldown"])
        ps["amount"] = max(0, int(ps["amount"]))
        if old_max is not None and ps["maxhp"] > old_max:
            self.p.hp += ps["maxhp"] - old_max
        self.pstats = ps

    # ------------------------------------------------------------- player

    def move_player(self, dx, dy):
        p, ps = self.p, self.pstats
        p.moving = bool(dx or dy)
        if p.moving:
            ln = math.hypot(dx, dy)
            spd = data.PLAYER_SPEED * PX * ps["move"] * self.stage["player_speed"]
            p.x += dx / ln * spd
            p.y += dy / ln * spd
            p.walk += 1
            if abs(dx) > 0.2:
                p.face_x = 1 if dx > 0 else -1
            p.face_x8 = round(dx / ln) if abs(dx / ln) > 0.38 else 0
            p.face_y8 = round(dy / ln) if abs(dy / ln) > 0.38 else 0
        lay = self.stage["layout"]
        if lay == "horizontal":
            p.y = max(-H * 0.55, min(H * 0.55, p.y))
        elif lay == "vertical":
            p.x = max(-W * 0.3, min(W * 0.3, p.x))

    def p_invuln(self, frames):
        self.p.inv = max(self.p.inv, int(frames))

    def heal(self, amount, show=True):
        p = self.p
        amount *= self.arc.heal_mult()
        before = p.hp
        p.hp = min(self.pstats["maxhp"], p.hp + amount)
        got = p.hp - before
        self.hp_healed += got
        self.arc.on_heal(amount)  # Sarabande pulses on healing even at full HP
        if show and got >= 1:
            self.floaters.append(Floater(p.x, p.y - 22, f"+{int(got)}", 11, 24))

    def hurt_player(self, dmg):
        p = self.p
        if p.inv > 0 or self.god:
            return
        for w in self.weapons:
            if hasattr(w, "blocks_hit") and w.blocks_hit(self):
                p.inv = data.INVULN_FRAMES
                return
        dmg = max(1, dmg - self.pstats["armor"])
        for w in self.weapons:
            if hasattr(w, "cap_damage"):
                dmg = w.cap_damage(dmg)
        p.hp -= dmg
        p.inv = data.INVULN_FRAMES + int(self.pstats["inv_bonus"])
        p.hurt = 6
        self.shake = 4
        self.sfx("hurt")
        self.arc.on_hurt(dmg)
        if p.hp <= 0 and self.revivals > 0 and self.t < self.stage["minutes"] * MIN:
            self.revivals -= 1
            self.revivals_used += 1
            p.hp = self.pstats["maxhp"] * 0.5
            p.inv = FPS * 2
            self.flash_t = 10
            for e in self.targetable():
                if not e.reaper:
                    self.kill(e, None)
            self.show_banner("REVIVED!", 45)
            self.arc.on_revive()

    # ------------------------------------------------------------- update

    def step(self, dx, dy):
        """Advance the run one frame given the movement input."""
        self.t += 1
        p, ps = self.p, self.pstats
        self.move_player(dx, dy)
        if p.inv > 0:
            p.inv -= 1
        if p.hurt > 0:
            p.hurt -= 1
        if ps["recovery"] and p.hp < ps["maxhp"]:
            self.heal(ps["recovery"] / FPS, show=False)
        self.cam_x = p.x - W / 2
        self.cam_y = p.y - H / 2
        self.arc.update()
        self.update_waves()
        self.build_grid()
        for w in self.weapons:
            w.update(self)
        if self.nduja_t > 0:
            self.nduja_t -= 1
            if self.nduja_t % sec(0.5) == 0:
                self.breathe_fire()
        self.projs = [pr for pr in self.projs if update_proj(pr, self)]
        self.update_enemies()
        self.update_hazards()
        self.update_pickups()
        for f in self.floaters:
            f.y -= 0.5
            f.life -= 1
        self.floaters = [f for f in self.floaters if f.life > 0]
        for pa in self.particles:
            pa.x += pa.vx
            pa.y += pa.vy
            pa.vx *= 0.9
            pa.vy *= 0.9
            pa.life -= 1
        self.particles = [pa for pa in self.particles if pa.life > 0]
        for tname in ("freeze_t", "flash_t", "shake", "banner_t"):
            v = getattr(self, tname)
            if v > 0:
                setattr(self, tname, v - 1)

    # --------------------------------------------------------- waves

    def update_waves(self):
        minute = self.t // MIN
        if minute != self.wave_min:
            self.start_minute(minute)
        while self.events and self.events[0][0] <= self.t:
            _, ev = self.events.pop(0)
            self.run_event(ev)
        if minute >= self.stage["minutes"]:
            return
        waves = self.stage["waves"]
        wave = waves[min(minute, len(waves) - 1)]
        self.spawn_t -= 1
        if self.spawn_t <= 0 and wave["enemies"]:
            self.spawn_t = sec(wave["interval"] / self.pstats["curse"])
            alive = self.enemy_count
            if alive < data.MAX_ENEMIES:
                need = int(wave["minimum"] * self.pstats["curse"])
                if alive < need:
                    for i in range(min(need - alive, 40)):
                        self.spawn_enemy(wave["enemies"][i % len(wave["enemies"])])
                else:
                    for k in wave["enemies"]:
                        self.spawn_enemy(k)
        self.light_t += 1
        if self.light_t >= FPS:
            self.light_t = 0
            lights = sum(1 for e in self.enemies if e.prop)
            chance = min(0.5, self.stage["light_chance"] * self.pstats["luck"])
            if lights < self.stage["light_max"] and random.random() < chance:
                x, y = self.offscreen_point(16)
                self.enemies.append(Enemy(None, x, y, self))

    def start_minute(self, minute):
        self.wave_min = minute
        self.events = []
        if minute >= self.stage["minutes"]:
            if self.reapers == 0:
                for e in self.enemies:
                    if not e.prop:
                        e.dead = True
                self.enemies = [e for e in self.enemies if not e.dead]
                self.show_banner("THE REAPER COMES", 150)
                self.flash_t = 10
            self.spawn_spec(REAPER)
            self.reapers += 1
            self.sfx("boss")
            return
        waves = self.stage["waves"]
        if minute >= len(waves):
            return
        wave = waves[minute]
        for i, b in enumerate(wave["bosses"]):
            e = self.spawn_enemy(b, boss=True)
            if e and i < len(wave["treasure"]):
                e.treasure = wave["treasure"][i]
        if wave["bosses"]:
            self.sfx("boss")
        for ev in wave["events"]:
            if random.random() * 100 > ev["chance"] / self.pstats["luck"]:
                continue
            reps = max(1, ev["repeat"])
            for k in range(reps):
                at = self.t + sec(max(1.0, ev["delay"])) + int(k * MIN / (reps + 1))
                self.events.append((at, ev))
        self.events.sort(key=lambda a: a[0])
        start = minute == 0 or (self.t % MIN == 0 and minute == self.config.get("minute", 0))
        if start and wave["enemies"]:
            for i in range(self.stage["starting_spawns"]):
                self.spawn_enemy(wave["enemies"][i % len(wave["enemies"])])

    def event_enemy(self, ev):
        """Resolve a map event's enemy variant to an enemy id (fallback: current wave)."""
        if ev.get("eid") in data.ENEMIES:
            return ev["eid"]
        for name in (ev.get("variant"), ev.get("enemy")):
            if not name:
                continue
            key = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("'", "")
            key = key.replace(".", "").replace("__", "_")
            for eid in data.ENEMIES:
                if eid == key or eid.startswith(key):
                    return eid
        waves = self.stage["waves"]
        wave = waves[min(self.t // MIN, len(waves) - 1)]
        return wave["enemies"][0] if wave["enemies"] else "zombie"

    def run_event(self, ev):
        p = self.p
        name = ev["name"] or "Event"
        eid = self.event_enemy(ev)
        low = name.lower()
        if "swarm" in low or "stream" in low:
            lay = self.stage["layout"]
            ang = random.choice([0, math.pi]) if lay == "horizontal" else \
                random.choice([math.pi / 2, -math.pi / 2]) if lay == "vertical" else \
                random.uniform(0, math.tau)
            v = 4.5 * PX
            vx, vy = math.cos(ang) * v, math.sin(ang) * v
            cx = p.x - math.cos(ang) * (W * 0.7)
            cy = p.y - math.sin(ang) * (H * 0.8)
            for _ in range(ev["amount"] or 24):
                e = self.spawn_enemy(eid, cx + random.uniform(-40, 40),
                                     cy + random.uniform(-40, 40), force=True)
                if e:
                    e.vx, e.vy = vx, vy
                    e.ttl = sec(5)
        elif "wall" in low:
            n = ev["amount"] or 40
            for i in range(n):
                a = i * math.tau / n
                e = self.spawn_enemy(eid, p.x + math.cos(a) * W * 0.55,
                                     p.y + math.sin(a) * H * 0.62, force=True)
                if e:
                    e.ttl = sec(ev["duration"] or 30)
                    e.spd = max(e.spd, 0.3)
        elif "star" in low or "bomb" in low:
            for _ in range(max(1, ev["amount"]) * 3):
                self.hazards.append(Hazard(p.x + random.uniform(-90, 90),
                                           p.y + random.uniform(-70, 70), 22,
                                           sec(1.2) + random.randint(0, 30), 25))
        elif "rush" in low or "assault" in low or "pile" in low:
            side = random.uniform(0, math.tau)
            for _ in range(ev["amount"] or 20):
                a = side + random.uniform(-0.4, 0.4)
                e = self.spawn_enemy(eid, p.x + math.cos(a) * W * 0.6,
                                     p.y + math.sin(a) * H * 0.7, force=True)
                if e:
                    e.spd *= 1.6
        else:  # stalkers: one relentless hunter (wiki stats when the variant resolved)
            e = self.spawn_enemy(eid, force=True)
            if e:
                if ev.get("eid") not in data.ENEMIES:
                    e.hp = e.maxhp = e.maxhp * 20
                e.spd = max(e.spd, data.PLAYER_SPEED * PX * 0.9)
                e.hunter = True
        self.show_banner(name.upper(), 50)

    def offscreen_point(self, margin=24):
        left, top = self.cam_x - margin, self.cam_y - margin
        w, h = W + margin * 2, H + margin * 2
        lay = self.stage["layout"]
        if lay == "horizontal":
            return (left if random.random() < 0.5 else left + w), top + random.uniform(0, h)
        if lay == "vertical":
            return left + random.uniform(0, w), (top if random.random() < 0.5 else top + h)
        r = random.uniform(0, 2 * (w + h))
        if r < w:
            return left + r, top
        r -= w
        if r < w:
            return left + r, top + h
        r -= w
        if r < h:
            return left, top + r
        return left + w, top + r - h

    def spawn_enemy(self, eid, x=None, y=None, force=False, boss=False):
        spec = data.ENEMIES.get(eid)
        if spec is None:
            return None
        return self.spawn_spec(spec, x, y, force, boss)

    def spawn_spec(self, spec, x=None, y=None, force=False, boss=False):
        reaper = spec["id"] == "reaper"
        if not (force or boss or reaper) and self.enemy_count >= data.MAX_ENEMIES:
            return None
        if x is None:
            x, y = self.offscreen_point()
        e = Enemy(spec, x, y, self, boss or reaper)
        if self.freeze_t:
            e.frozen = self.freeze_t
        self.enemies.append(e)
        self.enemy_count += 1
        return e

    def show_banner(self, text, frames):
        self.banner, self.banner_t = text, frames

    # --------------------------------------------------------- spatial grid

    def build_grid(self):
        g = {}
        c = self.CELL
        n = 0
        for e in self.enemies:
            if e.dead:
                continue
            n += not e.prop
            cx, cy = int(e.x // c), int(e.y // c)
            e.cx, e.cy = cx, cy
            g.setdefault((cx, cy), []).append(e)
        self.grid = g
        self.enemy_count = n

    def query(self, x, y, r):
        c = self.CELL
        out = []
        pad = r + 32
        for cx in range(int((x - pad) // c), int((x + pad) // c) + 1):
            for cy in range(int((y - pad) // c), int((y + pad) // c) + 1):
                for e in self.grid.get((cx, cy), ()):
                    if e.dead:
                        continue
                    rr = r + e.r
                    dx, dy = e.x - x, e.y - y
                    if dx * dx + dy * dy <= rr * rr:
                        out.append(e)
        return out

    def query_rect(self, x0, y0, w, h):
        c = self.CELL
        out = []
        for cx in range(int((x0 - 32) // c), int((x0 + w + 32) // c) + 1):
            for cy in range(int((y0 - 32) // c), int((y0 + h + 32) // c) + 1):
                for e in self.grid.get((cx, cy), ()):
                    if not e.dead and x0 - e.r <= e.x <= x0 + w + e.r \
                            and y0 - e.r <= e.y <= y0 + h + e.r:
                        out.append(e)
        return out

    def targetable(self):
        px, py = self.p.x, self.p.y
        return [e for e in self.enemies if not e.dead and not e.prop
                and abs(e.x - px) < W / 2 + 10 and abs(e.y - py) < H / 2 + 10]

    def nearest_enemies(self, x, y, n):
        cand = self.targetable()
        cand.sort(key=lambda e: (e.x - x) ** 2 + (e.y - y) ** 2)
        return cand[:n]

    def random_enemy_near(self, x, y, r=None):
        cand = self.targetable()
        if r:
            cand = [e for e in cand if (e.x - x) ** 2 + (e.y - y) ** 2 < r * r]
        return random.choice(cand) if cand else None

    def random_enemy_on_screen(self):
        return self.random_enemy_near(self.p.x, self.p.y)

    # ------------------------------------------------------------ combat

    def damage_enemy(self, e, dmg, w, sx, sy, kb):
        if e.dead:
            return
        e.hp -= dmg
        e.flash = 4
        if w is not None:
            w.dmg_done += dmg
            fc = self.arc.freeze_chance(w)
            if fc and random.random() < fc * self.pstats["luck"]:
                self.freeze_enemy(e, sec(1.5))
        if len(self.floaters) < 90 and not e.prop:
            self.floaters.append(Floater(e.x + random.uniform(-3, 3), e.y - e.h * 0.6,
                                         str(int(round(dmg))), 7))
        m = kb * e.kb
        if m > 0 and not e.reaper and not e.frozen:
            dx, dy = e.x - sx, e.y - sy
            d = math.hypot(dx, dy) or 1
            f = max(e.spd, 1.8) * min(3.0, m) * 1.4
            e.kbx, e.kby = dx / d * f, dy / d * f
            e.kbt = 4
        self.sfx("hit")
        if e.hp <= 0:
            self.kill(e, w)

    def freeze_enemy(self, e, frames):
        if e.dead or e.prop or e.reaper or e.res_freeze >= 1:
            return
        new = e.frozen == 0
        e.frozen = max(e.frozen, int(frames * (1 - e.res_freeze)))
        if new:
            self.arc.on_freeze(e)

    def kill(self, e, w):
        if e.dead:
            return
        if e.reaper:
            e.hp = e.maxhp
            return
        e.dead = True
        for _ in range(4 if not e.boss else 16):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.5, 2.5)
            self.particles.append(Particle(e.x, e.y - e.h * 0.3, math.cos(a) * s, math.sin(a) * s,
                                           random.choice((7, 13, 8)), random.randint(6, 12)))
        if e.prop:
            self.drop_light_item(e.x, e.y)
            return
        self.kills += 1
        if w is not None:
            w.kills += 1
        self.arc.on_kill(e, w)
        self.sfx("pop")
        if e.xp:
            self.drop_gem(e.x, e.y, e.xp)
        if e.treasure is not None:
            ch = Pickup("chest", e.x, e.y)
            ch.treasure = e.treasure
            self.pickups.append(ch)

    def drop_gem(self, x, y, value):
        if self.gem_count >= data.MAX_GEMS:
            if self.big_gem is None or self.big_gem not in self.pickups:
                self.big_gem = Pickup("gem", x, y, 0)
                self.pickups.append(self.big_gem)
            self.big_gem.value += value
            return
        self.pickups.append(Pickup("gem", x, y, value))
        self.gem_count += 1

    def remove_pickup(self, it):
        """Remove a pickup without collecting it (Pentagram erases items)."""
        if it in self.pickups:
            self.pickups.remove(it)
            if it.kind == "gem":
                if it is self.big_gem:
                    self.big_gem = None
                else:
                    self.gem_count -= 1

    def drop_light_item(self, x, y):
        lv = self.level
        luck = self.pstats["luck"]
        orolog = getattr(self.arc, "orologion_mult", 1.0)
        opts = [(k, w * (1 if k in data.GOLD else luck) * (orolog if k == "clock" else 1))
                for k, w, mn in data.LIGHT_DROPS if lv >= mn]
        r = random.uniform(0, sum(w for _, w in opts))
        for k, w in opts:
            r -= w
            if r <= 0:
                break
        self.pickups.append(Pickup(k, x, y, data.GOLD.get(k, 0)))

    def breathe_fire(self):
        p = self.p
        fx, fy = p.face_x8, p.face_y8
        base = math.atan2(fy, fx) if (fx or fy) else (0 if p.face_x > 0 else math.pi)
        for _ in range(12):
            a = base + random.uniform(-0.45, 0.45)
            v = random.uniform(2.5, 4.5) * PX
            self.projs.append(Proj("fire", None, p.x, p.y, math.cos(a) * v, math.sin(a) * v,
                                   30 * self.pstats["might"], sec(0.6), 999, 6, 0.5))

    def update_enemies(self):
        p = self.p
        gfreeze = self.freeze_t > 0
        max_dx, max_dy = W * 0.8, H * 0.85
        for e in self.enemies:
            if e.dead:
                continue
            if e.flash:
                e.flash -= 1
            if e.prop:
                if abs(e.x - p.x) > W * 1.2 or abs(e.y - p.y) > H * 1.2:
                    e.dead = True
                continue
            if e.ttl > 0:
                e.ttl -= 1
                if e.ttl == 0:
                    e.dead = True
                    continue
            if e.frozen:
                e.frozen -= 1
                continue
            if gfreeze and not e.reaper:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d = math.hypot(dx, dy) or 1
            if e.kbt > 0:
                e.kbt -= 1
                e.x += e.kbx
                e.y += e.kby
            elif e.vx or e.vy:
                e.x += e.vx
                e.y += e.vy
            else:
                e.x += dx / d * e.spd
                e.y += dy / d * e.spd
                e.flip = dx < 0
            if d < e.r + 6:
                self.hurt_player(e.dmg)
            if e.ttl < 0 and (abs(dx) > max_dx or abs(dy) > max_dy):
                e.x = p.x + dx * 0.9
                e.y = p.y + dy * 0.9
        for cell in self.grid.values():
            n = len(cell)
            if n < 2:
                continue
            for i in range(n):
                a = cell[i]
                if a.dead or a.prop or a.reaper:
                    continue
                for j in range(i + 1, min(n, i + 6)):
                    b = cell[j]
                    if b.dead or b.prop:
                        continue
                    dx, dy = b.x - a.x, b.y - a.y
                    rr = (a.r + b.r) * 0.8
                    d2 = dx * dx + dy * dy
                    if d2 < rr * rr:
                        d = math.sqrt(d2) or 0.1
                        push = (rr - d) * 0.25
                        ux, uy = dx / d, dy / d
                        a.x -= ux * push
                        a.y -= uy * push
                        b.x += ux * push
                        b.y += uy * push
        self.enemies = [e for e in self.enemies if not e.dead]

    def update_hazards(self):
        p = self.p
        keep = []
        for hz in self.hazards:
            hz.t += 1
            if hz.t >= hz.fuse:
                if (p.x - hz.x) ** 2 + (p.y - hz.y) ** 2 < hz.r ** 2:
                    self.hurt_player(hz.dmg)
                for _ in range(8):
                    a = random.uniform(0, math.tau)
                    self.particles.append(Particle(hz.x, hz.y, math.cos(a) * 2, math.sin(a) * 2,
                                                   random.choice((9, 10, 7)), 10))
                continue
            keep.append(hz)
        self.hazards = keep

    def update_pickups(self):
        p = self.p
        mag = self.pstats["magnet"]
        mag2 = mag * mag
        keep = []
        for it in self.pickups:
            it.t += 1
            dx, dy = p.x - it.x, p.y - it.y
            d2 = dx * dx + dy * dy
            if it.kind != "chest" and not it.fly and d2 < mag2:
                it.fly = True
                it.vel = -2.0
            if it.fly:
                d = math.sqrt(d2) or 1
                it.vel = min(it.vel + 0.5, 13)
                it.x += dx / d * it.vel
                it.y += dy / d * it.vel
            if d2 < 196:
                self.collect(it)
                continue
            keep.append(it)
        self.pickups = keep

    def gain_gold(self, n):
        n = int(round(n * self.pstats["greed"]))
        self.gold += n
        self.arc.on_gold(n)

    def collect(self, it):
        k = it.kind
        p = self.p
        if k == "gem":
            if it is self.big_gem:
                self.big_gem = None
            else:
                self.gem_count -= 1
            self.gain_xp(self.arc.xp_gain(it.value))
            self.sfx("gem")
        elif k in data.GOLD:
            self.gain_gold(it.value)
            self.sfx("coin")
        elif k == "chicken":
            self.heal(30)
            self.sfx("chicken")
        elif k == "rosary":
            self.flash_t = 8
            self.sfx("rosary")
            for e in self.targetable():
                if not e.reaper:
                    self.kill(e, None)
        elif k == "clock":
            self.freeze_t = sec(10)
            for e in self.enemies:
                self.freeze_enemy(e, sec(10))
            self.sfx("freeze")
        elif k == "vacuum":
            for g in self.pickups:
                if g.kind == "gem":
                    g.fly = True
            self.sfx("coin")
        elif k == "nduja":
            self.nduja_t = sec(10)
        elif k == "clover":
            self.luck_bonus += 0.1
            self.recompute_stats()
            self.floaters.append(Floater(p.x, p.y - 22, "LUCK UP", 11, 30))
        elif k == "chest":
            self.open_chest(it)

    def gain_xp(self, value):
        mult = self.pstats["growth"] + (1 if self.level in (20, 40) else 0)
        self.xp += value * mult
        while self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            self.pending += 1
            self.xp_next = data.xp_needed(self.level)
            self.recompute_stats()

    # --------------------------------------------------------- level up

    def build_choices(self):
        luck = self.pstats["luck"]
        owned_up = [("w", w.id) for w in self.weapons if not w.maxed]
        owned_up += [("p", pid) for pid, lv in self.passives.items()
                     if lv < data.PASSIVES[pid]["max_level"]]
        gone = set()  # base weapons consumed by an owned evolution
        for evo, (ws, _ps) in data.EVOLUTIONS.items():
            if self.weapon(evo):
                gone.update(ws)
        new = []
        if len(self.weapons) < 6:
            new += [("w", wid) for wid in data.BASE_WEAPONS
                    if not self.weapon(wid) and wid not in gone]
        if len(self.passives) < 6:
            new += [("p", pid) for pid, sp in data.PASSIVES.items()
                    if pid not in self.passives and sp["rarity"] > 0 and pid != "tetraforce"]
        pool = owned_up + new
        if not pool:
            return [("x", "chicken"), ("x", "gold")]
        n = 3 + (1 if random.random() < 1 - 1 / luck else 0)
        picks = []
        x = 2 if self.level % 2 == 0 else 1
        for _ in range(2):
            avail = [o for o in owned_up if o not in picks]
            if avail and random.random() < 1 + 0.3 * x - 1 / luck:
                picks.append(random.choice(avail))
        rest = [o for o in pool if o not in picks]
        while len(picks) < n and rest:
            weights = [max(1, (data.WEAPONS if t == "w" else data.PASSIVES)[i]["rarity"])
                       for t, i in rest]
            o = random.choices(rest, weights)[0]
            picks.append(o)
            rest.remove(o)
        random.shuffle(picks)
        return picks

    def apply_choice(self, opt):
        t, i = opt
        if t == "w":
            w = self.weapon(i)
            if w:
                w.level += 1
            else:
                self.weapons.append(Weapon(i))
        elif t == "p":
            self.passives[i] = self.passives.get(i, 0) + 1
            self.recompute_stats()
        elif i == "chicken":
            self.heal(30)
        else:
            self.gain_gold(25)

    def option_text(self, opt):
        """(name, tag, description) for a level-up option (wiki text)."""
        t, i = opt
        if t == "x":
            return ("Floor Chicken", "", "Heals 30 HP.") if i == "chicken" else \
                ("Gold Coins", "", "Gain 25 gold.")
        if t == "w":
            spec = data.WEAPONS[i]
            w = self.weapon(i)
            if not w:
                return spec["name"], "New!", spec["desc"]
            lv = spec["level_desc"]
            desc = lv[w.level] if w.level < len(lv) else ""
            return spec["name"], f"Lv {w.level + 1}", desc
        spec = data.PASSIVES[i]
        lv = self.passives.get(i, 0)
        return spec["name"], "New!" if lv == 0 else f"Lv {lv + 1}", spec["desc"]

    # ------------------------------------------------------------- chest

    def open_chest(self, it):
        tr = it.treasure or {}
        luck = self.pstats["luck"]
        if str(tr.get("reward1", "")).lower() == "arcana":
            self.open_arcana_pick()
            return
        pct = lambda k: float(tr.get(k) or 0) / 100
        if self.chests_opened < len(data.CHEST_SEQUENCE):
            n = data.CHEST_SEQUENCE[self.chests_opened]
        else:
            r = random.random()
            n = 5 if r < pct("tier3") * luck else 3 if r < pct("tier2") * luck else 1
        n = max(n, self.arc.chest_min_items())
        self.chests_opened += 1
        can_evo = str(tr.get("evo", "")) == "1"
        items = []
        for k in range(n):
            res = self.try_evolve() if can_evo and k == 0 else None
            items.append(res or self.random_upgrade())
        lo, hi = {1: (100, 200), 3: (300, 600), 5: (500, 1000)}.get(n, (100, 200))
        gold = random.randint(lo, hi)
        self.gain_gold(gold)
        self.chest = dict(t=0, reveal=45 + 15 * n, items=items, gold=gold, coins=[])
        self.state = "chest"
        self.sfx("chest")

    def evolvable(self):
        for evo, (ws, ps) in data.EVOLUTIONS.items():
            if self.weapon(evo):
                continue
            owned = [self.weapon(w) for w in ws]
            if all(o and o.maxed for o in owned) and all(p in self.passives for p in ps):
                return evo, owned
        return None

    def try_evolve(self):
        found = self.evolvable()
        if not found:
            return None
        evo, owned = found
        nw = Weapon(evo)
        nw.dmg_done = sum(o.dmg_done for o in owned)
        nw.kills = sum(o.kills for o in owned)
        self.weapons[self.weapons.index(owned[0])] = nw
        for o in owned[1:]:
            self.weapons.remove(o)
        return ("evo", evo)

    def random_upgrade(self):
        opts = [("w", w.id) for w in self.weapons if not w.maxed]
        opts += [("p", pid) for pid, lv in self.passives.items()
                 if lv < data.PASSIVES[pid]["max_level"]]
        if not opts:
            self.gain_gold(25)
            return ("x", "gold")
        t, i = random.choice(opts)
        if t == "w":
            self.weapon(i).level += 1
        else:
            self.passives[i] += 1
            self.recompute_stats()
        return (t, i)

    def open_arcana_pick(self):
        pool = [a for a in data.ARCANAS if not self.arc.has(a)]
        random.shuffle(pool)
        self.arcana_pick = dict(options=pool[:3], sel=0)
        self.state = "arcana_chest"
        self.menu_delay = 10
        self.sfx("chest")

    # ------------------------------------------------------------ autopilot

    def autopilot_choice(self):
        """Test-only draft: evolution passives > new weapons > weapon levels > passives."""
        wanted = {p for ws, ps in data.EVOLUTIONS.values() for p in ps
                  if any(self.weapon(w) for w in ws)}
        def score(opt):
            t, i = opt
            if t == "p" and i in wanted:
                return 0
            if t == "w":
                return 1 if not self.weapon(i) else 2
            return 3
        return min(range(len(self.choices)), key=lambda k: score(self.choices[k]))

    def autopilot(self):
        """Test-only steering: keep ~50px from the nearest enemy, strafe, grab items."""
        p = self.p
        fx = fy = 0.0
        for e in self.query(p.x, p.y, 36):
            if e.prop:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d2 = max(dx * dx + dy * dy, 16)
            fx += dx / d2 * 60
            fy += dy / d2 * 60
        near = self.nearest_enemies(p.x, p.y, 1)
        if near:
            e = near[0]
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy) or 1
            if any(w.kind in ("whip", "tear") for w in self.weapons):
                # whips hit a horizontal band: line up vertically, keep ~50px sideways
                fy += max(-1.0, min(1.0, dy / 12))
                fx += (1.0 if abs(dx) > 60 else 0.15) * (1 if dx > 0 else -1)  # face the target
                crowded = len(self.query(p.x, p.y, 40)) >= 4
                if not crowded and abs(dx) < 90 and (dx > 0) != (p.face_x > 0):
                    fx = 1.0 if dx > 0 else -1.0  # turn around so the slash lands
            else:
                pull = 1.0 if d > 70 else -1.0 if d < 45 else 0.0
                fx += dx / d * pull - dy / d * 0.7
                fy += dy / d * pull + dx / d * 0.7
        best = None
        for it in self.pickups:
            d2 = (it.x - p.x) ** 2 + (it.y - p.y) ** 2
            if d2 < 160 ** 2 and (best is None or d2 < best[0]):
                best = (d2, it)
        if best:
            d = math.sqrt(best[0]) or 1
            calm = not near or (near[0].x - p.x) ** 2 + (near[0].y - p.y) ** 2 > 60 ** 2
            healthy = p.hp > self.pstats["maxhp"] * 0.5
            wgt = 1.5 if best[1].kind == "chest" else 1.6 if calm else 1.0 if healthy else 0.5
            fx += (best[1].x - p.x) / d * wgt
            fy += (best[1].y - p.y) / d * wgt
        return fx, fy
