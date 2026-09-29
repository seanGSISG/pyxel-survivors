"""Arcana cards: run-wide modifiers chosen at the start (and from Arcana chests).

The Arcanas object is the only hook surface weapons/world call into. Every
hook is a cheap no-op when no relevant Arcana is active. Effects follow each
card's wiki page (wiki/raw/Arcanas); "listed" weapons come from its `affects`.

Arcana explosions are spawned with w=None so they never re-trigger
on_hit/on_expire (no recursion) and don't count against weapon pools.
"""

import math
import random

import art
import data
import weapons

FPS = 30
MIN = 60 * FPS

KILLER, GEMINI, TWILIGHT, TRAGIC, AWAKE = (
    "T00_KILLER", "T01_AQUARIUS", "T02_TWILIGHT", "T03_TRAGIC", "T04_AWAKE")
CRASH, SARABANDE, IRON, MADGROOVE, DIVINE = (
    "T05_CRASH", "T06_SARABANDE", "T07_IRON_BLUE", "T08_MAD_FOREST", "T09_DIVINE")
BEGINNING, PEARLS, OUTTIME, WICKED, JEWELS = (
    "T10_BEGINNING", "T11_PEARLS", "T12_OUT_OF_TIME", "T13_WICKED", "T14_JEWELS")
GOLD, SLASH, PAINTING, ILLUSIONS, FIRE = (
    "T15_GOLD", "T16_SLASH", "T17_PAINTING", "T18_ILLUSIONS", "T19_FIRE")
SINKING, BLOODY = "T20_SINKING", "T21_BLOODY"

OSCILLATING = {CRASH, PAINTING, ILLUSIONS, WICKED}
WICKED_ORDER = ("growth", "luck", "greed", "curse")  # doubled 10 s each, in order
MAX_BOOMS_PER_FRAME = 6


def _osc(t):
    """-1..1 over a 20 s cycle (10 s from one extreme to the other)."""
    return math.sin(t * math.tau / (20 * FPS))


