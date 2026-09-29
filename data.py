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

# Enemy speed units -> px/frame. Zombie (100) ~1.1 px/f, bat ~1.5, player 1.8.
SPEED_UNIT = 0.011
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
