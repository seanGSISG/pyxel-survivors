"""Game data: loads gamedata.json (compiled from the Vampire Survivors wiki by
tools/build_gamedata.py) and adds engine constants.

Game numbers (damage, cooldowns, level gains, HP, XP, waves) come from the
wiki. Spatial values (radii, px/frame speeds) are rescaled for this screen.
"""

import json
import pathlib

_G = json.loads((pathlib.Path(__file__).parent / "gamedata.json").read_text())

WEAPONS = _G["weapons"]
PASSIVES = _G["passives"]
ENEMIES = _G["enemies"]
STAGES = _G["stages"]
STAGE_ORDER = ["mad_forest", "inlaid_library", "dairy_plant", "gallo_tower", "cappella_magna"]
CHARACTERS = list(_G["characters"].values())
ARCANAS = _G["arcanas"]
MAP_EVENTS = _G["map_events"]

# Weapons that can be offered on level-up (base, non-exclusive).
BASE_WEAPONS = [k for k, v in WEAPONS.items() if v["type"] == "Normal" and not v["exclusive"]]


def _evolutions():
    """evolved id -> (weapon ids that must be max level, passive ids that must be owned)."""
    out = {}
    for normal_first in (True, False):  # base weapons first, then chains (Bi -> Tri-Bracelet)
        for k, v in WEAPONS.items():
            if (v["type"] == "Normal") != normal_first:
                continue
            if v["evo"]:
                out.setdefault(v["evo"], ([k], list(v["evo_with"])))
            if v["union"]:
                ws = [k] + [u for u in v["union_with"] if u in WEAPONS]
                ps = [u for u in v["union_with"] if u in PASSIVES]
                out.setdefault(v["union"], (ws, ps))
    return out


EVOLUTIONS = _evolutions()

# Enemy speed units -> px/frame. Zombie (100) ~0.84 px/f, bat (140) ~1.18, player 1.8:
# the opening bats move at ~65% of the player, so a fresh run can outpace them as in VS.
SPEED_UNIT = 0.0084
PLAYER_SPEED = 1.8
MAGNET_BASE = 26
MAX_ENEMIES = 300
MAX_GEMS = 220
INVULN_FRAMES = 8  # 240 ms at 30 fps
ATTRACTORB_MULT = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

# Light-source drops: (kind, weight, min player level)
LIGHT_DROPS = [
    ("coin", 50, 0), ("coinbag", 10, 0), ("chicken", 12, 0), ("richbag", 1, 5),
    ("rosary", 1, 8), ("clock", 2, 4), ("vacuum", 2, 12), ("nduja", 1, 0),
    ("clover", 1, 0),
]
GOLD = {"coin": 1, "coinbag": 10, "richbag": 100}
START_LIGHTS = 5  # light sources pre-placed around the start (VS only spawns them over time)

# Stage items (wiki "Stage items"): passives lying at fixed spots, in tilesets from the start.
# Each entry is a chain of (dx, dy, chance): a spot only rolls if the previous one spawned.
TILESET = 320  # world px per wiki tileset
_D = 0.7071  # diagonal unit
STAGE_ITEMS = {
    "mad_forest": [
        ("skull_omaniac", [(-6 * _D, -6 * _D, 1)]),
        ("hollow_heart", [(0, -4.5, 1)]),
        ("spinach", [(2 * _D + 3, -2 * _D, 1), (2 * _D + 5, -2 * _D, .3),
                     (2 * _D + 4, 2 * _D, .2), (2 * _D + 6, 2 * _D, .1)]),
        ("pummarola", [(0, 5, 1)]),
        ("clover", [(-3 * _D - 4, 3 * _D, 1), (-4 * _D - 2, 4 * _D, .3),
                    (-4 * _D - 4, 4 * _D, .2), (-3 * _D - 5, 3 * _D, .1)]),
    ],
    "inlaid_library": [
        ("empty_tome", [(-5, 0, 1), (-6, 0, .4), (-7, 0, .3), (-8, 0, .2)]),
        ("stone_mask", [(5, 0, 1)]),
    ],
    "dairy_plant": [
        ("attractorb", [(-4 * _D, -4 * _D, 1)]), ("armor", [(2 * _D, -2 * _D, 1)]),
        ("wings", [(-2 * _D, 2 * _D, 1)]), ("candelabrador", [(4 * _D, 4 * _D, 1)]),
    ],
    # the wiki gives only a direction for these two stages; 4 tilesets out
    "gallo_tower": [("bracer", [(0, -4, 1)]), ("spellbinder", [(0, 4, 1)])],
    "cappella_magna": [
        ("crown", [(-0.5, -4, 1)]), ("tirajisu", [(0.5, -4, 1)]), ("duplicator", [(0, 4, 1)]),
    ],
}
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
