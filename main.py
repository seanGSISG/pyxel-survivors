"""Pyxel Survivors: a small Vampire Survivors clone.

Move with arrows / WASD / left stick. Weapons fire on their own.
Survive 30 minutes in the Mad Forest until the Reaper comes.

    uv run --with pyxel python main.py
"""

import math
import random

import pyxel

import data
import icons
import sprites
from weapons import Proj, Weapon, draw_aura, draw_proj, sec, update_proj

W, H = 320, 240
FPS = 30
MIN = 60 * FPS
# Extra palette entries for terrain (indices 16..20).
TERRAIN = [0x1E3D22, 0x26502A, 0x33662F, 0x173019, 0x4A7A3A]
G_DARK, G_MID, G_LIGHT, G_SHADOW, G_TUFT = 16, 17, 18, 19, 20

UP = (pyxel.KEY_UP, pyxel.KEY_W, pyxel.GAMEPAD1_BUTTON_DPAD_UP)
DOWN = (pyxel.KEY_DOWN, pyxel.KEY_S, pyxel.GAMEPAD1_BUTTON_DPAD_DOWN)
LEFT = (pyxel.KEY_LEFT, pyxel.KEY_A, pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
RIGHT = (pyxel.KEY_RIGHT, pyxel.KEY_D, pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
OK = (pyxel.KEY_RETURN, pyxel.KEY_SPACE, pyxel.KEY_Z, pyxel.GAMEPAD1_BUTTON_A)
PAUSE = (pyxel.KEY_ESCAPE, pyxel.KEY_P, pyxel.GAMEPAD1_BUTTON_START)


def held(keys):
    return any(pyxel.btn(k) for k in keys)


def pressed(keys):
    return any(pyxel.btnp(k) for k in keys)


def pressed_rep(keys):
    return any(pyxel.btnp(k, 10, 4) for k in keys)


def hash2(x, y):
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return n ^ (n >> 16)


def mmss(frames):
    s = frames // FPS
    return f"{s // 60:02d}:{s % 60:02d}"


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return lines


def shadow_text(x, y, s, col, sh=0):
    pyxel.text(x + 1, y + 1, s, sh)
    pyxel.text(x, y, s, col)


_GLYPHS = {}


def _glyph_pixels(s):
    """Lit pixel coordinates of `s` in the built-in font (cached)."""
    px = _GLYPHS.get(s)
    if px is None:
        img = pyxel.images[1]
        w = len(s) * 4
        img.rect(0, 248, w + 1, 8, 0)
        img.text(0, 249, s, 7)
        px = [(i, j - 1) for i in range(w) for j in range(1, 7) if img.pget(i, 248 + j) == 7]
        _GLYPHS[s] = px
    return px


def big_text(x, y, s, col, scale=2, sh=0):
    """Built-in font scaled with solid rects, with an optional drop shadow."""
    px = _glyph_pixels(s)
    x, y = int(x), int(y)
    if sh is not None:
        for i, j in px:
            pyxel.rect(x + i * scale + scale // 2 + 1, y + j * scale + scale // 2 + 1,
                       scale, scale, sh)
    for i, j in px:
        pyxel.rect(x + i * scale, y + j * scale, scale, scale, col)


def text_w(s, scale=1):
    return len(s) * 4 * scale


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
        "kind", "x", "y", "hp", "maxhp", "spd", "dmg", "xp", "kb", "r", "flash",
        "kbt", "kbx", "kby", "boss", "prop", "spr", "pal", "scale", "vx", "vy",
        "ttl", "phase", "minute", "reaper", "dead", "flip", "cx", "cy",
    )

    def __init__(self, kind, x, y, level, minute):
        s = data.ENEMIES.get(kind) if kind != "brazier" else None
        self.kind = kind
        self.x, self.y = x, y
        self.flash = self.kbt = 0
        self.kbx = self.kby = self.vx = self.vy = 0.0
        self.ttl = -1
        self.phase = random.randint(0, 7)
        self.minute = minute
        self.dead = False
        self.flip = False
        self.cx = self.cy = 0
        if s is None:  # light source
            self.hp = self.maxhp = 10
            self.spd = self.dmg = self.xp = self.kb = 0
            self.r = 5
            self.boss = self.reaper = False
            self.prop = True
            self.spr, self.pal, self.scale = "brazier", {}, 1.0
            return
        hp = s["hp"] * (level if s.get("hplvl") else 1)
        self.hp = self.maxhp = hp
        self.spd = s["speed"] * data.SPEED_UNIT
        self.dmg = s["dmg"]
        self.xp = s["xp"]
        self.kb = s["kb"]
        self.scale = s.get("scale", 1.0)
        self.r = 6 * self.scale
        self.boss = s.get("boss", False)
        self.reaper = s.get("reaper", False)
        self.prop = False
        self.spr = s["spr"]
        self.pal = s.get("pal", {})
        if self.reaper:
            self.spd = 2.3


class Pickup:
    __slots__ = ("kind", "x", "y", "value", "fly", "vel", "t", "evo", "minute")

    def __init__(self, kind, x, y, value=0):
        self.kind = kind
        self.x, self.y = x, y
        self.value = value
        self.fly = False
        self.vel = 0.0
        self.t = random.randint(0, 60)
        self.evo = False
        self.minute = 0


class Floater:
    __slots__ = ("x", "y", "s", "col", "life")

    def __init__(self, x, y, s, col, life=18):
        self.x, self.y, self.s, self.col, self.life = x, y, s, col, life


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "col", "life")

    def __init__(self, x, y, vx, vy, col, life):
        self.x, self.y, self.vx, self.vy, self.col, self.life = x, y, vx, vy, col, life


# --------------------------------------------------------------------- app


