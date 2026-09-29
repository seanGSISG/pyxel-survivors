"""Weapon lab: a standalone arena for eyeballing weapon behaviours.

A minimal fake Game implements the API weapons.py expects (queries, damage,
freeze, pickups, ...). Enemies stream toward the player, who walks a slow
circle and pauses periodically (so movement weapons fire). Usage:

    LAB_WEAPONS="peachone:8,laurel:7" uv run --with pyxel python tools/weapon_lab.py
    # or from a script: weapon_lab.Lab(["whip:8", "garlic:4"])
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pyxel

import art
import icons
import sprites
from weapons import Weapon, draw_proj, draw_weapon_fx, update_proj

W, H = 480, 270
ENEMY_IDS = ["zombie", "skeleton", "pipeestrello_1", "ghost_1", "mudman_1"]


class P:
    def __init__(self):
        self.x = self.y = 0.0
        self.face_x, self.face_x8, self.face_y8 = 1, 1, 0
        self.moving = False
        self.inv = 0
        self.walk = 0


class E:
    __slots__ = ("x", "y", "r", "hp", "maxhp", "dead", "prop", "boss", "reaper", "frozen",
                 "kb", "spd", "flash", "eid", "kbx", "kby", "kbt", "res_kill")

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = 9
        self.hp = self.maxhp = 60
        self.dead = self.prop = self.boss = self.reaper = False
        self.frozen = self.flash = self.kbt = 0
        self.kbx = self.kby = 0.0
        self.kb = 1.0
        self.spd = 0.9
        self.eid = random.choice(ENEMY_IDS)
        self.res_kill = 0


class Pickup:
    def __init__(self, kind, x, y):
        self.kind, self.x, self.y, self.fly = kind, x, y, False


class Lab:
    W, H = W, H

    def __init__(self, loadout=None, n_enemies=90, move=True, art_prefer="wiki"):
        spec = loadout or os.environ.get("LAB_WEAPONS", "whip:8,magic_wand:8").split(",")
        pyxel.init(W, H, title="weapon lab", fps=30)
        pyxel.colors.extend([0x1E3D22, 0x26502A, 0x33662F, 0x173019, 0x4A7A3A])
        sprites.load()
        icons.load()
        self.art_mode = art.init(art_prefer)
        self.p = P()
        self.pstats = dict(might=1, armor=0, maxhp=100, recovery=0, cooldown=1, area=1, speed=1,
                           duration=1, amount=0, move=1, magnet=30, luck=1, growth=1, greed=1,
                           curse=1, revival=0)
        self.projs, self.enemies, self.pickups, self.floaters = [], [], [], []
        self.gold = self.frame = self.t = self.kills = 0
        self.total_dmg = 0.0
        self.freezes = self.shield_blocks = self.gems_dropped = 0
        self.flash_t = 0
        self.move = move
        self.n_enemies = n_enemies
        self.weapons = []
        for s in spec:
            wid, _, lv = s.strip().partition(":")
            w = Weapon(wid)
            w.level = int(lv or 1)
            self.weapons.append(w)
        self.cam_x, self.cam_y = -W / 2, -H / 2
        self.grid = {}
        for _ in range(12):
            self.pickups.append(Pickup("gem", random.uniform(-200, 200), random.uniform(-110, 110)))
        pyxel.run(self.update, self.draw)

    # ---- game API -----------------------------------------------------------
    def query(self, x, y, r):
        out = []
        for cx in range(int((x - r - 16) // 32), int((x + r + 16) // 32) + 1):
            for cy in range(int((y - r - 16) // 32), int((y + r + 16) // 32) + 1):
                for e in self.grid.get((cx, cy), ()):
                    if not e.dead and (e.x - x) ** 2 + (e.y - y) ** 2 <= (r + e.r) ** 2:
                        out.append(e)
        return out

    def query_rect(self, x0, y0, w, h):
        return [e for e in self.enemies if not e.dead
                and x0 - e.r <= e.x <= x0 + w + e.r and y0 - e.r <= e.y <= y0 + h + e.r]

    def targetable(self):
        return [e for e in self.enemies if not e.dead
                and abs(e.x - self.p.x) < W / 2 and abs(e.y - self.p.y) < H / 2]

    def nearest_enemies(self, x, y, n):
        c = self.targetable()
        c.sort(key=lambda e: (e.x - x) ** 2 + (e.y - y) ** 2)
        return c[:n]

    def random_enemy_near(self, x, y, r=None):
        c = self.targetable()
        if r:
            c = [e for e in c if (e.x - x) ** 2 + (e.y - y) ** 2 < r * r]
        return random.choice(c) if c else None

    def random_enemy_on_screen(self):
        return self.random_enemy_near(self.p.x, self.p.y)

    def damage_enemy(self, e, dmg, w, sx, sy, kb):
        if e.dead:
            return
        e.hp -= dmg
        e.flash = 3
        self.total_dmg += dmg
        if w is not None:
            w.dmg_done += dmg
        if kb > 0 and not e.frozen:
            dx, dy = e.x - sx, e.y - sy
            d = math.hypot(dx, dy) or 1
            e.kbx, e.kby, e.kbt = dx / d * 2.5 * min(3, kb), dy / d * 2.5 * min(3, kb), 4
        if len(self.floaters) < 60:
            self.floaters.append([e.x, e.y - 12, str(int(dmg)), 15])
        if e.hp <= 0:
            self.kill(e, w)

    def kill(self, e, w):
        e.dead = True
        self.kills += 1
        if w is not None:
            w.kills += 1

    def freeze_enemy(self, e, frames):
        e.frozen = max(e.frozen, frames)
        self.freezes += 1

    def heal(self, n):
        pass

    def sfx(self, name):
        pass

    def sfx_fire(self, kind):
        pass

    def p_invuln(self, frames):
        self.p.inv = max(self.p.inv, frames)

    def drop_gem(self, x, y, v):
        self.gems_dropped += 1
        self.pickups.append(Pickup("gem", x, y))

    def remove_pickup(self, it):
        if it in self.pickups:
            self.pickups.remove(it)

    # ---- loop ---------------------------------------------------------------
    def update(self):
        self.frame += 1
        self.t += 1
        p = self.p
        # walk a slow circle, stopping for a second every ~2.5 seconds
        phase = self.frame % 110
        p.moving = self.move and phase < 75
        if p.moving:
            a = self.frame / 90
            dx, dy = math.cos(a), math.sin(a)
            p.x += dx * 1.6
            p.y += dy * 1.6
            p.face_x = 1 if dx > 0 else -1
            p.face_x8 = round(dx) if abs(dx) > 0.38 else 0
            p.face_y8 = round(dy) if abs(dy) > 0.38 else 0
        if p.inv:
            p.inv -= 1
        self.cam_x, self.cam_y = p.x - W / 2, p.y - H / 2
        # keep the arena populated
        while len(self.enemies) < self.n_enemies:
            a = random.uniform(0, math.tau)
            self.enemies.append(E(p.x + math.cos(a) * 260, p.y + math.sin(a) * 160))
        self.grid = {}
        for e in self.enemies:
            self.grid.setdefault((int(e.x // 32), int(e.y // 32)), []).append(e)
        for w in self.weapons:
            w.update(self)
        self.projs = [pr for pr in self.projs if update_proj(pr, self)]
        for e in self.enemies:
            if e.flash:
                e.flash -= 1
            if e.frozen:
                e.frozen -= 1
                continue
            if e.kbt:
                e.kbt -= 1
                e.x += e.kbx
                e.y += e.kby
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d = math.hypot(dx, dy) or 1
            if d > 14:
                e.x += dx / d * e.spd
                e.y += dy / d * e.spd
        self.enemies = [e for e in self.enemies if not e.dead]
        # simulated incoming hits for Laurel / Crimson Shroud
        if self.frame % 60 == 0:
            for w in self.weapons:
                if w.blocks_hit(self):
                    self.shield_blocks += 1
                    break
        for f in self.floaters:
            f[1] -= 0.6
            f[3] -= 1
        self.floaters = [f for f in self.floaters if f[3] > 0]
        if self.flash_t:
            self.flash_t -= 1
        self.proj_count = len(self.projs)
        self.alive_counts = {w.id: w.alive for w in self.weapons}

    def draw(self):
        pyxel.cls(16)
        cx, cy = int(self.cam_x), int(self.cam_y)
        pyxel.camera(cx, cy)
        for gx in range(cx // 32, (cx + W) // 32 + 1):
            for gy in range(cy // 32, (cy + H) // 32 + 1):
                if (gx * 7 + gy * 13) % 5 == 0:
                    pyxel.pset(gx * 32 + 5, gy * 32 + 9, 18)
        for pr in self.projs:
            if pr.kind in ("water", "borra") and pr.t >= 12:
                draw_proj(pr, self)
        for w in self.weapons:
            draw_weapon_fx(w, self)
        for it in self.pickups:
            if not art.pickup("gem", it.x, it.y):
                pyxel.circ(it.x, it.y, 2, 12)
        for e in sorted(self.enemies, key=lambda e: e.y):
            art.draw_enemy(e.eid, e.x, e.y, self.frame, e.x > self.p.x, flash=bool(e.flash),
                           frozen=bool(e.frozen))
        art.draw_char("antonio_belpaese", self.p.x, self.p.y, self.p.moving, self.frame,
                      self.p.face_x < 0)
        for pr in self.projs:
            if not (pr.kind in ("water", "borra") and pr.t >= 12):
                draw_proj(pr, self)
        for x, y, s, _ in self.floaters:
            pyxel.text(x - len(s) * 2, y, s, 7)
        pyxel.camera()
        if self.flash_t:
            pyxel.dither(0.4)
            pyxel.rect(0, 0, W, H, 7)
            pyxel.dither(1.0)
        y = 3
        for w in self.weapons:
            art.icon(w.id, 10, y + 6)
            pyxel.text(20, y + 3, f"{w.id} L{w.level} dmg {int(w.dmg_done)} live {w.alive}", 7)
            y += 13
        pyxel.text(W - 110, 3, f"kills {self.kills} frz {self.freezes}", 10)
        pyxel.text(W - 110, 11, f"blocks {self.shield_blocks} gold {self.gold}", 10)


if __name__ == "__main__":
    Lab()
