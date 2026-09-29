"""Game data: weapons, passives, evolutions, enemies, waves, pickups.

Numbers follow the Vampire Survivors wiki (Mad Forest) where the game uses
them directly (damage, cooldowns, level gains, HP, XP, wave minutes). Spatial
values (radii, px/frame speeds) are rescaled for a 320x240 screen at 30 fps.
"""

# Enemy speed units -> px/frame. Zombie (100) ~1.1 px/f, bat ~1.5, player 1.8.
SPEED_UNIT = 0.011
PLAYER_SPEED = 1.8
MAGNET_BASE = 26
MAX_ENEMIES = 300
MAX_GEMS = 220
INVULN_FRAMES = 8  # 240 ms at 30 fps
STAGE_MINUTES = 30

# ------------------------------------------------------------------ weapons
# base: dmg, cd (s), amount, pierce, speed (mult), area (mult), dur (s)
# levels: additive deltas for L2..L8. burst: frames between volley shots
# (0 = all at once). rarity: level-up weight.

WEAPONS = {
    "whip": dict(
        name="Whip", kind="whip", rarity=100, burst=4,
        desc="Attacks horizontally, passes through enemies.",
        base=dict(dmg=10, cd=1.35, amount=1, pierce=999, speed=1, area=1, dur=0),
        levels=[dict(amount=1), dict(dmg=5), dict(area=0.1, dmg=5), dict(dmg=5),
                dict(area=0.1, dmg=5), dict(dmg=5), dict(dmg=5)],
        evo="bloody_tear", evo_with="hollow_heart",
    ),
    "magic_wand": dict(
        name="Magic Wand", kind="wand", rarity=100, burst=3,
        desc="Fires at the nearest enemy.",
        base=dict(dmg=10, cd=1.2, amount=1, pierce=1, speed=1, area=1, dur=0),
        levels=[dict(amount=1), dict(cd=-0.2), dict(amount=1), dict(dmg=10),
                dict(amount=1), dict(pierce=1), dict(dmg=10)],
        evo="holy_wand", evo_with="empty_tome",
    ),
    "knife": dict(
        name="Knife", kind="knife", rarity=100, burst=3,
        desc="Fires quickly in the faced direction.",
        base=dict(dmg=6.5, cd=1.0, amount=1, pierce=1, speed=1, area=1, dur=0),
        levels=[dict(amount=1), dict(amount=1, dmg=5), dict(amount=1), dict(pierce=1),
                dict(amount=1), dict(amount=1, dmg=5), dict(pierce=1)],
        evo="thousand_edge", evo_with="bracer",
    ),
    "axe": dict(
        name="Axe", kind="axe", rarity=100, burst=6,
        desc="High damage, high Area scaling.",
        base=dict(dmg=20, cd=4.0, amount=1, pierce=3, speed=1, area=1.3, dur=0),
        levels=[dict(amount=1), dict(dmg=20), dict(pierce=2), dict(amount=1),
                dict(dmg=20), dict(pierce=2), dict(dmg=20)],
        evo="death_spiral", evo_with="candelabrador",
    ),
    "cross": dict(
        name="Cross", kind="cross", rarity=80, burst=3,
        desc="Aims at nearest enemy, has boomerang effect.",
        base=dict(dmg=5, cd=2.0, amount=1, pierce=999, speed=1, area=1, dur=0),
        levels=[dict(dmg=10), dict(area=0.1, speed=0.25), dict(amount=1), dict(dmg=10),
                dict(area=0.1, speed=0.25), dict(amount=1), dict(dmg=10)],
        evo="heaven_sword", evo_with="clover",
    ),
    "king_bible": dict(
        name="King Bible", kind="bible", rarity=80, burst=0,
        desc="Orbits around the character.",
        base=dict(dmg=10, cd=3.0, amount=1, pierce=999, speed=1, area=1, dur=3.0),
        levels=[dict(amount=1), dict(area=0.25, speed=0.3), dict(dur=0.5, dmg=10),
                dict(amount=1), dict(area=0.25, speed=0.3), dict(dur=0.5, dmg=10),
                dict(amount=1)],
        evo="unholy_vespers", evo_with="spellbinder",
    ),
    "fire_wand": dict(
        name="Fire Wand", kind="fire", rarity=80, burst=0,
        desc="Fires at a random enemy, deals heavy damage.",
        base=dict(dmg=20, cd=3.0, amount=3, pierce=1, speed=0.75, area=1, dur=0),
        levels=[dict(dmg=10), dict(dmg=10, speed=0.2), dict(dmg=10), dict(dmg=10, speed=0.2),
                dict(dmg=10), dict(dmg=10, speed=0.2), dict(dmg=10)],
        evo="hellfire", evo_with="spinach",
    ),
    "garlic": dict(
        name="Garlic", kind="garlic", rarity=70, burst=0,
        desc="Damages nearby enemies. Reduces resistance to knockback.",
        base=dict(dmg=5, cd=1.3, amount=0, pierce=999, speed=1, area=1, dur=0),
        levels=[dict(area=0.4, dmg=2), dict(cd=-0.1, dmg=1), dict(area=0.2, dmg=1),
                dict(cd=-0.1, dmg=2), dict(area=0.2, dmg=1), dict(cd=-0.1, dmg=1),
                dict(area=0.2, dmg=2)],
        evo="soul_eater", evo_with="pummarola",
    ),
    "santa_water": dict(
        name="Santa Water", kind="water", rarity=100, burst=6,
        desc="Generates damaging zones.",
        base=dict(dmg=10, cd=4.5, amount=1, pierce=999, speed=1, area=1, dur=2.0),
        levels=[dict(amount=1, area=0.2), dict(dur=0.5, dmg=10), dict(amount=1, area=0.2),
                dict(dur=0.25, dmg=10), dict(amount=1, area=0.2), dict(dur=0.25, dmg=5),
                dict(area=0.2, dmg=5)],
        evo="la_borra", evo_with="attractorb",
    ),
    "lightning_ring": dict(
        name="Lightning Ring", kind="ring", rarity=80, burst=2,
        desc="Strikes at random enemies.",
        base=dict(dmg=15, cd=4.5, amount=2, pierce=999, speed=1, area=1, dur=0),
        levels=[dict(amount=1), dict(area=1.0, dmg=10), dict(amount=1),
                dict(area=1.0, dmg=20), dict(amount=1), dict(area=1.0, dmg=20),
                dict(amount=1)],
        evo="thunder_loop", evo_with="duplicator",
    ),
    "runetracer": dict(
        name="Runetracer", kind="rune", rarity=80, burst=3,
        desc="Passes through enemies, bounces around.",
        base=dict(dmg=10, cd=3.0, amount=1, pierce=999, speed=1, area=1, dur=2.25),
        levels=[dict(dmg=5, speed=0.2), dict(dur=0.3, dmg=5), dict(amount=1),
                dict(dmg=5, speed=0.2), dict(dur=0.3, dmg=5), dict(amount=1),
                dict(dur=0.5)],
        evo="no_future", evo_with="armor",
    ),
    # ----------------------------------------------------------- evolutions
    "bloody_tear": dict(
        name="Bloody Tear", kind="tear", rarity=0, burst=4, evolved=True,
        desc="Evolved Whip. Can deal critical damage and absorb HP.",
        base=dict(dmg=40, cd=1.35, amount=2, pierce=999, speed=1, area=1.3, dur=0),
        levels=[],
    ),
    "holy_wand": dict(
        name="Holy Wand", kind="holy", rarity=0, burst=2, evolved=True,
        desc="Evolved Magic Wand. Fires with no delay.",
        base=dict(dmg=30, cd=0.5, amount=4, pierce=2, speed=2, area=1, dur=0),
        levels=[],
    ),
    "thousand_edge": dict(
        name="Thousand Edge", kind="edge", rarity=0, burst=1, evolved=True,
        desc="Evolved Knife. Fires with no delay.",
        base=dict(dmg=16.5, cd=0.35, amount=6, pierce=3, speed=1.5, area=1, dur=0),
        levels=[],
    ),
    "death_spiral": dict(
        name="Death Spiral", kind="spiral", rarity=0, burst=0, evolved=True,
        desc="Evolved Axe. Scythes spiral outward.",
        base=dict(dmg=60, cd=4.0, amount=1, pierce=999, speed=0.8, area=1.2, dur=0),
        levels=[],
    ),
    "heaven_sword": dict(
        name="Heaven Sword", kind="heaven", rarity=0, burst=5, evolved=True,
        desc="Evolved Cross. Can deal critical damage.",
        base=dict(dmg=77, cd=3.3, amount=2, pierce=999, speed=1.25, area=1.4, dur=0),
        levels=[],
    ),
    "unholy_vespers": dict(
        name="Unholy Vespers", kind="vespers", rarity=0, burst=0, evolved=True,
        desc="Evolved King Bible. Never ends.",
        base=dict(dmg=30, cd=3.0, amount=4, pierce=999, speed=1.6, area=1.75, dur=0),
        levels=[],
    ),
    "hellfire": dict(
        name="Hellfire", kind="hellfire", rarity=0, burst=0, evolved=True,
        desc="Evolved Fire Wand. Passes through enemies.",
        base=dict(dmg=100, cd=3.0, amount=2, pierce=999, speed=1, area=1, dur=0),
        levels=[],
    ),
    "soul_eater": dict(
        name="Soul Eater", kind="soul", rarity=0, burst=0, evolved=True,
        desc="Evolved Garlic. Steals hearts. Power grows with healing.",
        base=dict(dmg=20, cd=1.0, amount=0, pierce=999, speed=1, area=2.2, dur=0),
        levels=[],
    ),
    "la_borra": dict(
        name="La Borra", kind="borra", rarity=0, burst=6, evolved=True,
        desc="Evolved Santa Water. Zones follow you and grow.",
        base=dict(dmg=40, cd=4.5, amount=4, pierce=999, speed=1, area=2.0, dur=4.0),
        levels=[],
    ),
    "thunder_loop": dict(
        name="Thunder Loop", kind="thunder", rarity=0, burst=2, evolved=True,
        desc="Evolved Lightning Ring. Projectiles strike twice.",
        base=dict(dmg=65, cd=4.5, amount=6, pierce=999, speed=1, area=4.0, dur=0),
        levels=[],
    ),
    "no_future": dict(
        name="NO FUTURE", kind="nofuture", rarity=0, burst=3, evolved=True,
        desc="Evolved Runetracer. Explodes when bouncing.",
        base=dict(dmg=30, cd=1.0, amount=1, pierce=999, speed=1.6, area=1, dur=3.25),
        levels=[],
    ),
}

