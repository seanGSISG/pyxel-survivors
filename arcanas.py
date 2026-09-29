"""Arcana cards: run-wide modifiers chosen at the start (and from Arcana chests).

The Arcanas object is the only hook surface weapons/world call into. Every
hook is a cheap no-op when no relevant Arcana is active.
"""

import data


class Arcanas:
    def __init__(self, g, ids=()):
        self.g = g
        self.active = list(ids)

    def has(self, aid):
        return aid in self.active

    def add(self, aid):
        if aid not in self.active:
            self.active.append(aid)
            self.on_add(aid)

    def listed(self, aid, wid):
        """True if Arcana `aid` is active and lists weapon `wid`."""
        return aid in self.active and wid in data.ARCANAS[aid]["affects"]

    # ---- hooks (weapons.py) ------------------------------------------------
    def amount_bonus(self, w):
        """Extra projectiles for weapon w (Beginning, Gemini...)."""
        return 0

    def cooldown_factor(self, w):
        """Multiplier on weapon w's cooldown this frame (Tragic Princess...)."""
        return 1.0

    def bounces(self, w):
        """Extra bounces for w's projectiles (Waltz of Pearls, Iron Blue Will)."""
        return 0

    def crit(self, w):
        """(chance, multiplier) crit override for w, or None (Slash)."""
        return None

    def freeze_chance(self, w):
        """Chance that w's hits freeze (Jail of Crystal)."""
        return 0.0

    def on_hit(self, pr, e):
        """A projectile/effect of weapon pr.w hit enemy e (Heart of Fire...)."""

    def on_expire(self, pr):
        """A projectile of pr.w expired (Twilight Requiem explosions)."""

    # ---- hooks (world) -----------------------------------------------------
    def on_add(self, aid):
        """Immediate effect when an Arcana is gained."""

    def update(self):
        """Per-frame effects (stat oscillation, Mad Groove pulls, ...)."""

    def stat_mods(self, ps):
        """Adjust the player stat dict in place after passives are applied."""

    def heal_mult(self):
        return 1.0

    def on_heal(self, amount):
        """Called after healing `amount` HP (Sarabande of Healing)."""

    def on_hurt(self, dmg):
        """Called after the player takes `dmg` (Heart of Fire)."""

    def on_kill(self, e, w):
        """Called when an enemy dies."""

    def on_freeze(self, e):
        """Called when an enemy is frozen (Out of Bounds)."""

    def on_gold(self, amount):
        """Called when gold is gained (Disco of Gold)."""

    def xp_gain(self, value):
        """Filter XP from a gem; return the XP actually gained (Game Killer)."""
        return value

    def chest_min_items(self):
        return 1

    def on_revive(self):
        """Called when a Revival is consumed (Awake)."""
