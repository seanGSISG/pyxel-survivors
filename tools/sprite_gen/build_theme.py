"""Pack the picked 90s renders into a Pyxel atlas in the wiki atlas format.

    uv run --with pillow --with numpy tools/sprite_gen/build_theme.py

Reads raw/qpixel0.5/<id>_s<seed>.png (seed from picks.json, default 90),
pixelizes each at its tier height and writes themes/nineties/page_N.png,
page_N_s.png and atlas.json. Game keys are resolved here, at build time, so
art.py loads this exactly like the wiki atlas: every enemy id points at its
family's sprite, and big variants and bosses are re-pixelized larger from the
same render rather than upscaled.
"""

import json
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_atlas import KEY, pack  # noqa: E402
from pixelize import BASE, NEON, pixelize  # noqa: E402

RAW = HERE / "raw" / "qpixel0.5"
OUT = ROOT / "themes" / "nineties"

HEROES = {  # the four Belpaese slots get the heroes, everyone else a 90s archetype
    "antonio_belpaese": "hero_snapjaw", "imelda_belpaese": "hero_dash",
    "pasqualina_belpaese": "hero_boxer", "gennaro_belpaese": "hero_chomp",
    "arca_ladonna": "char_skater", "porta_ladonna": "char_grunge", "lama_ladonna": "char_blader",
    "poe_ratcho": "char_mallrat", "suor_clerici": "char_bmx", "dommario": "char_pizzaguy",
    "krochi_freetto": "char_arcade", "christine_davain": "char_dancer",
    "pugnala_provola": "char_lasertag", "giovanna_grana": "char_raver",
    "poppea_pecorina": "char_surfer", "concetta_caciotta": "char_scientist",
    "mortaccio": "char_skelejock", "yatta_cavallo": "char_capgun", "bianca_ramba": "char_action",
    "osole_meeo": "char_beach", "sir_ambrojoe": "char_cardboard",
    "iguana_gallo_valletto": "char_iguana", "divano_thelma": "char_couch",
    "zi_assunta_belpaese": "char_grandma",
}

# First keyword found in the enemy id wins; order matters (reaper_trainee before reaper).
FAMILY = [
    ("reaper", "mon_late_fee"), ("stage_killer", "mon_late_fee"), ("stalker", "mon_late_fee"),
    ("drowner", "mon_late_fee"), ("maddener", "mon_late_fee"), ("trickster", "mon_late_fee"),
    ("pipeestrello", "mon_pizza_bat"), ("bat", "mon_pizza_bat"), ("skelewing", "mon_pizza_bat"),
    ("mummy", "mon_tape_mummy"), ("skele", "mon_skate_skeleton"), ("skul", "mon_skate_skeleton"),
    ("scarleton", "mon_skate_skeleton"), ("bloodbath", "mon_skate_skeleton"),
    ("sneaky", "mon_crt_head"), ("medusa", "mon_crt_head"), ("testa", "mon_crt_head"),
    ("head", "mon_crt_head"), ("ghost", "mon_vhs_ghost"), ("merdusa", "mon_vhs_ghost"),
    ("mudman", "mon_toxic_ooze"), ("golem", "mon_toxic_ooze"), ("elemental", "mon_toxic_ooze"),
    ("melone", "mon_toxic_ooze"), ("werewolf", "mon_sewer_rat"), ("beast", "mon_sewer_rat"),
    ("musc", "mon_sewer_rat"), ("minotaur", "mon_bull_biker"), ("mignotaur", "mon_bull_biker"),
    ("zombie", "mon_mall_zombie"), ("lost_twin", "mon_mall_zombie"),
    ("witch", "mon_aerobics_witch"), ("hag", "mon_aerobics_witch"), ("mage", "mon_aerobics_witch"),
    ("succubus", "mon_aerobics_witch"), ("priest", "mon_aerobics_witch"),
    ("manti", "mon_chattering_teeth"), ("crab", "mon_chattering_teeth"),
    ("harzia", "mon_chattering_teeth"), ("venus", "mon_grass_pot"), ("flower", "mon_grass_pot"),
    ("merman", "mon_sewer_gator"), ("tritont", "mon_sewer_gator"), ("shrimp", "mon_sewer_gator"),
    ("jellyfish", "mon_slime_jelly"), ("tetrabrachia", "mon_slime_jelly"),
    ("snake", "mon_slinky_snake"), ("trinacria", "mon_slinky_snake"),
    ("gallo", "mon_pet_chick"), ("gallotrice", "mon_pet_chick"),
    ("guardian", "mon_figure_trooper"), ("knight", "mon_figure_trooper"),
    ("lizard", "mon_figure_trooper"), ("archon", "mon_arcade_mimic"),
    ("cherub", "mon_arcade_mimic"), ("throne", "mon_arcade_mimic"),
    ("demon", "mon_dialup_demon"), ("devil", "mon_dialup_demon"), ("ghiavolo", "mon_dialup_demon"),
    ("imp", "mon_dialup_demon"), ("nesufritto", "mon_dialup_demon"),
]
DEFAULT_MONSTER = "mon_toxic_ooze"