BASE_WEAPONS = [k for k, v in WEAPONS.items() if not v.get("evolved")]

# ----------------------------------------------------------------- passives
# stat: key in player stats. per: gain per level. max: max level.

PASSIVES = {
    "spinach": dict(name="Spinach", stat="might", per=0.10, max=5, rarity=100,
                    desc="Raises inflicted damage by 10%."),
    "armor": dict(name="Armor", stat="armor", per=1, max=5, rarity=100,
                  desc="Reduces incoming damage by 1."),
    "hollow_heart": dict(name="Hollow Heart", stat="maxhp", per=0.20, max=5, rarity=90,
                         desc="Augments max health by 20%."),
    "pummarola": dict(name="Pummarola", stat="recovery", per=0.2, max=5, rarity=90,
                      desc="Recovers 0.2 HP per second."),
    "empty_tome": dict(name="Empty Tome", stat="cooldown", per=-0.08, max=5, rarity=50,
                       desc="Reduces weapons cooldown by 8%."),
    "candelabrador": dict(name="Candelabrador", stat="area", per=0.10, max=5, rarity=100,
                          desc="Augments area of attacks by 10%."),
    "bracer": dict(name="Bracer", stat="speed", per=0.10, max=5, rarity=100,
                   desc="Increases projectiles speed by 10%."),
    "spellbinder": dict(name="Spellbinder", stat="duration", per=0.10, max=5, rarity=100,
                        desc="Increases duration of weapon effects by 10%."),
    "duplicator": dict(name="Duplicator", stat="amount", per=1, max=2, rarity=50,
                       desc="Weapons fire more projectiles."),
    "wings": dict(name="Wings", stat="move", per=0.10, max=5, rarity=50,
                  desc="Character moves 10% faster."),
    "attractorb": dict(name="Attractorb", stat="magnet", per=0, max=5, rarity=100,
                       desc="Items pickup range +50%."),
    "clover": dict(name="Clover", stat="luck", per=0.10, max=5, rarity=100,
                   desc="Character gets 10% luckier."),
    "crown": dict(name="Crown", stat="growth", per=0.08, max=5, rarity=70,
                  desc="Character gains 8% more experience."),
}
ATTRACTORB_MULT = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