class App:
    W, H = W, H

    def __init__(self, config=None):
        """config (tests): char, minute, god, weapons {id: lvl},
        passives {id: lvl}, level, no_title."""
        self.config = config or {}
        pyxel.init(W, H, title="Pyxel Survivors", fps=FPS, quit_key=pyxel.KEY_NONE)
        pyxel.colors.extend(TERRAIN)
        sprites.load()
        icons.load()
        self.setup_audio()
        self.frame = 0
        self.sel = 0
        self.state = "title"
        self.title_bats = [
            [random.uniform(0, W), random.uniform(0, H), random.uniform(0.5, 1.5)]
            for _ in range(14)
        ]
        self.music_on = False
        if "char" in self.config:
            self.new_game(self.config["char"])
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------- audio

    def setup_audio(self):
        s = pyxel.sounds
        s[0].set("c3e3g3", "p", "4", "n", 2)  # gem
        s[1].set("f1c1", "n", "3", "f", 2)  # enemy hit
        s[2].set("c3e3g3c4e4g4c4", "s", "5", "n", 4)  # level up
        s[3].set("a1f1d1", "n", "6", "f", 4)  # player hurt
        s[4].set("c3g3c4e4g4c4e4g4c4", "s", "5", "n", 5)  # chest fanfare
        s[5].set("a2e2c2", "n", "3", "f", 2)  # whip swoosh
        s[6].set("a3e3", "p", "2", "f", 2)  # wand / knife
        s[7].set("c4g3c3g2c2", "n", "5", "f", 2)  # lightning
        s[8].set("e2c2a1", "n", "3", "f", 4)  # splash
        s[9].set("c2g1", "n", "3", "f", 3)  # death pop
        s[10].set("c4c4g3g3c3c3", "n", "6", "f", 6)  # rosary blast
        s[11].set("b3e4", "p", "4", "n", 3)  # coin
        s[12].set("c3", "s", "3", "n", 3)  # menu move
        s[13].set("c3g3", "s", "4", "n", 4)  # confirm
        s[14].set("g2f2e2d2c2b1a1", "t", "5", "n", 10)  # game over
        s[15].set("a2a2r a2a2", "s", "5", "n", 6)  # boss warning
        s[16].set("c2c3", "t", "4", "n", 3)  # chicken
        s[17].set("c1c1c1", "n", "6", "f", 8)  # freeze
        # music: melody A/B over a driving bass in A minor
        mel_a = ("e3ra3b3 c4b3a3e3 f3ra3c4 d4c4a3f3 "
                 "g3rb3d4 e4d4b3g3 e3g#3b3e4 d4b3g#3e3")
        mel_b = ("a3a3c4e4 a4g4e4c4 f4e4d4c4 a3c4f4a4 "
                 "g4f4e4d4 b3d4g4b3 g#3b3e4g#4 b4a4g#4e4")
        bass = ("a1a2a1a2 a1a2a1a2 f1f2f1f2 f1f2f1f2 "
                "g1g2g1g2 g1g2g1g2 e1e2e1e2 e1e2g#1b1")
        s[20].set(mel_a, "s", "3", "nnnnnnnf", 16)
        s[21].set(mel_b, "s", "3", "nnnnnnnf", 16)
        s[22].set(bass, "t", "5", "n", 16)
        pyxel.musics[0].set([20, 20, 21, 21], [22, 22, 22, 22])
        self.sfx_t = {}

    def sfx(self, name):
        table = {
            "gem": (0, 2, 2), "hit": (1, 2, 3), "level": (2, 3, 0),
            "hurt": (3, 3, 4), "chest": (4, 3, 0), "whip": (5, 2, 4),
            "shot": (6, 2, 4), "zap": (7, 3, 4), "splash": (8, 2, 6),
            "pop": (9, 2, 3), "rosary": (10, 3, 0), "coin": (11, 2, 2),
            "move": (12, 3, 0), "ok": (13, 3, 0), "over": (14, 3, 0),
            "boss": (15, 3, 0), "chicken": (16, 3, 0), "freeze": (17, 3, 0),
        }
        snd, ch, gap = table[name]
        if self.frame - self.sfx_t.get(ch, -99) < gap:
            return
        self.sfx_t[ch] = self.frame
        pyxel.play(ch, snd)

    def sfx_fire(self, kind):
        if kind in ("whip", "tear"):
            self.sfx("whip")
        elif kind in ("wand", "holy", "knife", "edge", "fire", "hellfire"):
            self.sfx("shot")

    # ----------------------------------------------------------- setup

    def new_game(self, char_idx):
        cfg = self.config
        self.char = data.CHARACTERS[char_idx]
        self.p = Player(self.char)
        self.t = int(cfg.get("minute", 0) * MIN)
        self.god = cfg.get("god", False)
        self.enemies, self.projs, self.pickups = [], [], []
        self.floaters, self.particles = [], []
        self.weapons = [Weapon(self.char["weapon"])]
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
        self.pending = 0
        self.chests_opened = 0
        self.luck_bonus = 0.0
        self.freeze_t = self.flash_t = self.nduja_t = 0
        self.shake = 0
        self.spawn_t = 0
        self.light_t = 0
        self.wave_min = -1
        self.events = []
        self.big_gem = None
        self.gem_count = 0
        self.enemy_count = 0
        self.reapers = 0
        self.banner, self.banner_t = "", 0
        self.grid = {}
        self.choices = []
        self.menu_delay = 0
        self.chest = None
        self.result = None
        self.hp_healed = 0.0
        self.recompute_stats()
        self.p.hp = self.pstats["maxhp"]
        if cfg.get("chest"):  # test hook: an evolution-capable chest nearby
            ch = Pickup("chest", 40, 0)
            ch.evo = True
            self.pickups.append(ch)
        self.cam_x, self.cam_y = -W / 2, -H / 2
        self.state = "play"
        pyxel.playm(0, loop=True)

    @property
    def weapon_ids(self):
        return [f"{w.id}:{w.level}" for w in self.weapons]

    def weapon(self, wid):
        for w in self.weapons:
            if w.id == wid:
                return w
        return None

    def recompute_stats(self):
        pv = self.passives.get
        ch = self.char
        old_max = getattr(self, "pstats", {}).get("maxhp")
        might_char = min(0.5, ch.get("might_per10", 0) * (self.level // 10))
        ps = {
            "might": 1 + 0.1 * pv("spinach", 0) + might_char,
            "armor": ch.get("armor", 0) + pv("armor", 0),
            "maxhp": ch["hp"] * (1.2 ** pv("hollow_heart", 0)),
            "recovery": 0.2 * pv("pummarola", 0),
            "cooldown": 1 - 0.08 * pv("empty_tome", 0),
            "area": 1 + 0.1 * pv("candelabrador", 0),
            "speed": 1 + 0.1 * pv("bracer", 0) + ch.get("speed", 0),
            "duration": 1 + 0.1 * pv("spellbinder", 0),
            "amount": pv("duplicator", 0) + ch.get("amount", 0),
            "move": 1 + 0.1 * pv("wings", 0),
            "magnet": data.MAGNET_BASE * data.ATTRACTORB_MULT[pv("attractorb", 0)],
            "luck": 1 + 0.1 * pv("clover", 0) + self.luck_bonus,
            "growth": 1 + 0.08 * pv("crown", 0) + ch.get("growth", 0),
        }
        if old_max is not None and ps["maxhp"] > old_max:
            self.p.hp += ps["maxhp"] - old_max
        self.pstats = ps

    # ------------------------------------------------------------ update

    def update(self):
        self.frame += 1
        fn = getattr(self, "update_" + self.state)
        fn()

    def update_title(self):
        for b in self.title_bats:
            b[0] += b[2]
            b[1] += math.sin(self.frame * 0.05 + b[2] * 10) * 0.5
            if b[0] > W + 10:
                b[0], b[1] = -10, random.uniform(0, H)
        if pressed(OK):
            self.sfx("ok")
            self.state = "select"

    def update_select(self):
        n = len(data.CHARACTERS)
        if pressed_rep(LEFT):
            self.sel = (self.sel - 1) % n
            self.sfx("move")
        if pressed_rep(RIGHT):
            self.sel = (self.sel + 1) % n
            self.sfx("move")
        if pressed(OK):
            self.sfx("ok")
            self.new_game(self.sel)
        if pressed(PAUSE):
            self.state = "title"

    def update_paused(self):
        if pressed(PAUSE) or pressed(OK):
            self.state = "play"
            pyxel.playm(0, loop=True)
        elif pyxel.btnp(pyxel.KEY_Q):
            self.state = "title"

    def update_over(self):
        if self.menu_delay > 0:
            self.menu_delay -= 1
        elif pressed(OK):
            self.sfx("ok")
            self.state = "title"

    def update_levelup(self):
        if self.menu_delay > 0:
            self.menu_delay -= 1
            return
        if self.config.get("autopilot"):
            self.sel = 0
            self.pick_choice()
            return
        n = len(self.choices)
        if pressed_rep(UP):
            self.sel = (self.sel - 1) % n
            self.sfx("move")
        if pressed_rep(DOWN):
            self.sel = (self.sel + 1) % n
            self.sfx("move")
        for i, k in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3, pyxel.KEY_4)):
            if i < n and pyxel.btnp(k):
                self.sel = i
                self.pick_choice()
                return
        if pressed(OK):
            self.pick_choice()

    def update_chest(self):
        c = self.chest
        c["t"] += 1
        if c["t"] % 3 == 0 and c["t"] < c["reveal"]:
            ang = random.uniform(-2.6, -0.5)
            spd = random.uniform(1.5, 4)
            c["coins"].append([W / 2, H / 2 + 10, math.cos(ang) * spd, math.sin(ang) * spd])
        for co in c["coins"]:
            co[0] += co[2]
            co[1] += co[3]
            co[3] += 0.15
        auto = self.config.get("autopilot")
        if c["t"] > c["reveal"] + 10 and (pressed(OK) or auto):
            self.sfx("ok")
            self.chest = None
            self.state = "play"
            self.p.inv = max(self.p.inv, 15)
        elif c["t"] < c["reveal"] and c["t"] > 15 and pressed(OK):
            c["t"] = c["reveal"]  # skip animation

    def update_play(self):
        if pressed(PAUSE):
            self.state = "paused"
            pyxel.stop()
            return
        self.t += 1
        p, ps = self.p, self.pstats
        # --- player movement
        dx = (1 if held(RIGHT) else 0) - (1 if held(LEFT) else 0)
        dy = (1 if held(DOWN) else 0) - (1 if held(UP) else 0)
        ax = pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTX) / 32768
        ay = pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTY) / 32768
        if abs(ax) > 0.25 or abs(ay) > 0.25:
            dx, dy = ax, ay
        if self.config.get("autopilot"):
            dx, dy = self.autopilot()
        p.moving = bool(dx or dy)
        if p.moving:
            ln = math.hypot(dx, dy)
            spd = data.PLAYER_SPEED * ps["move"]
            p.x += dx / ln * spd
            p.y += dy / ln * spd
            p.walk += 1
            if abs(dx) > 0.2:
                p.face_x = 1 if dx > 0 else -1
            p.face_x8 = round(dx / ln) if abs(dx / ln) > 0.38 else 0
            p.face_y8 = round(dy / ln) if abs(dy / ln) > 0.38 else 0
        if p.inv > 0:
            p.inv -= 1
        if p.hurt > 0:
            p.hurt -= 1
        if ps["recovery"] and p.hp < ps["maxhp"]:
            self.heal(ps["recovery"] / FPS, show=False)
        self.cam_x = p.x - W / 2
        self.cam_y = p.y - H / 2
        # --- stage clock, waves, spawns
        self.update_waves()
        # --- spatial grid for queries
        self.build_grid()
        # --- weapons & projectiles
        for w in self.weapons:
            w.update(self)
        if self.nduja_t > 0:
            self.nduja_t -= 1
            if self.nduja_t % sec(0.5) == 0:
                self.breathe_fire()
        self.projs = [pr for pr in self.projs if update_proj(pr, self)]
        # --- enemies
        self.update_enemies()
        # --- pickups
        self.update_pickups()
        # --- fx
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
        # --- death / level-up
        if p.hp <= 0:
            self.end_run()
            return
        if self.pending > 0:
            self.open_levelup()

    def autopilot(self):
        """Test-only steering: flee nearby enemies, orbit, drift toward gems/chests."""
        p = self.p
        fx = fy = 0.0
        for e in self.query(p.x, p.y, 26):
            if e.prop:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d2 = max(dx * dx + dy * dy, 16)
            fx += dx / d2 * 40
            fy += dy / d2 * 40
        near = self.nearest_enemies(p.x, p.y, 1)
        if near:  # hold ~40px from the nearest enemy, strafing around it
            e = near[0]
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy) or 1
            pull = 1.0 if d > 45 else -1.0 if d < 30 else 0.0
            fx += dx / d * pull - dy / d * 0.7
            fy += dy / d * pull + dx / d * 0.7
        best = None
        for it in self.pickups:
            d2 = (it.x - p.x) ** 2 + (it.y - p.y) ** 2
            if d2 < 110 ** 2 and (best is None or d2 < best[0]):
                best = (d2, it)
        if best:
            d = math.sqrt(best[0]) or 1
            w = 1.2 if best[1].kind == "chest" else 0.5
            fx += (best[1].x - p.x) / d * w
            fy += (best[1].y - p.y) / d * w
        return fx, fy

    def update_waves(self):
        minute = self.t // MIN
        if self.t % MIN == 0 or self.wave_min < 0:
            if minute != self.wave_min:
                self.start_minute(minute)
        # timed events inside the minute
        while self.events and self.events[0][0] <= self.t:
            _, kind, arg = self.events.pop(0)
            self.run_event(kind, arg)
        if minute >= data.STAGE_MINUTES:
            return
        wave = data.WAVES[min(minute, len(data.WAVES) - 1)]
        self.spawn_t -= 1
        if self.spawn_t <= 0:
            self.spawn_t = sec(wave["iv"])
            alive = self.enemy_count
            if alive < data.MAX_ENEMIES:
                if alive < wave["min"]:
                    n = min(wave["min"] - alive, 40)
                    for i in range(n):
                        self.spawn_enemy(wave["e"][i % len(wave["e"])])
                else:
                    for k in wave["e"]:
                        self.spawn_enemy(k)
        # light sources: one attempt per second, 10% x luck, max 10 alive
        self.light_t += 1
        if self.light_t >= FPS:
            self.light_t = 0
            lights = sum(1 for e in self.enemies if e.prop)
            if lights < 10 and random.random() < min(0.5, 0.1 * self.pstats["luck"]):
                x, y = self.offscreen_point(12)
                self.enemies.append(Enemy("brazier", x, y, 1, minute))

    def start_minute(self, minute):
        self.wave_min = minute
        self.events = []
        if minute >= data.STAGE_MINUTES:
            if self.reapers == 0:
                for e in self.enemies:
                    if not e.prop:
                        e.dead = True
                self.enemies = [e for e in self.enemies if not e.dead]
                self.show_banner("THE REAPER COMES", 150)
                self.flash_t = 10
            self.spawn_enemy("reaper")
            self.reapers += 1
            self.sfx("boss")
            return
        wave = data.WAVES[minute]
        for b in wave.get("boss", []):
            self.spawn_enemy(b)
        if wave.get("boss"):
            self.sfx("boss")
        for kind, arg in wave.get("ev", []):
            if kind in ("batswarm", "ghostswarm"):
                for k in range(arg):
                    at = self.t + int((k + 0.5) * MIN / arg)
                    self.events.append((at, kind, 0))
            else:
                self.events.append((self.t + sec(2), kind, arg))
        self.events.sort()
        if minute == 0:
            for i in range(10):
                self.spawn_enemy(wave["e"][0])

    def run_event(self, kind, arg):
        p = self.p
        if kind in ("batswarm", "ghostswarm"):
            ek = "swarmbat" if kind == "batswarm" else "swarmghost"
            ang = random.uniform(0, math.tau)
            vx, vy = math.cos(ang) * 4.2, math.sin(ang) * 4.2
            cx = p.x - math.cos(ang) * (W * 0.75)
            cy = p.y - math.sin(ang) * (H * 0.75)
            for _ in range(24 if ek == "swarmbat" else 18):
                e = self.spawn_enemy(ek, cx + random.uniform(-28, 28),
                                     cy + random.uniform(-28, 28), force=True)
                e.vx, e.vy = vx, vy
                e.ttl = sec(4)
            self.show_banner("SWARM!" if ek == "swarmbat" else "GHOSTS!", 45)
        elif kind == "flowerring":
            n = 40
            for i in range(n):
                a = i * math.tau / n
                e = self.spawn_enemy("flowerwall", p.x + math.cos(a) * 190,
                                     p.y + math.sin(a) * 150, force=True)
                e.ttl = sec(arg)
            self.show_banner("FLOWER WALL", 60)

    def offscreen_point(self, margin=20):
        left, top = self.cam_x - margin, self.cam_y - margin
        w, h = W + margin * 2, H + margin * 2
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

    def spawn_enemy(self, kind, x=None, y=None, force=False):
        if not force and self.enemy_count >= data.MAX_ENEMIES and not data.ENEMIES[kind].get("boss") \
                and kind != "reaper":
            return None
        if x is None:
            x, y = self.offscreen_point(20 + 6 * data.ENEMIES[kind].get("scale", 1))
        e = Enemy(kind, x, y, self.level, self.t // MIN)
        self.enemies.append(e)
        self.enemy_count += 1
        return e

    def show_banner(self, text, frames):
        self.banner, self.banner_t = text, frames

    # --------------------------------------------------------- spatial grid

    CELL = 32

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
        pad = r + 16
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
        for cx in range(int((x0 - 16) // c), int((x0 + w + 16) // c) + 1):
            for cy in range(int((y0 - 16) // c), int((y0 + h + 16) // c) + 1):
                for e in self.grid.get((cx, cy), ()):
                    if not e.dead and x0 - e.r <= e.x <= x0 + w + e.r \
                            and y0 - e.r <= e.y <= y0 + h + e.r:
                        out.append(e)
        return out

    def targetable(self):
        return [e for e in self.enemies if not e.dead and not e.prop
                and abs(e.x - self.p.x) < W / 2 + 10 and abs(e.y - self.p.y) < H / 2 + 10]

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
        if len(self.floaters) < 90 and not e.prop:
            self.floaters.append(Floater(e.x + random.uniform(-3, 3), e.y - e.r - 4,
                                         str(int(round(dmg))), 7))
        m = kb * e.kb
        if m > 0 and not e.reaper:
            dx, dy = e.x - sx, e.y - sy
            d = math.hypot(dx, dy) or 1
            f = max(e.spd, 1.2) * min(3.0, m) * 1.4
            e.kbx, e.kby = dx / d * f, dy / d * f
            e.kbt = 4
        self.sfx("hit")
        if e.hp <= 0:
            self.kill(e, w)

    def kill(self, e, w):
        e.dead = True
        if e.reaper:
            e.dead = False  # immune
            e.hp = e.maxhp
            return
        for _ in range(4 if not e.boss else 16):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.5, 2.5)
            self.particles.append(Particle(e.x, e.y, math.cos(a) * s, math.sin(a) * s,
                                           random.choice((7, 13, 8)), random.randint(6, 12)))
        if e.prop:
            self.drop_light_item(e.x, e.y)
            return
        self.kills += 1
        if w is not None:
            w.kills += 1
        self.sfx("pop")
        if e.xp:
            self.drop_gem(e.x, e.y, e.xp)
        if e.boss:
            ch = Pickup("chest", e.x, e.y)
            ch.evo = e.minute in data.EVO_CHEST_MINUTES
            ch.minute = e.minute
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

    def drop_light_item(self, x, y):
        lv = self.level
        luck = self.pstats["luck"]
        opts = [(k, w * (1 if k in data.GOLD else luck)) for k, w, mn in data.LIGHT_DROPS
                if lv >= mn]
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
        for i in range(12):
            a = base + random.uniform(-0.45, 0.45)
            v = random.uniform(2.5, 4.5)
            pr = Proj("fire", None, p.x, p.y, math.cos(a) * v, math.sin(a) * v,
                      30 * self.pstats["might"], sec(0.6), 999, 4, 0.5)
            self.projs.append(pr)

    def heal(self, amount, show=True):
        p = self.p
        mx = self.pstats["maxhp"]
        before = p.hp
        p.hp = min(mx, p.hp + amount)
        got = p.hp - before
        self.hp_healed += got
        if show and got >= 1:
            self.floaters.append(Floater(p.x, p.y - 14, f"+{int(got)}", 11, 24))

    def hurt_player(self, dmg):
        p = self.p
        if p.inv > 0 or self.god:
            return
        dmg = max(1, dmg - self.pstats["armor"])
        p.hp -= dmg
        p.inv = data.INVULN_FRAMES
        p.hurt = 6
        self.shake = 4
        self.sfx("hurt")
        # NO FUTURE: explode on the player when hit
        w = self.weapon("no_future")
        if w is not None:
            st = w.stats(self.pstats)
            self.projs.append(Proj("boom", w, p.x, p.y, dmg=st["dmg"], life=8,
                                   pierce=999, r=22 * st["area"], kb=1.0))

    def update_enemies(self):
        p = self.p
        frozen = self.freeze_t > 0
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
            if frozen and not e.reaper:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d = math.hypot(dx, dy) or 1
            if e.kbt > 0:
                e.kbt -= 1
                e.x += e.kbx
                e.y += e.kby
            elif e.vx or e.vy:  # swarm: straight line
                e.x += e.vx
                e.y += e.vy
            else:
                e.x += dx / d * e.spd
                e.y += dy / d * e.spd
                e.flip = dx < 0
            # contact damage
            if d < e.r + 4:
                self.hurt_player(e.dmg)
            # wrap stragglers to the opposite side (swarms and walls just expire)
            if e.ttl < 0 and (abs(dx) > max_dx or abs(dy) > max_dy):
                e.x = p.x + dx * 0.9
                e.y = p.y + dy * 0.9
        # separation: push overlapping enemies apart (cheap, per cell)
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
                it.vel = -1.5  # small hop away first
            if it.fly:
                d = math.sqrt(d2) or 1
                it.vel = min(it.vel + 0.35, 9)
                step = it.vel
                it.x += dx / d * step
                it.y += dy / d * step
            if d2 < 81:
                self.collect(it)
                continue
            keep.append(it)
        self.pickups = keep

    def collect(self, it):
        k = it.kind
        p = self.p
        if k == "gem":
            if it is self.big_gem:
                self.big_gem = None
            else:
                self.gem_count -= 1
            self.gain_xp(it.value)
            self.sfx("gem")
        elif k in data.GOLD:
            self.gold += it.value
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
            self.floaters.append(Floater(p.x, p.y - 14, "LUCK UP", 11, 30))
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
            if self.char.get("might_per10") and self.level % 10 == 0:
                self.recompute_stats()

    # --------------------------------------------------------- level up

    def build_choices(self):
        luck = self.pstats["luck"]
        owned_up = []  # (type, id) for owned upgradable
        for w in self.weapons:
            if not w.maxed:
                owned_up.append(("w", w.id))
        for pid, lv in self.passives.items():
            if lv < data.PASSIVES[pid]["max"]:
                owned_up.append(("p", pid))
        new = []
        evolved_from = {k for k, v in data.WEAPONS.items()
                        if v.get("evo") and self.weapon(v["evo"])}
        if len(self.weapons) < 6:
            for wid in data.BASE_WEAPONS:
                if not self.weapon(wid) and wid not in evolved_from:
                    new.append(("w", wid))
        if len(self.passives) < 6:
            for pid in data.PASSIVES:
                if pid not in self.passives:
                    new.append(("p", pid))
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
            weights = [self.rarity(o) for o in rest]
            o = random.choices(rest, weights)[0]
            picks.append(o)
            rest.remove(o)
        random.shuffle(picks)
        return picks

    def rarity(self, opt):
        t, i = opt
        return (data.WEAPONS if t == "w" else data.PASSIVES)[i]["rarity"]

    def open_levelup(self):
        self.choices = self.build_choices()
        self.sel = 0
        self.menu_delay = 8
        self.state = "levelup"
        self.flash_t = 4
        self.sfx("level")

    def pick_choice(self):
        t, i = self.choices[self.sel]
        self.sfx("ok")
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
            self.gold += 25
        self.pending -= 1
        if self.pending > 0:
            self.choices = self.build_choices()
            self.sel = 0
            self.menu_delay = 4
        else:
            self.state = "play"
            self.p.inv = max(self.p.inv, 15)
            self.choices = []

    def option_text(self, opt):
        """(name, tag, description) for a level-up option."""
        t, i = opt
        if t == "x":
            if i == "chicken":
                return "Floor Chicken", "", "Heals 30 HP."
            return "Gold Coins", "", "Gain 25 gold."
        if t == "w":
            spec = data.WEAPONS[i]
            w = self.weapon(i)
            if not w:
                return spec["name"], "New!", spec["desc"]
            return spec["name"], f"Lv {w.level + 1}", self.level_desc(spec["levels"][w.level - 1])
        spec = data.PASSIVES[i]
        lv = self.passives.get(i, 0)
        return spec["name"], "New!" if lv == 0 else f"Lv {lv + 1}", spec["desc"]

    @staticmethod
    def level_desc(delta):
        parts = []
        for k, v in delta.items():
            if k == "amount":
                parts.append(f"Fires {v} more projectile.")
            elif k == "dmg":
                parts.append(f"Base damage up by {v:g}.")
            elif k == "cd":
                parts.append(f"Cooldown reduced by {-v:g}s.")
            elif k == "area":
                parts.append(f"Base area up by {int(v * 100)}%.")
            elif k == "speed":
                parts.append(f"Base speed up by {int(v * 100)}%.")
            elif k == "dur":
                parts.append(f"Effect lasts {v:g}s longer.")
            elif k == "pierce":
                parts.append(f"Passes through {v} more enemy.")
        return " ".join(parts)

    # ------------------------------------------------------------- chest

    def open_chest(self, it):
        if self.chests_opened < len(data.CHEST_SEQUENCE):
            n = data.CHEST_SEQUENCE[self.chests_opened]
        else:
            luck = self.pstats["luck"]
            r = random.random()
            n = 5 if r < 0.03 * luck else 3 if r < 0.13 * luck else 1
        self.chests_opened += 1
        items = []
        for k in range(n):
            res = None
            if it.evo and k == 0:
                res = self.try_evolve()
            if res is None:
                res = self.random_upgrade()
            items.append(res)
        lo, hi = {1: (100, 200), 3: (300, 600), 5: (500, 1000)}[n]
        gold = int(random.randint(lo, hi) * 1)
        self.gold += gold
        self.chest = dict(t=0, reveal=45 + 15 * n, items=items, gold=gold, coins=[])
        self.state = "chest"
        self.sfx("chest")

    def try_evolve(self):
        for w in self.weapons:
            spec = w.spec
            if w.maxed and spec.get("evo") and spec["evo_with"] in self.passives:
                idx = self.weapons.index(w)
                nw = Weapon(spec["evo"])
                nw.dmg_done = w.dmg_done
                nw.kills = w.kills
                self.weapons[idx] = nw
                return ("evo", spec["evo"])
        return None

    def random_upgrade(self):
        opts = [("w", w.id) for w in self.weapons if not w.maxed]
        opts += [("p", pid) for pid, lv in self.passives.items()
                 if lv < data.PASSIVES[pid]["max"]]
        if not opts:
            self.gold += 25
            return ("x", "gold")
        t, i = random.choice(opts)
        if t == "w":
            self.weapon(i).level += 1
        else:
            self.passives[i] += 1
            self.recompute_stats()
        return (t, i)

    # ------------------------------------------------------------ end

    def end_run(self):
        cleared = self.t >= data.STAGE_MINUTES * MIN
        self.result = dict(cleared=cleared)
        if cleared:
            self.gold += 500
        self.state = "over"
        self.menu_delay = 30
        pyxel.stop()
        self.sfx("over")

    # ============================================================= DRAW

    def draw(self):
        getattr(self, "draw_" + self.state)()

    def draw_title(self):
        pyxel.cls(G_SHADOW)
        for i in range(0, W, 16):
            for j in range(0, H, 16):
                h = hash2(i, j)
                if h % 5 == 0:
                    pyxel.pset(i + h % 13, j + (h >> 4) % 13, G_MID)
        pyxel.circ(W - 60, 50, 26, 15)
        pyxel.circ(W - 50, 44, 24, G_SHADOW)
        for b in self.title_bats:
            f = (self.frame // 6 + int(b[2] * 10)) % 2
            sprites.draw(f"bat{f}", b[0], b[1])
        big_text(W / 2 - text_w("PYXEL", 4) / 2, 50, "PYXEL", 8, 4, 2)
        big_text(W / 2 - text_w("SURVIVORS", 3) / 2, 90, "SURVIVORS", 7, 3, 1)
        s = "a Vampire Survivors tribute"
        shadow_text(W / 2 - text_w(s) / 2, 122, s, 13)
        sprites.draw("player0" if self.frame // 10 % 2 else "player1", W / 2, 150, scale=2)
        if self.frame // 15 % 2:
            s = "PRESS ENTER"
            shadow_text(W / 2 - text_w(s) / 2, 180, s, 10)
        for k, s in enumerate(["MOVE: ARROWS / WASD / STICK   WEAPONS FIRE ON THEIR OWN",
                               "PAUSE: ESC / P      SURVIVE 30 MINUTES"]):
            shadow_text(W / 2 - text_w(s) / 2, 206 + k * 9, s, 13)

    def draw_select(self):
        pyxel.cls(G_SHADOW)
        s = "CHOOSE YOUR CHARACTER"
        big_text(W / 2 - text_w(s, 2) / 2, 18, s, 10, 2, 0)
        n = len(data.CHARACTERS)
        cw = 70
        x0 = W / 2 - (n * cw + (n - 1) * 6) / 2
        for i, ch in enumerate(data.CHARACTERS):
            x = x0 + i * (cw + 6)
            y = 60
            sel = i == self.sel
            pyxel.rect(x, y, cw, 110, 1 if sel else 0)
            pyxel.rectb(x, y, cw, 110, 10 if sel else 5)
            for a, b in ch["pal"].items():
                pyxel.pal(a, b)
            f = self.frame // 8 % 2 if sel else 0
            sprites.draw(f"player{f}", x + cw / 2, y + 30, scale=2)
            pyxel.pal()
            shadow_text(x + cw / 2 - text_w(ch["name"]) / 2, y + 54, ch["name"], 7)
            icons.draw(ch["weapon"], x + cw / 2, y + 70, 2)
            wn = data.WEAPONS[ch["weapon"]]["name"]
            shadow_text(x + cw / 2 - text_w(wn) / 2, y + 80, wn, 13)
        ch = data.CHARACTERS[self.sel]
        lines = [ch["bonus"], f"Max HP {ch['hp']}" + (f"  Armor {ch['armor']}" if ch.get("armor") else "")]
        for k, s in enumerate(lines):
            shadow_text(W / 2 - text_w(s) / 2, 182 + k * 10, s, 11)
        s = "LEFT/RIGHT choose   ENTER start"
        shadow_text(W / 2 - text_w(s) / 2, 220, s, 13)

    # --- world

    def draw_world(self):
        sx = sy = 0
        if self.shake:
            sx, sy = random.randint(-2, 2), random.randint(-2, 2)
        cx, cy = int(self.cam_x) + sx, int(self.cam_y) + sy
        pyxel.cls(G_DARK)
        pyxel.camera(cx, cy)
        self.draw_terrain(cx, cy)
        # ground-level projectiles (puddles)
        for pr in self.projs:
            if pr.kind in ("water", "borra") and pr.t >= 12:
                draw_proj(pr, self)
        for w in self.weapons:
            if w.spec["kind"] in ("garlic", "soul"):
                draw_aura(w, self)
        for it in self.pickups:
            self.draw_pickup(it)
        # enemies + player sorted by y
        p = self.p
        vis = [e for e in self.enemies
               if cx - 40 < e.x < cx + W + 40 and cy - 40 < e.y < cy + H + 40]
        vis.sort(key=lambda e: e.y)
        drawn_player = False
        for e in vis:
            if not drawn_player and e.y > p.y:
                self.draw_player()
                drawn_player = True
            self.draw_enemy(e)
        if not drawn_player:
            self.draw_player()
        for pr in self.projs:
            if not (pr.kind in ("water", "borra") and pr.t >= 12):
                draw_proj(pr, self)
        for pa in self.particles:
            pyxel.pset(pa.x, pa.y, pa.col)
        for f in self.floaters:
            pyxel.text(f.x - len(f.s) * 2 + 1, f.y + 1, f.s, 0)
            pyxel.text(f.x - len(f.s) * 2, f.y, f.s, f.col)
        pyxel.camera()
        self.draw_offscreen_arrows()
        if self.flash_t:
            pyxel.dither(self.flash_t / 10)
            pyxel.rect(0, 0, W, H, 7)
            pyxel.dither(1.0)
        if self.freeze_t:
            pyxel.dither(0.15)
            pyxel.rect(0, 0, W, H, 12)
            pyxel.dither(1.0)
        self.draw_hud()

    def draw_terrain(self, cx, cy):
        # large lighter patches on a 64px lattice
        for gx in range(cx // 64 - 1, (cx + W) // 64 + 2):
            for gy in range(cy // 64 - 1, (cy + H) // 64 + 2):
                h = hash2(gx, gy)
                if h % 3 == 0:
                    px = gx * 64 + h % 40
                    py = gy * 64 + (h >> 6) % 40
                    pyxel.elli(px, py, 40 + (h >> 10) % 40, 20 + (h >> 14) % 20, G_MID)
        # details on a 16px lattice
        for gx in range(cx // 16 - 1, (cx + W) // 16 + 2):
            for gy in range(cy // 16 - 1, (cy + H) // 16 + 2):
                h = hash2(gx + 7919, gy - 104729)
                x = gx * 16 + h % 12
                y = gy * 16 + (h >> 5) % 12
                r = h % 97
                if r < 12:  # grass tuft
                    pyxel.line(x, y, x - 1, y - 3, G_TUFT)
                    pyxel.line(x + 1, y, x + 1, y - 4, G_LIGHT)
                    pyxel.line(x + 2, y, x + 3, y - 3, G_TUFT)
                elif r < 14:  # flower
                    c = (7, 10, 14, 6)[(h >> 9) % 4]
                    pyxel.pset(x, y, c)
                    pyxel.pset(x + 1, y + 1, c)
                    pyxel.pset(x - 1, y + 1, c)
                    pyxel.pset(x, y + 2, c)
                    pyxel.pset(x, y + 1, 10 if c != 10 else 9)
                elif r < 15:  # stone
                    pyxel.elli(x, y, 5, 3, 13)
                    pyxel.line(x + 1, y, x + 3, y, 7)
                elif r < 16:  # dark bush
                    pyxel.circ(x, y, 5, G_SHADOW)
                    pyxel.circ(x + 4, y + 1, 4, G_SHADOW)
                    pyxel.pset(x - 1, y - 2, G_MID)

    def draw_player(self):
        p = self.p
        pyxel.elli(p.x - 6, p.y + 5, 12, 4, G_SHADOW)
        if p.inv and self.frame % 4 < 2 and p.hurt:
            pass
        else:
            for a, b in self.char["pal"].items():
                pyxel.pal(a, b)
            if p.hurt:
                for c in range(1, 16):
                    pyxel.pal(c, 8)
            f = (p.walk // 6) % 2 if p.moving else 0
            sprites.draw(f"player{f}", p.x, p.y - 2, flip=p.face_x < 0)
            pyxel.pal()
        # HP bar
        mx = self.pstats["maxhp"]
        pyxel.rect(p.x - 8, p.y + 8, 16, 2, 1)
        pyxel.rect(p.x - 8, p.y + 8, max(0, 16 * p.hp / mx), 2, 8)

    def draw_enemy(self, e):
        if e.prop:
            sprites.draw("brazier", e.x, e.y - 4)
            fl = self.frame // 3 % 3
            pyxel.circ(e.x, e.y - 9, 2 + (fl == 1), 9 if not e.flash else 7)
            pyxel.pset(e.x, e.y - 12 - fl, 10)
            pyxel.pset(e.x, e.y - 9, 10)
            return
        pyxel.elli(e.x - e.r, e.y + e.r * 0.7, e.r * 2, e.r * 0.6, G_SHADOW)
        for a, b in e.pal.items():
            pyxel.pal(a, b)
        if e.flash:
            for c in range(1, 16):
                pyxel.pal(c, 7)
        elif self.freeze_t and not e.reaper:
            for c in range(1, 16):
                pyxel.pal(c, 6 if c in (7, 15, 10, 14, 13) else 12)
        if e.reaper:
            name = "reaper0"
        else:
            name = f"{e.spr}{(self.frame // 8 + e.phase) % 2}"
        sprites.draw(name, e.x, e.y - 2 * e.scale, flip=e.flip, scale=e.scale)
        pyxel.pal()
        if e.boss:
            f = self.frame // 4 % 2
            pyxel.tri(e.x - 3, e.y - e.r - 10 - f, e.x + 3, e.y - e.r - 10 - f,
                      e.x, e.y - e.r - 6 - f, 10)

    def draw_pickup(self, it):
        x, y = it.x, it.y
        k = it.kind
        if k == "gem":
            v = it.value
            if v > 9 or it is self.big_gem:
                pyxel.pal(12, 8)
                pyxel.pal(1, 2)
            elif v > 2:
                pyxel.pal(12, 11)
                pyxel.pal(1, 3)
            sc = 1.5 if it is self.big_gem else 1.0
            sprites.draw("gem", x, y, scale=sc)
            pyxel.pal()
            if (it.t // 4) % 16 == 0:
                pyxel.pset(x - 1, y - 2, 7)
        elif k == "chest":
            bob = math.sin(it.t * 0.15) * 1.5
            pyxel.elli(x - 7, y + 4, 14, 4, G_SHADOW)
            if it.evo:
                pyxel.pal(9, 7)
                pyxel.pal(4, 13)
            sprites.draw("chest", x, y - 3 + bob)
            pyxel.pal()
            if it.t // 8 % 2:
                pyxel.pset(x + 5, y - 7 + bob, 7)
        elif k in data.GOLD:
            icons.draw("coin" if k == "coin" else k, x, y)
        elif k == "clover":
            icons.draw("little_clover", x, y)
        else:
            icons.draw(k, x, y + math.sin(it.t * 0.12))

    def draw_offscreen_arrows(self):
        for it in self.pickups:
            if it.kind != "chest":
                continue
            sx, sy = it.x - self.cam_x, it.y - self.cam_y
            if 0 <= sx < W and 0 <= sy < H:
                continue
            ang = math.atan2(sy - H / 2, sx - W / 2)
            ax = min(max(sx, 10), W - 10)
            ay = min(max(sy, 20), H - 10)
            ca, sa = math.cos(ang), math.sin(ang)
            pyxel.tri(ax + ca * 6, ay + sa * 6, ax - sa * 4, ay + ca * 4,
                      ax + sa * 4, ay - ca * 4, 10)

    def draw_hud(self):
        # XP bar
        pyxel.rect(0, 0, W, 8, 1)
        pyxel.rect(0, 0, W * min(1, self.xp / self.xp_next), 8, 12)
        pyxel.rect(0, 0, W * min(1, self.xp / self.xp_next), 2, 6)
        pyxel.rectb(0, 0, W, 8, 5)
        s = f"LV {self.level}"
        shadow_text(W - text_w(s) - 4, 1, s, 7)
        # timer
        s = mmss(self.t)
        big_text(W / 2 - text_w(s, 2) / 2, 11, s, 7, 2, 0)
        # kills & gold
        s = str(self.kills)
        icons.draw("skull", W - 10, 16)
        shadow_text(W - 16 - text_w(s), 14, s, 7)
        s = str(self.gold)
        icons.draw("coin", W - 10, 26)
        shadow_text(W - 16 - text_w(s), 24, s, 10)
        # inventory rows
        for i in range(6):
            x = 3 + i * 11
            pyxel.rectb(x, 10, 10, 10, 5)
            if i < len(self.weapons):
                icons.draw(self.weapons[i].id, x + 5, 15)
            pyxel.rectb(x, 21, 10, 10, 1)
        for i, pid in enumerate(self.passives):
            icons.draw(pid, 3 + i * 11 + 5, 26)
        if self.nduja_t:
            icons.draw("nduja", 8, 38)
        if self.banner_t and self.state == "play":
            s = self.banner
            if self.banner_t > 10 or self.frame % 2:
                big_text(W / 2 - text_w(s, 2) / 2, 60, s, 8 if "REAPER" in s else 10, 2, 0)

    def draw_play(self):
        self.draw_world()

    def dim(self, amt=0.6):
        pyxel.dither(amt)
        pyxel.rect(0, 0, W, H, 0)
        pyxel.dither(1.0)

    def draw_paused(self):
        self.draw_world()
        self.dim()
        big_text(W / 2 - text_w("PAUSED", 3) / 2, 24, "PAUSED", 7, 3, 1)
        y = 64
        for w in self.weapons:
            icons.draw(w.id, 70, y + 3)
            shadow_text(80, y, f"{w.spec['name']}  Lv {w.level}", 7)
            y += 11
        y = 64
        for pid, lv in self.passives.items():
            icons.draw(pid, 180, y + 3)
            shadow_text(190, y, f"{data.PASSIVES[pid]['name']}  Lv {lv}", 7)
            y += 11
        ps = self.pstats
        stats = (f"HP {int(self.p.hp)}/{int(ps['maxhp'])}  Might {ps['might'] * 100:.0f}%  "
                 f"Area {ps['area'] * 100:.0f}%  CD {ps['cooldown'] * 100:.0f}%")
        shadow_text(W / 2 - text_w(stats) / 2, 150, stats, 13)
        stats = (f"Armor {ps['armor']}  Speed {ps['speed'] * 100:.0f}%  Amount +{ps['amount']}  "
                 f"Luck {ps['luck'] * 100:.0f}%  Magnet {ps['magnet']:.0f}")
        shadow_text(W / 2 - text_w(stats) / 2, 160, stats, 13)
        s = "ENTER/ESC resume     Q quit to title"
        shadow_text(W / 2 - text_w(s) / 2, 200, s, 10)

    def draw_levelup(self):
        self.draw_world()
        self.dim(0.5)
        pw, ph = 220, 36 + len(self.choices) * 40
        px, py = W / 2 - pw / 2, H / 2 - ph / 2
        pyxel.rect(px, py, pw, ph, 1)
        pyxel.rectb(px, py, pw, ph, 10)
        pyxel.rectb(px + 1, py + 1, pw - 2, ph - 2, 9)
        s = "LEVEL UP!"
        big_text(W / 2 - text_w(s, 2) / 2, py + 8, s, 10, 2, 0)
        for k, opt in enumerate(self.choices):
            y = py + 30 + k * 40
            sel = k == self.sel
            pyxel.rect(px + 6, y, pw - 12, 36, 5 if sel else 0)
            pyxel.rectb(px + 6, y, pw - 12, 36, 10 if sel else 13)
            key = opt[1]
            pyxel.rect(px + 10, y + 4, 20, 20, 1)
            icons.draw(key, px + 20, y + 14, 2)
            name, tag, desc = self.option_text(opt)
            shadow_text(px + 36, y + 4, name, 7)
            if tag:
                shadow_text(px + pw - 12 - text_w(tag) - 2, y + 4, tag, 10 if tag == "New!" else 11)
            for j, line in enumerate(wrap(desc, 42)[:2]):
                shadow_text(px + 36, y + 14 + j * 8, line, 13 if not sel else 7)
            if sel and self.frame // 8 % 2:
                pyxel.tri(px, y + 14, px + 4, y + 18, px, y + 22, 10)
        if self.menu_delay == 0:
            s = "UP/DOWN + ENTER (or 1-4)"
            shadow_text(W / 2 - text_w(s) / 2, py + ph + 4, s, 13)

    def draw_chest(self):
        self.draw_world()
        self.dim(0.7)
        c = self.chest
        t = c["t"]
        cx, cy = W / 2, H / 2 + 10
        # light rays
        if t < c["reveal"] + 200:
            for k in range(12):
                a = k * math.tau / 12 + t * 0.02
                pyxel.line(cx, cy, cx + math.cos(a) * 200, cy + math.sin(a) * 200,
                           10 if k % 2 else 9)
        for co in c["coins"]:
            icons.draw("coin", co[0], co[1])
        bob = 0 if t >= c["reveal"] else math.sin(t * 0.8) * 2
        sprites.draw("chest", cx, cy + bob, scale=3)
        if t < c["reveal"]:
            # slot-machine roll of item icons
            k = icons.KEYS[(t // 2) % 35]
            pyxel.rect(cx - 12, cy - 52, 24, 24, 1)
            pyxel.rectb(cx - 12, cy - 52, 24, 24, 10)
            icons.draw(k, cx, cy - 40, 2)
            return
        n = len(c["items"])
        pw, ph = 200, 30 + n * 16
        px, py = W / 2 - pw / 2, 20
        pyxel.rect(px, py, pw, ph, 1)
        pyxel.rectb(px, py, pw, ph, 10)
        s = "TREASURE!"
        big_text(W / 2 - text_w(s, 2) / 2, py + 4, s, 10, 2, 0)
        for k, (t_, i) in enumerate(c["items"]):
            y = py + 24 + k * 16
            icons.draw(i, px + 16, y + 4)
            if t_ == "evo":
                name, col, tag = data.WEAPONS[i]["name"], 10, "EVOLVED!"
            elif t_ == "w":
                name, col, tag = data.WEAPONS[i]["name"], 7, f"Lv {self.weapon(i).level}"
            elif t_ == "p":
                name, col, tag = data.PASSIVES[i]["name"], 7, f"Lv {self.passives[i]}"
            else:
                name, col, tag = "Gold +25", 10, ""
            shadow_text(px + 28, y + 2, name, col)
            shadow_text(px + pw - 10 - text_w(tag), y + 2, tag, 11 if t_ != "evo" else 8)
        s = f"+{c['gold']} gold"
        shadow_text(W / 2 - text_w(s) / 2, py + ph + 4, s, 10)
        if t > c["reveal"] + 10 and self.frame // 10 % 2:
            s = "PRESS ENTER"
            shadow_text(W / 2 - text_w(s) / 2, H - 20, s, 7)

    def draw_over(self):
        self.draw_world()
        self.dim(0.5)
        pyxel.rect(30, 8, W - 60, H - 16, 0)
        pyxel.rectb(30, 8, W - 60, H - 16, 5)
        cleared = self.result["cleared"]
        s = "STAGE CLEAR" if cleared else "GAME OVER"
        big_text(W / 2 - text_w(s, 3) / 2, 14, s, 10 if cleared else 8, 3, 0)
        if cleared:
            s = "You survived until the Reaper came."
            shadow_text(W / 2 - text_w(s) / 2, 44, s, 13)
        rows = [("Survived", mmss(self.t)), ("Level", str(self.level)),
                ("Enemies defeated", str(self.kills)), ("Gold earned", str(self.gold))]
        for k, (a, b) in enumerate(rows):
            y = 58 + k * 10
            shadow_text(80, y, a, 13)
            shadow_text(W - 80 - text_w(b), y, b, 7)
        y = 106
        pyxel.line(40, y, W - 40, y, 5)
        shadow_text(60, y + 4, "WEAPON", 13)
        shadow_text(180, y + 4, "LV", 13)
        shadow_text(210, y + 4, "DAMAGE", 13)
        shadow_text(252, y + 4, "KILLS", 13)
        for k, w in enumerate(self.weapons):
            yy = y + 16 + k * 12
            icons.draw(w.id, 50, yy + 3)
            shadow_text(60, yy, w.spec["name"], 7)
            shadow_text(180, yy, str(w.level), 7)
            shadow_text(210, yy, str(int(w.dmg_done)), 7)
            shadow_text(252, yy, str(w.kills), 7)
        if self.menu_delay == 0 and self.frame // 15 % 2:
            s = "PRESS ENTER"
            shadow_text(W / 2 - text_w(s) / 2, H - 16, s, 10)


if __name__ == "__main__":
    App()