class Arcanas:
    def __init__(self, g, ids=()):
        self.g = g
        self.active = list(ids)
        self._sets = {aid: set(a["affects"]) for aid, a in data.ARCANAS.items()}
        self.awake_n = 0  # revivals consumed with Awake
        self.heal_pool = 0.0  # Sarabande: healing banked until a pulse
        self.orologion_mult = 1.0  # read by the light-source drop table
        self._boom_frame = -1
        self.n_booms = 0  # total Arcana explosions (test/inspection)
        self._booms = 0
        self._fire_hit = {}  # Heart of Fire: projectile id -> exploded already
        self._last_slots = -1
        self._wicked_phase = -1
        self.divine_hp = 0.0  # Divine Bloodline: Max Health from retaliation kills

    def has(self, aid):
        return aid in self.active

    def add(self, aid):
        if aid not in self.active:
            self.active.append(aid)
            self.on_add(aid)

    def listed(self, aid, wid):
        """True if Arcana `aid` is active and lists weapon `wid`."""
        return aid in self.active and wid in self._sets.get(aid, ())

    # ---- helpers -----------------------------------------------------------
    def _boom(self, x, y, dmg, r, col=9, kb=0.5):
        """Rate-limited Arcana explosion (never re-triggers Arcana hooks)."""
        g = self.g
        if g.frame != self._boom_frame:
            self._boom_frame, self._booms = g.frame, 0
        if self._booms >= MAX_BOOMS_PER_FRAME:
            return
        self._booms += 1
        self.n_booms += 1
        weapons.boom(g, None, x, y, dmg, r, col, kb)

    def _main_weapons(self):
        """Starting weapon(s) of the character plus their evolutions."""
        base = set(self.g.char["weapons"])
        out = set(base)
        for evo, (ws, _ps) in data.EVOLUTIONS.items():
            if base & set(ws):
                out.add(evo)
        return out

    # ---- hooks (weapons.py) ------------------------------------------------
    def amount_bonus(self, w):
        """Extra projectiles for weapon w (Beginning, Gemini)."""
        n = 0
        if self.listed(GEMINI, w.id):
            n += 1
        if BEGINNING in self.active:
            if w.id in self._main_weapons():
                n += 3
            elif w.id in self._sets[BEGINNING]:
                n += 1
        return n

    def cooldown_factor(self, w):
        """Tragic Princess: listed weapons recharge faster while moving."""
        if self.listed(TRAGIC, w.id) and self.g.p.moving:
            return 0.6
        return 1.0

    def bounces(self, w):
        """Waltz of Pearls / Iron Blue Will: up to 3 bounces."""
        return 3 if (self.listed(PEARLS, w.id) or self.listed(IRON, w.id)) else 0

    def crit(self, w):
        """Slash: enables crits (20%, x2) on listed weapons; all crits deal double."""
        if SLASH not in self.active:
            return None
        base = weapons.CRIT.get(w.id)
        if base:
            return base[0], base[1] * 2
        if w.id in self._sets[SLASH]:
            return 0.2, 4.0
        return None

    def freeze_chance(self, w):
        """Jail of Crystal: listed weapon hits may freeze."""
        return 0.1 if self.listed(JEWELS, w.id) else 0.0

    def on_hit(self, pr, e):
        """Heart of Fire explosions; Divine Bloodline armor damage."""
        w = pr.w
        if w is None or pr.kind == "boom":
            return
        g = self.g
        if self.listed(FIRE, w.id):
            key = id(pr)
            if key not in self._fire_hit:  # one explosion per projectile
                self._fire_hit[key] = g.frame
                self._boom(e.x, e.y, max(5.0, pr.dmg * 0.5), 18 * weapons.PX, 8)
                if len(self._fire_hit) > 400:
                    cut = g.frame - FPS * 5
                    self._fire_hit = {k: f for k, f in self._fire_hit.items() if f > cut}
        if FIRE in self.active and e.prop and e.dead:  # light sources explode
            self._boom(e.x, e.y, 30 * g.pstats["might"], 30 * weapons.PX, 10)
        if self.listed(DIVINE, w.id) and not e.dead:
            bonus = min(250, 5 * g.pstats["armor"])
            if bonus > 0:
                g.damage_enemy(e, bonus, w, g.p.x, g.p.y, 0)

    def on_expire(self, pr):
        """Twilight Requiem: listed projectiles explode (damage scales with Curse)."""
        if pr.kind == "boom" or pr.w is None or not self.listed(TWILIGHT, pr.w.id):
            return
        curse = self.g.pstats["curse"]
        self._boom(pr.x, pr.y, 10 + 13.5 * (curse - 1) * 2, 20 * weapons.PX, 2, 0.8)

    # ---- hooks (world) -----------------------------------------------------
    def on_add(self, aid):
        """Immediate effect when an Arcana is gained."""
        g = self.g
        if aid == AWAKE:
            g.revivals += 3
        elif aid == MADGROOVE:
            self._groove()
        elif aid == OUTTIME:
            self.orologion_mult = 2.0
        if aid in OSCILLATING or aid in (SINKING, AWAKE):
            g.recompute_stats()
        g.show_banner(art.name("arcanas", data.ARCANAS[aid]).upper(), 45)

    def update(self):
        """Per-frame effects: stat oscillation, Mad Groove, Blood Astronomia, pulses."""
        if not self.active:
            return
        g = self.g
        t = g.t
        need = False
        if OSCILLATING & set(self.active) and g.frame % 6 == 0:
            need = True
        if DIVINE in self.active and g.frame % 30 == 0:  # missing-health Might bonus
            need = True
        if WICKED in self.active:
            phase = (t // (10 * FPS)) % 4
            if phase != self._wicked_phase:
                self._wicked_phase = phase
                need = True
        if SINKING in self.active and len(g.weapons) != self._last_slots:
            self._last_slots = len(g.weapons)
            need = True
        if need:
            g.recompute_stats()
        if MADGROOVE in self.active and t > 0 and t % (2 * MIN) == 0:
            self._groove()
        if BLOODY in self.active and t % FPS == 0:
            self._blood_pulse()
        if SARABANDE in self.active and self.heal_pool >= 1 and g.frame % 10 == 0:
            amt, self.heal_pool = self.heal_pool, 0.0
            self._boom(g.p.x, g.p.y, amt, 40 * weapons.PX, 14, 0.3)

    def stat_mods(self, ps):
        """Adjust the player stat dict in place after passives are applied."""
        if not self.active:
            return
        g = self.g
        lv = g.level
        if self.awake_n:
            n = self.awake_n
            ps["maxhp"] *= 1.1 ** n
            ps["armor"] += n
            for s in ("might", "area", "duration", "speed"):
                ps[s] += 0.05 * n
        if WICKED in self.active:
            for s in WICKED_ORDER:
                ps[s] += 0.01 * (lv // 2)
            ps[WICKED_ORDER[(g.t // (10 * FPS)) % 4]] *= 2
        if SINKING in self.active:
            empty = max(0, 6 - len(g.weapons))
            ps["might"] += 0.2 * empty
            ps["cooldown"] -= 0.08 * empty
        if DIVINE in self.active:
            ps["maxhp"] += self.divine_hp
        if DIVINE in self.active and ps["maxhp"] > 0:
            missing = max(0.0, 1 - g.p.hp / ps["maxhp"]) if hasattr(g, "p") else 0.0
            ps["might"] += 0.5 * missing  # up to +50% Might near death
        # oscillations multiply on top of everything else
        if CRASH in self.active:
            ps["speed"] = (ps["speed"] + 0.01 * lv) * (1 + 0.5 * _osc(g.t))
        if PAINTING in self.active:
            ps["duration"] = (ps["duration"] + 0.01 * lv) * (1 + 0.5 * _osc(g.t + 5 * FPS))
        if ILLUSIONS in self.active:
            ps["area"] = (ps["area"] + 0.01 * lv) * (1 + 0.25 * _osc(g.t + 10 * FPS))

    def heal_mult(self):
        return 2.0 if SARABANDE in self.active else 1.0

    def on_heal(self, amount):
        """Sarabande of Healing: healing is banked and released as a damage pulse."""
        if SARABANDE in self.active:
            self.heal_pool += amount

    def on_hurt(self, dmg):
        """Heart of Fire: the character explodes; Divine Bloodline retaliates."""
        g = self.g
        p = g.p
        if FIRE in self.active:
            self._boom(p.x, p.y, 20 * g.pstats["might"], 36 * weapons.PX, 8, 1.5)
        if DIVINE in self.active:
            armor = g.pstats["armor"]
            dmg_out = (10 + 5 * armor) * g.pstats["might"]
            for e in g.query(p.x, p.y, 30 * weapons.PX):
                if not e.prop:
                    g.damage_enemy(e, dmg_out, None, p.x, p.y, 1.0)
                    if e.dead:  # retaliation kills grant Max Health
                        self.divine_hp += 0.5

    def on_kill(self, e, w):
        """Called when an enemy dies."""

    def on_freeze(self, e):
        """Out of Bounds: freezing an enemy summons an explosion."""
        if OUTTIME in self.active:
            dmg = 10 + self.g.t / FPS / 30
            self._boom(e.x, e.y, dmg, 16 * weapons.PX, 12, 0.2)

    def on_gold(self, amount):
        """Disco of Gold: gold restores as many HP."""
        if GOLD in self.active and amount > 0:
            self.g.heal(amount)

    def xp_gain(self, value):
        """Game Killer: no XP; the gem becomes a projectile at the nearest enemy."""
        if KILLER not in self.active:
            return value
        g = self.g
        p = g.p
        tgt = g.nearest_enemies(p.x, p.y, 1)
        ang = math.atan2(tgt[0].y - p.y, tgt[0].x - p.x) if tgt else random.uniform(0, math.tau)
        v = 5 * weapons.PX
        g.projs.append(weapons.Proj("fire", None, p.x, p.y, math.cos(ang) * v, math.sin(ang) * v,
                                    10 * g.pstats["growth"], weapons.sec(1.2), 1,
                                    6 * weapons.PX, 1.0))
        return 0

    def chest_min_items(self):
        return 3 if KILLER in self.active else 1

    def on_revive(self):
        """Awake: each Revival consumed permanently buffs the character."""
        if AWAKE in self.active:
            self.awake_n += 1
            self.g.recompute_stats()

    # ---- internals ----------------------------------------------------------
    def _groove(self):
        """Mad Groove: pull pickups, chests and light sources into a ring."""
        g = self.g
        p = g.p
        items = [it for it in g.pickups] + [e for e in g.enemies if e.prop]
        n = max(1, len(items))
        for i, it in enumerate(items):
            a = i * math.tau / n
            r = 60 * weapons.PX + (i % 3) * 10
            it.x, it.y = p.x + math.cos(a) * r, p.y + math.sin(a) * r
        g.show_banner("MAD GROOVE", 40)
        g.sfx("coin")

    def _blood_pulse(self):
        """Blood Astronomia: listed weapons add a Magnet-sized blood zone each second."""
        g = self.g
        owned = [w for w in g.weapons if w.id in self._sets[BLOODY]]
        if not owned:
            return
        ps = g.pstats
        dmg = 5 * (1 + ps["amount"]) * len(owned) * ps["might"]
        self._boom(g.p.x, g.p.y, dmg, ps["magnet"], 8, 0.0)