# --------------------------------------------------------------- characters

CHARACTERS = [
    dict(name="Antonio", weapon="whip", pal={}, hp=120, armor=1,
         bonus="+10% Might every 10 levels", might_per10=0.1),
    dict(name="Imelda", weapon="magic_wand", pal={8: 12, 4: 10, 7: 6}, hp=100,
         bonus="+10% Growth", growth=0.10),
    dict(name="Pasqualina", weapon="runetracer", pal={8: 7, 7: 12, 4: 9}, hp=100,
         bonus="+10% Projectile Speed", speed=0.10),
    dict(name="Gennaro", weapon="knife", pal={8: 5, 7: 6, 4: 1}, hp=100,
         bonus="+1 Amount", amount=1),
]

# ------------------------------------------------------------------ enemies
# spr: sprite base name (frames spr0/spr1). pal: colour swaps.
# hp, dmg, speed (units), kb (knockback taken), xp, scale.
# hplvl: HP multiplied by player level (bosses, flower walls).

ENEMIES = {
    "bat": dict(spr="bat", hp=1, dmg=5, speed=140, kb=1.0, xp=1),
    "redbat": dict(spr="bat", hp=5, dmg=5, speed=140, kb=1.0, xp=1, pal={2: 8, 8: 10}),
    "zombie": dict(spr="zomb", hp=10, dmg=10, speed=100, kb=0.8, xp=1),
    "skeleton": dict(spr="skel", hp=15, dmg=10, speed=100, kb=1.0, xp=2),
    "ghost": dict(spr="ghost", hp=10, dmg=5, speed=200, kb=0.0, xp=1.5),
    "mudman": dict(spr="mud", hp=70, dmg=10, speed=100, kb=0.3, xp=2.5, pal={4: 13, 9: 5}),
    "mudman2": dict(spr="mud", hp=150, dmg=10, speed=100, kb=0.3, xp=2.5, pal={4: 3, 9: 11}),
    "giantbat": dict(spr="bat", hp=270, dmg=10, speed=140, kb=0.1, xp=2.5, scale=2.0,
                     pal={2: 1, 8: 8}),
    "werewolf": dict(spr="wolf", hp=180, dmg=14, speed=130, kb=0.8, xp=2),
    "mantichana": dict(spr="mant", hp=500, dmg=20, speed=80, kb=0.0, xp=3),
    "mummy": dict(spr="skel", hp=500, dmg=20, speed=80, kb=0.0, xp=3, scale=1.3,
                  pal={7: 15, 13: 9, 1: 4}),
    "venus": dict(spr="flower", hp=500, dmg=20, speed=80, kb=0.0, xp=3, scale=1.3),
    "flowerwall": dict(spr="flower", hp=30, dmg=1, speed=20, kb=1.0, xp=2, hplvl=True,
                       pal={14: 12, 10: 7}),
    "swarmbat": dict(spr="bat", hp=1, dmg=1, speed=0, kb=1.0, xp=1, pal={2: 5}),
    "swarmghost": dict(spr="ghost", hp=10, dmg=5, speed=0, kb=0.0, xp=1.5),
    # bosses (drop a treasure chest)
    "glowbat": dict(spr="bat", hp=50, dmg=10, speed=140, kb=0.0, xp=30, scale=1.6,
                    pal={2: 10, 8: 8}, boss=True, hplvl=True),
    "silverbat": dict(spr="bat", hp=50, dmg=10, speed=140, kb=0.0, xp=30, scale=1.6,
                      pal={2: 13, 8: 1}, boss=True, hplvl=True),
    "boss_mant": dict(spr="mant", hp=150, dmg=20, speed=160, kb=0.0, xp=50, scale=2.0,
                      boss=True, hplvl=True),
    "boss_bigmant": dict(spr="mant", hp=150, dmg=25, speed=140, kb=0.0, xp=50, scale=2.6,
                         pal={2: 8, 14: 9}, boss=True, hplvl=True),
    "boss_giantbat": dict(spr="bat", hp=100, dmg=15, speed=140, kb=0.0, xp=30, scale=2.6,
                          pal={2: 1, 8: 8}, boss=True, hplvl=True),
    "boss_wolf": dict(spr="wolf", hp=200, dmg=25, speed=140, kb=0.0, xp=50, scale=2.2,
                      pal={5: 13, 13: 7}, boss=True, hplvl=True),
    "boss_mummy": dict(spr="skel", hp=250, dmg=30, speed=100, kb=0.0, xp=25, scale=2.4,
                       pal={7: 15, 13: 9, 1: 4}, boss=True, hplvl=True),
    "boss_venus": dict(spr="flower", hp=150, dmg=30, speed=160, kb=0.0, xp=30, scale=2.4,
                       pal={14: 12, 10: 7, 8: 6}, boss=True, hplvl=True),
    "reaper": dict(spr="reaper", hp=655350, dmg=65535, speed=0, kb=0.0, xp=0, scale=2.0,
                   reaper=True),
}

