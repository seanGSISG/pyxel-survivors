"""Pyxel Survivors: a Vampire Survivors clone built from the VS wiki's data.

Move with arrows / WASD / left stick; weapons fire on their own.
Survive 30 minutes on one of five stages until the Reaper comes.

    uv run --with pyxel python main.py          # real sprites if wiki/atlas exists
    uv run --with pyxel python main.py --pixel  # force the generated pixel art
"""

import math
import random
import sys

import pyxel

import art
import data
import icons
import sprites
import weapons
from weapons import draw_proj
from world import FPS, LIGHT_KIND, MIN, World

W, H = 480, 270
TERRAIN = {
    "mad_forest": [0x1E3D22, 0x26502A, 0x33662F, 0x173019, 0x4A7A3A],
    "inlaid_library": [0x3B2518, 0x4D3221, 0x6B1E24, 0x24150D, 0x8A6A3A],
    "dairy_plant": [0x3D6B2A, 0x4D7F35, 0x8A6F45, 0x2C4F1E, 0xC9B77A],
    "gallo_tower": [0x3A3F52, 0x454B61, 0x2A2D3A, 0x1C1E28, 0x6B7390],
    "cappella_magna": [0x2A1A22, 0x5A3A44, 0x7A1420, 0x140B10, 0xB08A4A],
}
# Base-palette approximations of each stage's terrain, for the stage-select swatches.
SWATCH = {"mad_forest": [3, 11, 4, 1], "inlaid_library": [4, 9, 8, 0],
          "dairy_plant": [3, 11, 9, 1], "gallo_tower": [5, 13, 1, 0],
          "cappella_magna": [2, 14, 8, 0]}
T0, T1, T2, T3, T4 = 16, 17, 18, 19, 20  # terrain palette slots (T3 = shadows)