PICKUPS = {k: f"pk_{k}" for k in (
    "gem", "gem_green", "gem_red", "coin", "coinbag", "richbag", "rosary",
    "clock", "vacuum", "nduja", "clover", "chest", "chest_evo", "chest_arcana")}
PICKUPS["chicken"] = "pk_heart"  # healing is a 1UP heart: pizza would read as the pizza-bat enemies
LIGHTS = {"brazier": "lt_boombox", "candelabrone": "lt_lavalamp", "lampost": "lt_neonpost",
          "lantern": "lt_jukebox", "blue_brazier": "lt_bluelamp"}
PICKUP_H = {"gem": 10, "gem_green": 12, "gem_red": 14, "coin": 10, "chest": 16,
            "chest_evo": 16, "chest_arcana": 16}


def family(eid):
    return next((t for word, t in FAMILY if word in eid), DEFAULT_MONSTER)


def enemy_height(eid):
    if any(w in eid for w in ("boss", "colossal", "stage_killer", "archdemon", "reaper")) \
            and "trainee" not in eid:
        return 64
    if any(w in eid for w in ("big", "giant", "wall", "elite", "archon", "the_")):
        return 44
    if "swarm" in eid or "fast" in eid:
        return 24
    return 32


def main():
    g = json.loads((ROOT / "gamedata.json").read_text())
    picks = json.loads((HERE / "picks.json").read_text()) if (HERE / "picks.json").exists() else {}
    cache = {}

    def sprite(tid, h):
        if (tid, h) not in cache:
            src = RAW / f"{tid}_s{picks.get(tid, 90)}.png"
            cache[tid, h] = pixelize(src, h)
        return [cache[tid, h]]

    items = {}
    for cid, tid in HEROES.items():
        items[f"char:{cid}"] = sprite(tid, 40)
    for eid in list(g["enemies"]) + ["reaper"]:
        items[f"enemy:{eid}"] = sprite(family(eid), enemy_height(eid))
    for k, tid in PICKUPS.items():
        items[f"pickup:{k}"] = sprite(tid, PICKUP_H.get(k, 14))
    for k, tid in LIGHTS.items():
        items[f"light:{k}"] = sprite(tid, 28)

    q = Image.new("P", (1, 1))
    colors = [tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in BASE + NEON]
    q.putpalette([v for c in colors for v in c] + [0] * 3 * (256 - len(colors)))
    pages, index = pack(items, colors, q)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("page_*.png"):
        old.unlink()
    for i, p in enumerate(pages):
        p.save(OUT / f"page_{i}.png")
        sil = Image.new("RGB", p.size, KEY)
        opaque = Image.new("L", p.size, 0)
        opaque.putdata([0 if px == KEY else 255 for px in p.get_flattened_data()])
        sil.paste((238, 238, 238), (0, 0), opaque)
        sil.save(OUT / f"page_{i}_s.png")
    # palette slots 22+ carry the neon extension; base colours already live in 0-15
    (OUT / "atlas.json").write_text(json.dumps({"palette": NEON, "sprites": index}))
    fams = {}
    for eid in g["enemies"]:
        fams[family(eid)] = fams.get(family(eid), 0) + 1
    print(f"{len(index)} keys, {len(cache)} distinct sprites, {len(pages)} pages")
    print("enemy families:", dict(sorted(fams.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