# Wave per minute: enemies, minimum alive, spawn interval (s),
# bosses spawned at the minute mark, events: (kind, arg).
WAVES = [
    dict(e=["redbat"], min=15, iv=1.0),
    dict(e=["zombie", "bat"], min=30, iv=1.0, boss=["glowbat"]),
    dict(e=["bat", "redbat", "bat"], min=50, iv=0.5, ev=[("batswarm", 2)]),
    dict(e=["skeleton"], min=40, iv=0.25, boss=["glowbat"]),
    dict(e=["skeleton", "ghost"], min=30, iv=1.0),
    dict(e=["mudman2"], min=10, iv=1.0, boss=["boss_mant"], ev=[("flowerring", 30)]),
    dict(e=["zombie", "mudman2"], min=20, iv=0.5),
    dict(e=["redbat", "mudman"], min=80, iv=0.5, boss=["glowbat"], ev=[("batswarm", 3)]),
    dict(e=["zombie"], min=100, iv=1.5, boss=["boss_giantbat"]),
    dict(e=["giantbat", "zombie"], min=30, iv=0.5, boss=["silverbat"]),
    dict(e=["mudman", "mudman2"], min=10, iv=0.5, boss=["boss_bigmant"], ev=[("flowerring", 60)]),
    dict(e=["skeleton"], min=280, iv=0.1),
    dict(e=["werewolf", "ghost", "skeleton"], min=20, iv=0.25, boss=["glowbat"]),
    dict(e=["werewolf", "ghost", "ghost"], min=150, iv=0.5, ev=[("ghostswarm", 3)]),
    dict(e=["giantbat", "werewolf"], min=20, iv=0.1, boss=["silverbat"]),
    dict(e=["werewolf", "giantbat", "mudman2"], min=100, iv=0.1, boss=["boss_wolf"],
         ev=[("flowerring", 40)]),
    dict(e=["mantichana", "mudman", "mudman2"], min=100, iv=0.1, boss=["glowbat"]),
    dict(e=["mummy"], min=20, iv=0.2),
    dict(e=["mummy", "mudman"], min=60, iv=0.2, boss=["silverbat"]),
    dict(e=["mummy", "mudman"], min=100, iv=0.1),
    dict(e=["mummy", "mudman2", "giantbat"], min=100, iv=0.1, boss=["boss_mummy"]),
    dict(e=["flowerwall", "mummy"], min=200, iv=0.1),
    dict(e=["flowerwall", "mummy", "venus"], min=200, iv=0.1, boss=["glowbat"]),
    dict(e=["venus", "mummy"], min=240, iv=0.1, boss=["silverbat"], ev=[("flowerring", 40)]),
    dict(e=["venus", "flowerwall", "werewolf"], min=280, iv=0.1),
    dict(e=["venus"], min=100, iv=0.1, boss=["boss_venus"], ev=[("flowerring", 30)]),
    dict(e=["venus", "flowerwall"], min=150, iv=0.1),
    dict(e=["mummy", "mudman", "mudman2"], min=280, iv=0.1, boss=["glowbat"],
         ev=[("ghostswarm", 4)]),
    dict(e=["giantbat", "werewolf"], min=280, iv=0.1, boss=["glowbat", "boss_giantbat"]),
    dict(e=["werewolf", "mantichana", "giantbat"], min=280, iv=0.1,
         boss=["glowbat", "silverbat"], ev=[("batswarm", 4)]),
]

# Minutes whose boss chest may contain an evolution (Mad Forest rule).
EVO_CHEST_MINUTES = {1} | set(range(10, 31))

# ------------------------------------------------------------------ pickups
# Light-source drops: (kind, weight, min player level)
LIGHT_DROPS = [
    ("coin", 50, 0), ("coinbag", 10, 0), ("chicken", 12, 0), ("richbag", 1, 5),
    ("rosary", 1, 8), ("clock", 2, 4), ("vacuum", 2, 12), ("nduja", 1, 0),
    ("clover", 1, 0),
]
GOLD = {"coin": 1, "coinbag": 10, "richbag": 100}
CHEST_SEQUENCE = [1, 1, 3, 1, 1, 5]


def xp_needed(level):
    """XP required to go from `level` to `level + 1`."""
    if level == 1:
        return 5
    if level < 20:
        need = 10 * level - 5
    elif level < 40:
        need = 10 * 19 - 5 + 13 * (level - 19)
    else:
        need = 10 * 19 - 5 + 13 * 21 + 16 * (level - 40)
    if level == 20:
        need += 600
    if level == 40:
        need += 2400
    return need