UP = (pyxel.KEY_UP, pyxel.KEY_W, pyxel.GAMEPAD1_BUTTON_DPAD_UP)
DOWN = (pyxel.KEY_DOWN, pyxel.KEY_S, pyxel.GAMEPAD1_BUTTON_DPAD_DOWN)
LEFT = (pyxel.KEY_LEFT, pyxel.KEY_A, pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
RIGHT = (pyxel.KEY_RIGHT, pyxel.KEY_D, pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
OK = (pyxel.KEY_RETURN, pyxel.KEY_SPACE, pyxel.KEY_Z, pyxel.GAMEPAD1_BUTTON_A)
BACK = (pyxel.KEY_ESCAPE, pyxel.KEY_X, pyxel.GAMEPAD1_BUTTON_B)
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


def ascii_text(s):
    """The built-in font is ASCII only (Carréllo, Tirajisú...)."""
    return s if s.isascii() else s.translate(str.maketrans("éèàùúíóáñ’", "eeauuioan'"))


def shadow_text(x, y, s, col, sh=0):
    s = ascii_text(s)
    pyxel.text(x + 1, y + 1, s, sh)
    pyxel.text(x, y, s, col)


_GLYPHS = {}


def _glyph_pixels(s):
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
    px = _glyph_pixels(ascii_text(s))
    x, y = int(x), int(y)
    if sh is not None:
        for i, j in px:
            pyxel.rect(x + i * scale + scale // 2 + 1, y + j * scale + scale // 2 + 1,
                       scale, scale, sh)
    for i, j in px:
        pyxel.rect(x + i * scale, y + j * scale, scale, scale, col)


def text_w(s, scale=1):
    return len(s) * 4 * scale


def center_text(y, s, col, scale=1):
    if scale == 1:
        shadow_text(W / 2 - text_w(s) / 2, y, s, col)
    else:
        big_text(W / 2 - text_w(s, scale) / 2, y, s, col, scale)


def panel(x, y, w, h, border=10, fill=1):
    pyxel.rect(x, y, w, h, fill)
    pyxel.rectb(x, y, w, h, border)
    pyxel.rectb(x + 1, y + 1, w - 2, h - 2, 0)


# --------------------------------------------------------------------- app


class App(World):
    def __init__(self, config=None):
        """config (tests): char, stage, arcanas, minute, god, weapons {id: lvl},
        passives {id: lvl}, level, autopilot, chest, art ("pixel"/"wiki")."""
        self.config = config or {}
        pyxel.init(W, H, title="Pyxel Survivors", fps=FPS, quit_key=pyxel.KEY_NONE)
        pyxel.colors.extend(TERRAIN["mad_forest"])
        sprites.load()
        icons.load()
        self.art_mode = art.init(self.config.get("art", "wiki"))
        self.setup_audio()
        self.frame = 0
        self.sel = self.stage_sel = self.arc_sel = 0
        self.chosen_char = data.CHARACTERS[0]["id"]
        self.state = "title"
        self.title_bats = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.6, 1.6)]
                           for _ in range(16)]
        if "char" in self.config:
            ch = self.config["char"]
            cid = data.CHARACTERS[ch]["id"] if isinstance(ch, int) else ch
            self.start_run(cid, self.config.get("stage", "mad_forest"),
                           self.config.get("arcanas", []))
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------- audio

    def setup_audio(self):
        s = pyxel.sounds
        s[0].set("c3e3g3", "p", "4", "n", 2)
        s[1].set("f1c1", "n", "3", "f", 2)
        s[2].set("c3e3g3c4e4g4c4", "s", "5", "n", 4)
        s[3].set("a1f1d1", "n", "6", "f", 4)
        s[4].set("c3g3c4e4g4c4e4g4c4", "s", "5", "n", 5)
        s[5].set("a2e2c2", "n", "3", "f", 2)
        s[6].set("a3e3", "p", "2", "f", 2)
        s[7].set("c4g3c3g2c2", "n", "5", "f", 2)
        s[8].set("e2c2a1", "n", "3", "f", 4)
        s[9].set("c2g1", "n", "3", "f", 3)
        s[10].set("c4c4g3g3c3c3", "n", "6", "f", 6)
        s[11].set("b3e4", "p", "4", "n", 3)
        s[12].set("c3", "s", "3", "n", 3)
        s[13].set("c3g3", "s", "4", "n", 4)
        s[14].set("g2f2e2d2c2b1a1", "t", "5", "n", 10)
        s[15].set("a2a2r a2a2", "s", "5", "n", 6)
        s[16].set("c2c3", "t", "4", "n", 3)
        s[17].set("c1c1c1", "n", "6", "f", 8)
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

    SFX = {
        "gem": (0, 2, 2), "hit": (1, 2, 3), "level": (2, 3, 0), "hurt": (3, 3, 4),
        "chest": (4, 3, 0), "whip": (5, 2, 4), "shot": (6, 2, 4), "zap": (7, 3, 4),
        "splash": (8, 2, 6), "pop": (9, 2, 3), "rosary": (10, 3, 0), "coin": (11, 2, 2),
        "move": (12, 3, 0), "ok": (13, 3, 0), "over": (14, 3, 0), "boss": (15, 3, 0),
        "chicken": (16, 3, 0), "freeze": (17, 3, 0),
    }

    def sfx(self, name):
        snd, ch, gap = self.SFX.get(name, self.SFX["hit"])
        if self.frame - self.sfx_t.get(ch, -99) < gap:
            return
        self.sfx_t[ch] = self.frame
        pyxel.play(ch, snd)

    def sfx_fire(self, kind):
        self.sfx("whip" if kind in ("whip", "tear") else "shot")

    # ------------------------------------------------------------- flow

    def start_run(self, char_id, stage_id, arcana_ids):
        pyxel.colors[16:21] = TERRAIN[stage_id]
        self.new_game(char_id, stage_id, arcana_ids)
        self.state = "play"
        pyxel.playm(0, loop=True)

    def update(self):
        self.frame += 1
        getattr(self, "update_" + self.state)()

    def update_title(self):
        for b in self.title_bats:
            b[0] += b[2]
            b[1] += math.sin(self.frame * 0.05 + b[2] * 10) * 0.5
            if b[0] > W + 20:
                b[0], b[1] = -20, random.uniform(0, H)
        if pressed(OK):
            self.sfx("ok")
            self.state = "select"

    def update_select(self):
        n = len(data.CHARACTERS)
        cols = 8
        for keys, d in ((LEFT, -1), (RIGHT, 1), (UP, -cols), (DOWN, cols)):
            if pressed_rep(keys):
                self.sel = (self.sel + d) % n
                self.sfx("move")
        if pressed(OK):
            self.sfx("ok")
            self.chosen_char = data.CHARACTERS[self.sel]["id"]
            self.state = "stage"
        elif pressed(BACK):
            self.state = "title"

    def update_stage(self):
        n = len(data.STAGE_ORDER)
        if pressed_rep(LEFT):
            self.stage_sel = (self.stage_sel - 1) % n
            self.sfx("move")
        if pressed_rep(RIGHT):
            self.stage_sel = (self.stage_sel + 1) % n
            self.sfx("move")
        if pressed(OK):
            self.sfx("ok")
            self.state = "arcana"
        elif pressed(BACK):
            self.state = "select"

    ARC_COLS = 12

    def arcana_list(self):
        return [None] + sorted(data.ARCANAS)  # None = no Arcana

    def update_arcana(self):
        lst = self.arcana_list()
        n = len(lst)
        for keys, d in ((LEFT, -1), (RIGHT, 1), (UP, -self.ARC_COLS), (DOWN, self.ARC_COLS)):
            if pressed_rep(keys):
                self.arc_sel = (self.arc_sel + d) % n
                self.sfx("move")
        if pressed(OK):
            self.sfx("ok")
            aid = lst[self.arc_sel]
            self.start_run(self.chosen_char, data.STAGE_ORDER[self.stage_sel],
                           [aid] if aid else [])
        elif pressed(BACK):
            self.state = "stage"

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
            self.sel = self.autopilot_choice()
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

    def open_levelup(self):
        self.choices = self.build_choices()
        self.sel = 0
        self.menu_delay = 8
        self.state = "levelup"
        self.flash_t = 4
        self.sfx("level")

    def pick_choice(self):
        self.sfx("ok")
        self.apply_choice(self.choices[self.sel])
        self.pending -= 1
        if self.pending > 0:
            self.choices = self.build_choices()
            self.sel = 0
            self.menu_delay = 4
        else:
            self.state = "play"
            self.p_invuln(15)
            self.choices = []

    def update_chest(self):
        c = self.chest
        c["t"] += 1
        if c["t"] % 3 == 0 and c["t"] < c["reveal"]:
            ang = random.uniform(-2.6, -0.5)
            spd = random.uniform(1.5, 4)
            c["coins"].append([W / 2, H / 2 + 20, math.cos(ang) * spd, math.sin(ang) * spd])
        for co in c["coins"]:
            co[0] += co[2]
            co[1] += co[3]
            co[3] += 0.15
        auto = self.config.get("autopilot")
        if c["t"] > c["reveal"] + 10 and (pressed(OK) or auto):
            self.sfx("ok")
            self.chest = None
            self.state = "play"
            self.p_invuln(15)
        elif 15 < c["t"] < c["reveal"] and pressed(OK):
            c["t"] = c["reveal"]

    def update_arcana_chest(self):
        a = self.arcana_pick
        if self.menu_delay > 0:
            self.menu_delay -= 1
            return
        n = len(a["options"])
        if n == 0 or self.config.get("autopilot"):
            if n:
                self.arc.add(a["options"][0])
                self.recompute_stats()
            self.state = "play"
            return
        if pressed_rep(LEFT):
            a["sel"] = (a["sel"] - 1) % n
            self.sfx("move")
        if pressed_rep(RIGHT):
            a["sel"] = (a["sel"] + 1) % n
            self.sfx("move")
        if pressed(OK):
            self.sfx("ok")
            self.arc.add(a["options"][a["sel"]])
            self.recompute_stats()
            self.arcana_pick = None
            self.state = "play"
            self.p_invuln(15)

    def update_play(self):
        if pressed(PAUSE):
            self.state = "paused"
            pyxel.stop()
            return
        dx = (1 if held(RIGHT) else 0) - (1 if held(LEFT) else 0)
        dy = (1 if held(DOWN) else 0) - (1 if held(UP) else 0)
        ax = pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTX) / 32768
        ay = pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTY) / 32768
        if abs(ax) > 0.25 or abs(ay) > 0.25:
            dx, dy = ax, ay
        if self.config.get("autopilot"):
            dx, dy = self.autopilot()
        self.step(dx, dy)
        if self.state != "play":  # a chest opened during the step
            return
        if self.p.hp <= 0:
            self.end_run()
        elif self.pending > 0:
            self.open_levelup()

    def end_run(self):
        cleared = self.t >= self.stage["minutes"] * MIN
        self.result = dict(cleared=cleared)
        if cleared:
            self.gain_gold(500)
        self.state = "over"
        self.menu_delay = 30
        pyxel.stop()
        self.sfx("over")

    # ============================================================= DRAW

    def draw(self):
        getattr(self, "draw_" + self.state)()

    def draw_title(self):
        pyxel.cls(0)
        for i in range(0, W, 16):
            for j in range(0, H, 16):
                h = hash2(i, j)
                if h % 7 == 0:
                    pyxel.pset(i + h % 13, j + (h >> 4) % 13, 1)
        pyxel.circ(W - 70, 56, 30, 15)
        pyxel.circ(W - 58, 48, 28, 0)
        for b in self.title_bats:
            art.draw_enemy("pipeestrello_1", b[0], b[1], self.frame + int(b[2] * 10), False)
        center_text(56, "PYXEL", 8, 5)
        center_text(100, "SURVIVORS", 7, 4)
        center_text(136, "a Vampire Survivors tribute built from the VS wiki", 13)
        art.draw_char("antonio_belpaese", W / 2, 176, True, self.frame, False)
        if self.frame // 15 % 2:
            center_text(206, "PRESS ENTER", 10)
        center_text(232, "MOVE: ARROWS / WASD / STICK    WEAPONS FIRE ON THEIR OWN", 13)
        center_text(242, f"PAUSE: ESC / P    SURVIVE 30 MINUTES    ART: {self.art_mode.upper()}", 5)

    def draw_select(self):
        pyxel.cls(0)
        center_text(8, "CHOOSE YOUR CHARACTER", 10, 2)
        cols, cw, chh = 8, 56, 50
        x0 = W / 2 - cols * cw / 2
        for i, ch in enumerate(data.CHARACTERS):
            x = x0 + (i % cols) * cw
            y = 26 + (i // cols) * chh
            sel = i == self.sel
            pyxel.rect(x + 1, y, cw - 2, chh - 2, 1 if sel else 0)
            pyxel.rectb(x + 1, y, cw - 2, chh - 2, 10 if sel else 5)
            art.draw_char(ch["id"], x + cw / 2, y + 20, sel, self.frame, False)
            name = ch["alias"][:13]
            shadow_text(x + cw / 2 - text_w(name) / 2, y + chh - 10, name, 7 if sel else 13)
        ch = data.CHARACTERS[self.sel]
        y = 26 + 3 * chh + 4
        panel(20, y, W - 40, H - y - 18, 5, 0)
        if ch["weapons"]:
            art.icon(ch["weapons"][0], 36, y + 14)
        shadow_text(52, y + 6, ch["name"], 10)
        wn = ", ".join(data.WEAPONS[w]["name"] for w in ch["weapons"] if w in data.WEAPONS)
        shadow_text(52, y + 16, f"{wn}   Max HP {ch['hp']}", 7)
        for k, line in enumerate(wrap(ch["desc"], 100)[:2]):
            shadow_text(32, y + 30 + k * 9, line, 11)
        center_text(H - 12, "ARROWS choose   ENTER next   ESC back", 13)

    def draw_stage(self):
        pyxel.cls(0)
        center_text(8, "CHOOSE A STAGE", 10, 2)
        n = len(data.STAGE_ORDER)
        cw = 88
        x0 = W / 2 - (n * cw + (n - 1) * 4) / 2
        for i, sid in enumerate(data.STAGE_ORDER):
            st = data.STAGES[sid]
            x = x0 + i * (cw + 4)
            y = 30
            sel = i == self.stage_sel
            pyxel.rect(x, y, cw, 150, 1 if sel else 0)
            pyxel.rectb(x, y, cw, 150, 10 if sel else 5)
            for k, c in enumerate(SWATCH[sid]):
                pyxel.rect(x + 6 + k * 19, y + 6, 19, 8, c)
            w0 = st["waves"][0]
            if w0["enemies"]:
                art.draw_enemy(w0["enemies"][0], x + cw / 2 - 18, y + 44, self.frame, False)
            boss = next((b for wv in st["waves"] for b in wv["bosses"]), None)
            if boss:
                art.draw_enemy(boss, x + cw / 2 + 18, y + 44, self.frame, True)
            name = st["name"]
            shadow_text(x + cw / 2 - text_w(name) / 2, y + 72, name, 10 if sel else 7)
            lay = {"open": "Open field", "horizontal": "Corridor (L-R)",
                   "vertical": "Tower (up-down)"}[st["layout"]]
            shadow_text(x + cw / 2 - text_w(lay) / 2, y + 82, lay, 13)
            shadow_text(x + cw / 2 - text_w("30:00") / 2, y + 92, "30:00", 13)
            for k, line in enumerate(wrap(st["desc"], 20)[:5]):
                shadow_text(x + 5, y + 104 + k * 8, line, 6 if sel else 5)
        st = data.STAGES[data.STAGE_ORDER[self.stage_sel]]
        n_en = len({e for w in st["waves"] for e in w["enemies"] + w["bosses"]})
        n_ev = len({e["name"] for w in st["waves"] for e in w["events"]})
        center_text(192, f"{n_en} enemy types   {n_ev} map events   "
                         f"player x{st['player_speed']:g}  enemies x{st['enemy_speed']:g}", 11)
        center_text(H - 12, "LEFT/RIGHT choose   ENTER next   ESC back", 13)

    def draw_card(self, aid, x, y, big=False):
        """Arcana card: real art (atlas) or a generated card."""
        if aid and big and art.draw(f"arcana:{aid}", x, y):
            return
        if aid and not big and art.draw(f"arcana_icon:{aid}", x, y):
            return
        w, h = (64, 96) if big else (14, 20)
        pyxel.rect(x - w / 2, y - h / 2, w, h, 1 if aid else 0)
        pyxel.rectb(x - w / 2, y - h / 2, w, h, 10 if aid else 5)
        if aid:
            num = data.ARCANAS[aid]["name"].split("(")[-1].rstrip(")")
            s = num if big else num[:3]
            shadow_text(x - text_w(s) / 2, y - (30 if big else 3), s, 10)
            if big:
                pyxel.circ(x, y + 6, 14, 2)
                pyxel.circb(x, y + 6, 14, 10)
        else:
            pyxel.line(x - 4, y - 4, x + 4, y + 4, 8)
            pyxel.line(x + 4, y - 4, x - 4, y + 4, 8)

    def draw_arcana(self):
        pyxel.cls(0)
        center_text(8, "CHOOSE AN ARCANA", 10, 2)
        lst = self.arcana_list()
        cols = self.ARC_COLS
        x0 = 150
        for i, aid in enumerate(lst):
            x = x0 + (i % cols) * 26
            y = 44 + (i // cols) * 30
            if i == self.arc_sel:
                pyxel.rectb(x - 11, y - 13, 22, 26, 10)
            self.draw_card(aid, x, y)
        aid = lst[self.arc_sel]
        self.draw_card(aid, 70, 110, big=True)
        if aid:
            a = data.ARCANAS[aid]
            shadow_text(140, 120, a["name"], 10)
            for k, line in enumerate(wrap(a["desc"], 80)[:5]):
                shadow_text(140, 132 + k * 9, line, 7)
            aff = [data.WEAPONS[w]["name"] for w in a["affects"] if w in data.WEAPONS]
            if aff:
                shadow_text(140, 184, "Affects:", 13)
                for k, line in enumerate(wrap(", ".join(aff), 80)[:3]):
                    shadow_text(140, 194 + k * 9, line, 11)
        else:
            shadow_text(140, 120, "No Arcana", 10)
            shadow_text(140, 132, "Play the classic way.", 7)
        center_text(H - 12, "ARROWS choose   ENTER start   ESC back", 13)

    # --- world

    def draw_world(self):
        sx = sy = 0
        if self.shake:
            sx, sy = random.randint(-2, 2), random.randint(-2, 2)
        cx, cy = int(self.cam_x) + sx, int(self.cam_y) + sy
        pyxel.cls(T0)
        pyxel.camera(cx, cy)
        getattr(self, "terrain_" + self.stage["id"])(cx, cy)
        ground = getattr(weapons, "GROUND_KINDS", {"water", "borra"})
        for pr in self.projs:
            if pr.kind in ground:
                draw_proj(pr, self)
        for hz in self.hazards:
            pyxel.circb(hz.x, hz.y, hz.r * hz.t / hz.fuse, 8 if self.frame % 4 < 2 else 10)
            pyxel.circb(hz.x, hz.y, hz.r, 2)
        for it in self.pickups:
            self.draw_pickup(it)
        p = self.p
        vis = [e for e in self.enemies
               if cx - 60 < e.x < cx + W + 60 and cy - 60 < e.y < cy + H + 60]
        vis.sort(key=lambda e: e.y)
        drawn_player = False
        for e in vis:
            if not drawn_player and e.y > p.y:
                self.draw_player()
                drawn_player = True
            self.draw_enemy(e)
        if not drawn_player:
            self.draw_player()
        fx = getattr(weapons, "draw_weapon_fx", None) or weapons.draw_aura
        for w in self.weapons:
            fx(w, self)
        for pr in self.projs:
            if pr.kind not in ground:
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
            pyxel.dither(0.12)
            pyxel.rect(0, 0, W, H, 12)
            pyxel.dither(1.0)
        self.draw_hud()

    def terrain_mad_forest(self, cx, cy):
        for gx in range(cx // 96 - 1, (cx + W) // 96 + 2):
            for gy in range(cy // 96 - 1, (cy + H) // 96 + 2):
                h = hash2(gx, gy)
                if h % 3 == 0:
                    pyxel.elli(gx * 96 + h % 50, gy * 96 + (h >> 6) % 50,
                               60 + (h >> 10) % 60, 30 + (h >> 14) % 30, T1)
        for gx in range(cx // 24 - 1, (cx + W) // 24 + 2):
            for gy in range(cy // 24 - 1, (cy + H) // 24 + 2):
                h = hash2(gx + 7919, gy - 104729)
                x, y = gx * 24 + h % 18, gy * 24 + (h >> 5) % 18
                r = h % 97
                if r < 12:
                    pyxel.line(x, y, x - 1, y - 4, T4)
                    pyxel.line(x + 1, y, x + 1, y - 5, T2)
                    pyxel.line(x + 2, y, x + 3, y - 4, T4)
                elif r < 14:
                    c = (7, 10, 14, 6)[(h >> 9) % 4]
                    for ddx, ddy in ((0, 0), (1, 1), (-1, 1), (0, 2)):
                        pyxel.pset(x + ddx, y + ddy, c)
                    pyxel.pset(x, y + 1, 10 if c != 10 else 9)
                elif r < 15:
                    pyxel.elli(x, y, 7, 4, 13)
                    pyxel.line(x + 1, y, x + 4, y, 7)
                elif r < 17:
                    pyxel.circ(x, y, 7, T3)
                    pyxel.circ(x + 6, y + 1, 6, T3)
                    pyxel.pset(x - 1, y - 3, T1)

    def terrain_inlaid_library(self, cx, cy):
        band = H * 0.55 + 24
        for gy in range(cy // 12 - 1, (cy + H) // 12 + 2):
            y = gy * 12
            pyxel.line(cx, y, cx + W, y, T3)
            off = (gy * 37) % 48
            for gx in range((cx - off) // 48 - 1, (cx + W) // 48 + 2):
                x = gx * 48 + off
                pyxel.line(x, y, x, y + 11, T3)
                if hash2(gx, gy) % 4 == 0:
                    pyxel.rect(x + 1, y + 1, 46, 10, T1)
        pyxel.rect(cx, -20, W, 40, T2)  # carpet runner
        pyxel.line(cx, -20, cx + W, -20, T4)
        pyxel.line(cx, 19, cx + W, 19, T4)
        for s in (-1, 1):  # bookshelf walls
            y0 = band if s > 0 else -band - 60
            pyxel.rect(cx, y0, W, 60, T3)
            for gx in range(cx // 10 - 1, (cx + W) // 10 + 2):
                h = hash2(gx, s)
                pyxel.rect(gx * 10 + 1, y0 + 6 + h % 8, 8, 44 - h % 8, (4, 2, 5, 3, 9, 13)[h % 6])
            pyxel.rect(cx, y0 + (0 if s > 0 else 56), W, 4, T4)

    def terrain_dairy_plant(self, cx, cy):
        for gx in range(cx // 160 - 1, (cx + W) // 160 + 2):
            pyxel.rect(gx * 160, cy, 18, H, T2)
            for gy in range(cy // 40 - 1, (cy + H) // 40 + 2):
                pyxel.rect(gx * 160 + 24, gy * 40, 3, 26, T4)
        for gy in range(cy // 140 - 1, (cy + H) // 140 + 2):
            pyxel.rect(cx, gy * 140, W, 14, T2)
        for gx in range(cx // 24 - 1, (cx + W) // 24 + 2):
            for gy in range(cy // 24 - 1, (cy + H) // 24 + 2):
                h = hash2(gx, gy)
                x, y = gx * 24 + h % 16, gy * 24 + (h >> 5) % 16
                if h % 11 == 0:
                    pyxel.line(x, y, x, y - 4, T1)
                    pyxel.line(x + 2, y, x + 3, y - 3, T1)
                elif h % 37 == 0:
                    pyxel.elli(x, y, 12, 8, T4)
                    pyxel.line(x + 2, y + 3, x + 9, y + 3, 9)

    def terrain_gallo_tower(self, cx, cy):
        for gx in range(cx // 32 - 1, (cx + W) // 32 + 2):
            for gy in range(cy // 32 - 1, (cy + H) // 32 + 2):
                pyxel.rect(gx * 32, gy * 32, 32, 32, T0 if (gx + gy) % 2 else T1)
                pyxel.rectb(gx * 32, gy * 32, 32, 32, T2)
                if hash2(gx, gy) % 9 == 0:
                    pyxel.line(gx * 32 + 6, gy * 32 + 8, gx * 32 + 14, gy * 32 + 16, T2)
        edge = W * 0.3 + 30
        for s in (-1, 1):  # brick walls with windows
            x0 = edge if s > 0 else -edge - 80
            pyxel.rect(x0, cy, 80, H, T3)
            for gy in range(cy // 16 - 1, (cy + H) // 16 + 2):
                off = 8 if gy % 2 else 0
                for k in range(6):
                    pyxel.rectb(x0 + off + k * 16 - 8, gy * 16, 16, 16, T2)
                if gy % 9 == 0:
                    pyxel.rect(x0 + 30, gy * 16 + 2, 16, 26, 1)
                    pyxel.rect(x0 + 32, gy * 16 + 4, 12, 22, 12)
            pyxel.rect(x0 + (0 if s > 0 else 76), cy, 4, H, T4)

    def terrain_cappella_magna(self, cx, cy):
        for gx in range(cx // 24 - 1, (cx + W) // 24 + 2):
            for gy in range(cy // 24 - 1, (cy + H) // 24 + 2):
                pyxel.rect(gx * 24, gy * 24, 24, 24, T0 if (gx + gy) % 2 else T1)
        for gx in range(cx // 240 - 1, (cx + W) // 240 + 2):
            pyxel.rect(gx * 240, cy, 28, H, T2)
            pyxel.line(gx * 240, cy, gx * 240, cy + H, T4)
            pyxel.line(gx * 240 + 27, cy, gx * 240 + 27, cy + H, T4)
        for gx in range(cx // 120 - 1, (cx + W) // 120 + 2):
            for gy in range(cy // 120 - 1, (cy + H) // 120 + 2):
                if hash2(gx, gy) % 3 == 0:
                    x, y = gx * 120 + 60, gy * 120 + 60
                    pyxel.rect(x - 1, y - 10, 3, 12, T4)
                    pyxel.line(x - 6, y - 10, x + 6, y - 10, T4)
                    for k in (-6, 0, 6):
                        pyxel.pset(x + k, y - 12 - (self.frame // 4 + k) % 2, 10)

    def draw_player(self):
        p = self.p
        w, h = art.char_size(self.char["id"])
        pyxel.elli(p.x - 9, p.y + 9, 18, 5, T3)
        if not (p.inv and self.frame % 4 < 2 and p.hurt):
            art.draw_char(self.char["id"], p.x, p.y - h / 2 + 12, p.moving, p.walk,
                          p.face_x < 0, hurt=bool(p.hurt))
        mx = self.pstats["maxhp"]
        pyxel.rect(p.x - 12, p.y + 14, 24, 3, 1)
        pyxel.rect(p.x - 12, p.y + 14, max(0, 24 * p.hp / mx), 3, 8)

    def draw_enemy(self, e):
        if e.prop:
            if not art.light(LIGHT_KIND[self.stage["id"]], e.x, e.y - 8, self.frame, bool(e.flash)):
                sprites.draw("brazier", e.x, e.y - 8, scale=1.5)
                fl = self.frame // 3 % 3
                pyxel.circ(e.x, e.y - 18, 3 + (fl == 1), 9 if not e.flash else 7)
                pyxel.pset(e.x, e.y - 22 - fl, 10)
            return
        pyxel.elli(e.x - e.r, e.y + e.r * 0.6, e.r * 2, e.r * 0.7, T3)
        art.draw_enemy(e.eid, e.x, e.y - e.h * 0.35, self.frame + e.phase, e.flip,
                       e.scale, flash=bool(e.flash),
                       frozen=bool(e.frozen or (self.freeze_t and not e.reaper)))
        if e.boss or e.hunter:
            f = self.frame // 4 % 2
            top = e.y - e.h * 0.85 - 6 - f
            pyxel.tri(e.x - 4, top - 5, e.x + 4, top - 5, e.x, top, 10 if e.boss else 8)

    def draw_pickup(self, it):
        x, y, k = it.x, it.y, it.kind
        if k == "gem":
            v = it.value
            key = "gem_red" if (v > 9 or it is self.big_gem) else "gem_green" if v > 2 else "gem"
            if not art.pickup(key, x, y):
                if key == "gem_red":
                    pyxel.pal(12, 8)
                    pyxel.pal(1, 2)
                elif key == "gem_green":
                    pyxel.pal(12, 11)
                    pyxel.pal(1, 3)
                sprites.draw("gem", x, y, scale=1.5 if it is self.big_gem else 1.2)
                pyxel.pal()
            if (it.t // 4) % 16 == 0:
                pyxel.pset(x - 1, y - 3, 7)
        elif k == "chest":
            bob = math.sin(it.t * 0.15) * 1.5
            pyxel.elli(x - 9, y + 5, 18, 5, T3)
            tr = it.treasure or {}
            evo = str(tr.get("evo", "")) == "1"
            arc = str(tr.get("reward1", "")).lower() == "arcana"
            key = "chest_arcana" if arc else "chest_evo" if evo else "chest"
            if not art.pickup(key, x, y - 4 + bob):
                if evo:
                    pyxel.pal(9, 7)
                    pyxel.pal(4, 13)
                sprites.draw("chest", x, y - 4 + bob, scale=1.5)
                pyxel.pal()
            if it.t // 8 % 2:
                pyxel.pset(x + 6, y - 10 + bob, 7)
        elif not art.pickup(k, x, y + math.sin(it.t * 0.12), it.t):
            key = "little_clover" if k == "clover" else k if k in icons.SLOT else "coin"
            icons.draw(key, x, y, 2)

    def draw_offscreen_arrows(self):
        for it in self.pickups:
            if it.kind != "chest":
                continue
            sx, sy = it.x - self.cam_x, it.y - self.cam_y
            if 0 <= sx < W and 0 <= sy < H:
                continue
            ang = math.atan2(sy - H / 2, sx - W / 2)
            ax, ay = min(max(sx, 12), W - 12), min(max(sy, 44), H - 12)
            ca, sa = math.cos(ang), math.sin(ang)
            pyxel.tri(ax + ca * 7, ay + sa * 7, ax - sa * 5, ay + ca * 5,
                      ax + sa * 5, ay - ca * 5, 10)

    def draw_hud(self):
        pyxel.rect(0, 0, W, 9, 1)
        f = min(1, self.xp / self.xp_next)
        pyxel.rect(0, 0, W * f, 9, 12)
        pyxel.rect(0, 0, W * f, 2, 6)
        pyxel.rectb(0, 0, W, 9, 5)
        s = f"LV {self.level}"
        shadow_text(W - text_w(s) - 4, 2, s, 7)
        s = mmss(self.t)
        big_text(W / 2 - text_w(s, 2) / 2, 13, s, 7, 2, 0)
        icons.draw("skull", W - 10, 18, 1)
        s = str(self.kills)
        shadow_text(W - 17 - text_w(s), 16, s, 7)
        if not art.pickup("coin", W - 10, 29):
            icons.draw("coin", W - 10, 29)
        s = str(self.gold)
        shadow_text(W - 17 - text_w(s), 27, s, 10)
        for i in range(6):
            x = 3 + i * 19
            pyxel.rectb(x, 11, 18, 18, 5)
            if i < len(self.weapons):
                art.icon(self.weapons[i].id, x + 9, 20)
            pyxel.rectb(x, 30, 18, 18, 1)
        for i, pid in enumerate(self.passives):
            art.icon(pid, 3 + i * 19 + 9, 39)
        for i, aid in enumerate(self.arc.active):
            self.draw_card(aid, 126 + i * 16, 22)
        if self.revivals:
            shadow_text(4, 51, f"REVIVAL x{self.revivals}", 11)
        if self.nduja_t:
            art.icon("nduja", 12, 64)
        if self.banner_t and self.state == "play":
            s = self.banner
            if self.banner_t > 10 or self.frame % 2:
                big_text(W / 2 - text_w(s, 2) / 2, 70, s, 8 if "REAPER" in s else 10, 2, 0)

    def draw_play(self):
        self.draw_world()

    def dim(self, amt=0.6):
        pyxel.dither(amt)
        pyxel.rect(0, 0, W, H, 0)
        pyxel.dither(1.0)

    def draw_paused(self):
        self.draw_world()
        self.dim()
        panel(60, 16, W - 120, H - 32, 5, 0)
        center_text(24, "PAUSED", 7, 3)
        y = 60
        for w in self.weapons:
            art.icon(w.id, 80, y + 3)
            shadow_text(92, y, f"{w.spec['name']}  Lv {w.level}", 7)
            y += 16
        y = 60
        for pid, lv in self.passives.items():
            art.icon(pid, 250, y + 3)
            shadow_text(262, y, f"{data.PASSIVES[pid]['name']}  Lv {lv}", 7)
            y += 16
        for i, aid in enumerate(self.arc.active):
            self.draw_card(aid, 90 + i * 20, 170)
        ps = self.pstats
        center_text(196, f"HP {int(self.p.hp)}/{int(ps['maxhp'])}  Might {ps['might']:.0%}  "
                         f"Area {ps['area']:.0%}  CD {ps['cooldown']:.0%}  Armor {ps['armor']:g}  "
                         f"Amount +{ps['amount']}", 13)
        center_text(206, f"Speed {ps['speed']:.0%}  Duration {ps['duration']:.0%}  "
                         f"Luck {ps['luck']:.0%}  Growth {ps['growth']:.0%}  "
                         f"Greed {ps['greed']:.0%}  Curse {ps['curse']:.0%}", 13)
        center_text(228, f"{self.stage['name']}  -  {self.char['name']}", 11)
        center_text(242, "ENTER/ESC resume     Q quit to title", 10)

    def draw_levelup(self):
        self.draw_world()
        self.dim(0.5)
        pw, ph = 300, 34 + len(self.choices) * 42
        px, py = W / 2 - pw / 2, H / 2 - ph / 2
        panel(px, py, pw, ph, 10, 1)
        center_text(py + 7, "LEVEL UP!", 10, 2)
        for k, opt in enumerate(self.choices):
            y = py + 28 + k * 42
            sel = k == self.sel
            pyxel.rect(px + 6, y, pw - 12, 38, 5 if sel else 0)
            pyxel.rectb(px + 6, y, pw - 12, 38, 10 if sel else 13)
            pyxel.rect(px + 10, y + 4, 22, 22, 1)
            art.icon(opt[1], px + 21, y + 15)
            name, tag, desc = self.option_text(opt)
            shadow_text(px + 38, y + 4, name, 7)
            if tag:
                shadow_text(px + pw - 14 - text_w(tag), y + 4, tag, 10 if tag == "New!" else 11)
            for j, line in enumerate(wrap(desc, 62)[:2]):
                shadow_text(px + 38, y + 15 + j * 9, line, 7 if sel else 13)
            if sel and self.frame // 8 % 2:
                pyxel.tri(px - 2, y + 14, px + 3, y + 19, px - 2, y + 24, 10)
        if self.menu_delay == 0:
            center_text(py + ph + 4, "UP/DOWN + ENTER (or 1-4)", 13)

    def draw_chest(self):
        self.draw_world()
        self.dim(0.7)
        c = self.chest
        t = c["t"]
        cx, cy = W / 2, H / 2 + 20
        for k in range(12):
            a = k * math.tau / 12 + t * 0.02
            pyxel.line(cx, cy, cx + math.cos(a) * 300, cy + math.sin(a) * 300, 10 if k % 2 else 9)
        for co in c["coins"]:
            if not art.pickup("coin", co[0], co[1]):
                icons.draw("coin", co[0], co[1], 2)
        bob = 0 if t >= c["reveal"] else math.sin(t * 0.8) * 2
        if not art.draw("pickup:chest", cx, cy + bob, scale=3):
            sprites.draw("chest", cx, cy + bob, scale=4)
        if t < c["reveal"]:
            keys = list(data.WEAPONS) + list(data.PASSIVES)
            panel(cx - 16, cy - 76, 32, 32, 10, 1)
            art.icon(keys[(t // 2) % len(keys)], cx, cy - 60)
            return
        n = len(c["items"])
        pw, ph = 260, 30 + n * 18
        px, py = W / 2 - pw / 2, 16
        panel(px, py, pw, ph, 10, 1)
        center_text(py + 5, "TREASURE!", 10, 2)
        for k, (t_, i) in enumerate(c["items"]):
            y = py + 26 + k * 18
            art.icon(i, px + 18, y + 4)
            if t_ == "evo":
                name, col, tag = data.WEAPONS[i]["name"], 10, "EVOLVED!"
            elif t_ == "w":
                w = self.weapon(i)
                name, col, tag = data.WEAPONS[i]["name"], 7, f"Lv {w.level}" if w else ""
            elif t_ == "p":
                name, col, tag = data.PASSIVES[i]["name"], 7, f"Lv {self.passives.get(i, 0)}"
            else:
                name, col, tag = "Gold +25", 10, ""
            shadow_text(px + 32, y + 1, name, col)
            shadow_text(px + pw - 12 - text_w(tag), y + 1, tag, 11 if t_ != "evo" else 8)
        center_text(py + ph + 4, f"+{c['gold']} gold", 10)
        if t > c["reveal"] + 10 and self.frame // 10 % 2:
            center_text(H - 16, "PRESS ENTER", 7)

    def draw_arcana_chest(self):
        self.draw_world()
        self.dim(0.7)
        a = self.arcana_pick
        center_text(20, "ARCANA", 10, 3)
        n = len(a["options"])
        for i, aid in enumerate(a["options"]):
            x = W / 2 + (i - (n - 1) / 2) * 110
            if i == a["sel"]:
                pyxel.rectb(x - 40, 52, 80, 120, 10)
            self.draw_card(aid, x, 112, big=True)
        if n:
            ar = data.ARCANAS[a["options"][a["sel"]]]
            center_text(184, ar["name"], 10)
            for k, line in enumerate(wrap(ar["desc"], 100)[:3]):
                center_text(196 + k * 9, line, 7)
        center_text(H - 14, "LEFT/RIGHT choose   ENTER take", 13)

    def draw_over(self):
        self.draw_world()
        self.dim(0.5)
        panel(40, 8, W - 80, H - 16, 5, 0)
        cleared = self.result["cleared"]
        center_text(16, "STAGE CLEAR" if cleared else "GAME OVER", 10 if cleared else 8, 3)
        if cleared:
            center_text(42, "You survived until the Reaper came.", 13)
        rows = [("Stage", self.stage["name"]), ("Character", self.char["name"]),
                ("Survived", mmss(self.t)), ("Level", str(self.level)),
                ("Enemies defeated", str(self.kills)), ("Gold earned", str(self.gold))]
        for k, (a, b) in enumerate(rows):
            y = 54 + k * 10
            shadow_text(110, y, a, 13)
            shadow_text(W - 110 - text_w(b), y, b, 7)
        y = 120
        pyxel.line(60, y, W - 60, y, 5)
        for label, x in (("WEAPON", 90), ("LV", 260), ("DAMAGE", 300), ("KILLS", 360)):
            shadow_text(x, y + 4, label, 13)
        for k, w in enumerate(self.weapons):
            yy = y + 18 + k * 16
            art.icon(w.id, 78, yy + 3)
            shadow_text(90, yy, w.spec["name"], 7)
            shadow_text(260, yy, str(w.level), 7)
            shadow_text(300, yy, str(int(w.dmg_done)), 7)
            shadow_text(360, yy, str(w.kills), 7)
        if self.menu_delay == 0 and self.frame // 15 % 2:
            center_text(H - 18, "PRESS ENTER", 10)


if __name__ == "__main__":
    App({"art": "pixel"} if "--pixel" in sys.argv else None)
