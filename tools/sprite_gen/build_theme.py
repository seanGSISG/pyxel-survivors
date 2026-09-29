"""Pack the picked 90s renders into a Pyxel atlas in the wiki atlas format.

    uv run --with pillow --with numpy tools/sprite_gen/build_theme.py

Reads raw/qpixel0.5/<id>_s<seed>.png (seed from picks.json, default 90),
pixelizes each at its tier height and writes themes/nineties/page_N.png,
page_N_s.png and atlas.json. Game keys are resolved here, at build time, so
art.py loads this exactly like the wiki atlas: every enemy id points at its
family's sprite, and big variants and bosses are re-pixelized larger from the
same render rather than upscaled.

Characters and enemies move on four frames: the picked sprite, then the three
poses pose.py drew of it (pose_cycle). A design without pose frames gets a small
derived shuffle instead (step_cycle). Frames are padded evenly around the picked
sprite, whose size stays the sprite's body size in atlas.json, so hitboxes and
placement do not change. Identical frames are packed once and shared.
"""

import json
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_atlas import KEY, pack  # noqa: E402
from pixelize import BASE, NEON, pixelize, pixelize_pose  # noqa: E402
from pose import MOVE_OF  # noqa: E402

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
# Weapons the game draws as sprites (weapons.py spr()), with the box each must fit: the draw
# scales were tuned against sprites of these sizes.
WSPR = {"knife": 28, "axe": 16, "death_spiral": 16, "cross": 16, "heaven_sword": 16,
        "king_bible": 22, "unholy_vespers": 22, "runetracer": 12, "gatti_amari": 16,
        "vicious_hunger": 28, "shadow_pinion": 16, "bone": 14, "cherry_bomb": 14, "carrello": 28,
        "celestial_dusting": 16, "la_robba": 28, "peachone": 16, "ebony_wings": 16, "vandalier": 16}
PASSIVES = {"clover": "pk_clover", "pummarola": "pk_juicebox"}  # everything else is pa_<id>
CARD_H = 80  # Arcana card height on the pick screen
# Candy colours, dark to light. The orbiting candy rings come in all of them: one frame per
# colour, recoloured from the single picked render so the shape stays the same.
CANDY = {
    "blue": ["2B335F", "395C98", "19959C", "7696DE", "70C6A9", "A9C1FF"],
    "red": ["7A0F2A", "C4122F", "C4122F", "D4186C", "FF9798", "FF9798"],
    "green": ["2E5A1C", "5E8C31", "5E8C31", "9BC53D", "9BC53D", "F5E6C8"],
    "grape": ["3D2C5E", "7E2072", "7E2072", "9D4EDD", "9D4EDD", "A9C1FF"],
    "orange": ["6B3E26", "B0703A", "D38441", "FF7A1A", "E9C35B", "FFE14D"],
    "lemon": ["B0703A", "D38441", "E9C35B", "E9C35B", "FFE14D", "F5E6C8"],
}
RINGS = {"king_bible": "blue", "unholy_vespers": "red"}  # weapon -> the colour it was rendered in


def recolour(img, src, dst):
    """Copy of img with each colour of the src ramp swapped for the same step of the dst ramp."""
    rgb = [tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in src + dst]
    swap = dict(zip(rgb[:len(src)], rgb[len(src):]))
    out = img.copy()
    out.putdata([(*swap.get(p[:3], p[:3]), p[3]) for p in img.get_flattened_data()])
    return out


# Casting: designs given to particular enemy ids, ahead of the keyword families above. The horde
# is monsters (creatures, living objects, toys and mascots gone bad); the few humanoid villain
# parodies (vil_dr_yolk, vil_moon_witch, vil_skullord, vil_lord_wheezer, vil_general_bizarro)
# only play bosses. Sizes are unchanged, so hitboxes are too.
CAST = {
    "mon_shroom": ["mudman_1"],
    "mon_bomb": ["dust_elemental"],
    "mon_sack": ["dust_elemental_boss", "unknown_2"],
    "mon_tubby": ["milk_elemental", "milk_elemental_2"],
    "mon_tomato": ["melone", "meat_golem_1"],
    "mon_purple_dino": ["big_golem_1", "big_golem_1_lv29"],
    "vil_dr_yolk": ["big_golem_2_boss"],
    "mon_troll": ["musc_musc", "big_musc_musc"],
    "mon_gargoyle": ["archon_ascia", "archon_lancia", "archon_spada", "skelewing", "skelewing_ino"],
    "vil_lord_wheezer": ["archon_disco", "archon_rame_boss"],
    "vil_megatyrant": ["fake_fallen_cherubbello", "fake_fallen_cherubbello_boss", "fallen_throne"],
    "mon_glutton_ghost": ["ghost_swarm", "fallen_cherub", "fallen_cherubbello"],
    "vil_drooler": ["the_stalker"],
    "mon_eyeball_orb": ["the_maddener", "medusa_head", "lionhead", "lionhead_boss"],
    "vil_sea_witch": ["the_drowner", "merdusa"],
    "vil_gremlin": ["the_trickster", "nesufritto"],
    "mon_eye_cluster": ["testa_di_mano_1", "testa_di_mano_2"],
    "mon_wheel_bug": ["skeleton_ninja_1", "skulorosso"],
    "mon_virtual_pet": ["skeleton_ninja_2"],
    "mon_clip": ["skullino", "lizard_pawn"],
    "vil_skullord": ["scarleton", "skullone_boss"],
    "mon_shark": ["merman_3", "merman_boss"],
    "mon_kaiju": ["tritont"],
    "mon_fire_lizard": ["dragon_shrimp_1", "dragon_shrimp_1_flag", "dragon_shrimp_2",
                        "dragon_shrimp_2_flag"],
    "vil_king_krusher": ["dragon_shrimp_1_boss", "dragon_shrimp_2_boss"],
    "mon_animatronic": ["werewolf_1_boss", "colossal_musc_musc"],
    "mon_raptor": ["demon_beast", "demon_beast_2"],
    "mon_whirl_devil": ["mignotaur", "mignotaur_rush"],
    "vil_moon_witch": ["hag", "undead_sassy_witch"],
    "mon_fuzzy_toy": ["undead_mage", "ghiavolo", "impefinger"],
    "mon_zap_rodent": ["succubus", "harzia", "harzia_v"],
    "mon_pitcher": ["succubus_boss"],
    "mon_beanbag_bear": ["demon_priest", "lost_twin"],
    "vil_general_bizarro": ["elite_devil", "archdemon_boss"],
    "mon_roach": ["mantichana_boss", "giant_enemy_crab"],
    "vil_quadro": ["manticore"],
    "mon_thwomper": ["lizard_rook", "axe_guardian"],
    "vil_exterminator": ["sword_guardian"],
    "mon_squid": ["tetrabrachia_1", "tetrabrachia_2"],
    "mon_marshmallow": ["big_mummy", "big_mummy_boss"],
    "mon_sandworm": ["trinacria"],
}
CAST_OF = {eid: tid for tid, eids in CAST.items() for eid in eids}


POSE_AREA = (0.6, 1.6)  # accepted bounding-box area of a pose, relative to its picked sprite
# Poses the edit model got wrong on review (it grew the creature a new body, or added a person):
# the picked sprite stands in, and still hops or bobs with the cycle.
BAD_POSES = {"mon_arcade_mimic": "abc", "mon_crt_head": "ab", "vil_sea_witch": "ab",
             "mon_chattering_teeth": "b", "mon_grass_pot": "b", "mon_shroom": "b", "mon_tomato": "b",
             "mon_thwomper": "b", "mon_eyeball_orb": "b", "mon_beanbag_bear": "b"}


def centroid(img, top=1.0):
    """Centre of the opaque pixels in the upper `top` share of the image."""
    w, h = img.size
    alpha = img.getchannel("A").crop((0, 0, w, max(1, round(h * top)))).load()
    pts = [(x, y) for y in range(max(1, round(h * top))) for x in range(w) if alpha[x, y]]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else (w / 2, h / 2)


def pose_cycle(ref, poses, move):
    """The picked sprite and its re-posed frames on one canvas, the picked sprite dead centre.

    Walkers and hoppers stand on the same ground line and line up on their upper body, so a
    stride moves the legs and not the head. Flyers and floaters line up on their centre of
    mass and ride a pixel up and down. A hop's middle pose is lifted clear of the ground.
    """
    grounded = move in ("walk", "hop")
    # a pose that covers far more or less than the picked sprite drew something else: stand in
    # the picked sprite (by area, as a stretch or a raised wing changes the shape, not the bulk)
    lo, hi = POSE_AREA
    area = ref.width * ref.height
    poses = [p if lo <= p.width * p.height / area <= hi else ref for p in poses]
    cx, cy = centroid(ref, 0.45 if grounded else 1.0)
    placed = [(ref, 0, 0)]
    for n, img in enumerate(poses):
        px, py = centroid(img, 0.45 if grounded else 1.0)
        if grounded:
            y = ref.height - img.height - (3 if move == "hop" and n == 1 else 0)
        else:
            y = round(cy - py) + (n - 1)
        placed.append((img, round(cx - px), y))
    dx = max(max(-x, x + img.width - ref.width, 0) for img, x, y in placed)
    dy = max(max(-y, y + img.height - ref.height, 0) for img, x, y in placed)
    frames = []
    for img, x, y in placed:
        f = Image.new("RGBA", (ref.width + 2 * dx, ref.height + 2 * dy))
        f.paste(img, (x + dx, y + dy))
        frames.append(f)
    return frames


def step_cycle(img, floats=False):
    """Four frames of movement derived from one sprite: the fallback when it has no pose frames.

    A walker steps: neutral, front foot up, neutral, back foot up. On a step the body dips one
    pixel and the legs shorten by a row, and the lifted foot's half of the legs rises a pixel.
    A floater bobs a pixel up and down instead. The sprite faces right, so its front is the right.
    """
    w, h = img.size
    if floats:
        up, down = Image.new("RGBA", (w, h + 1)), Image.new("RGBA", (w, h + 1))
        up.paste(img, (0, 0))
        down.paste(img, (0, 1))
        return [up, up, down, down]
    legs = max(3, round(h * 0.22))
    top = h - legs
    steps = []
    for x0, x1 in ((w // 2, w), (0, w // 2)):  # the half whose foot lifts
        f = Image.new("RGBA", (w, h))
        f.paste(img.crop((0, top + 1, w, h)), (0, top + 1))  # legs, a row shorter
        f.paste(Image.new("RGBA", (x1 - x0, legs)), (x0, top))
        f.paste(img.crop((x0, top + 1, x1, h)), (x0, top))  # this foot, a pixel higher
        f.paste(img.crop((0, 0, w, top)), (0, 1))  # body, a pixel lower
        steps.append(f)
    return [img, steps[0], img, steps[1]]


def family(eid):
    if eid in CAST_OF:
        return CAST_OF[eid]
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
    cache, body = {}, {}

    def sprite(tid, h, box=False):
        """One frame at height h; box=True also caps the width at h (icons, projectiles)."""
        if (tid, h, box) not in cache:
            src = RAW / f"{tid}_s{picks.get(tid, 90)}.png"
            img = pixelize(src, h)
            if box and img.width > h:
                img = pixelize(src, max(1, h * img.height // img.width))
            cache[tid, h, box] = img
        return [cache[tid, h, box]]

    def variant(kind, wid):
        """wi_<id> (icon) or ws_<id> (projectile) when that weapon has its own render, else wp_<id>."""
        return f"{kind}_{wid}" if (RAW / f"{kind}_{wid}_s90.png").exists() else f"wp_{wid}"

    def moving(tid, h):
        if (tid, h, "cycle") not in cache:
            img, k = sprite(tid, h)[0], 1
            if img.height * 2 <= h:  # a coarse render: whole-number enlarge to its tier
                k = h // img.height
                img = img.resize((img.width * k, img.height * k), Image.NEAREST)
            src = RAW / f"{tid}_s{picks.get(tid, 90)}.png"
            shots = [src.with_name(f"{src.stem}_{p}.png") for p in "abc"]
            move = MOVE_OF.get(tid, "walk")
            if all(s.exists() for s in shots):
                poses = [pixelize_pose(s, src, h) for s in shots]
                if k > 1:
                    poses = [p.resize((p.width * k, p.height * k), Image.NEAREST) for p in poses]
                poses = [img if n in BAD_POSES.get(tid, "") else p for n, p in zip("abc", poses)]
                cache[tid, h, "cycle"] = pose_cycle(img, poses, move)
            else:
                cache[tid, h, "cycle"] = step_cycle(img, move in ("fly", "float"))
            body[tid, h] = img.size
        return cache[tid, h, "cycle"]

    items, sizes = {}, {}
    for cid, tid in HEROES.items():
        items[f"char:{cid}"] = moving(tid, 40)
        sizes[f"char:{cid}"] = body[tid, 40]
    for eid in list(g["enemies"]) + ["reaper"]:
        items[f"enemy:{eid}"] = moving(family(eid), enemy_height(eid))
        sizes[f"enemy:{eid}"] = body[family(eid), enemy_height(eid)]
    for k, tid in PICKUPS.items():
        items[f"pickup:{k}"] = sprite(tid, PICKUP_H.get(k, 14))
    for k, tid in LIGHTS.items():
        items[f"light:{k}"] = sprite(tid, 28)
    for wid in g["weapons"]:
        items[f"wicon:{wid}"] = sprite(variant("wi", wid), 16, box=True)
    for wid, size in WSPR.items():
        items[f"wspr:{wid}"] = sprite(variant("ws", wid), size, box=True)
    for wid, own in RINGS.items():
        base = items[f"wspr:{wid}"][0]
        items[f"wspr:{wid}"] = [base] + [recolour(base, CANDY[own], ramp)
                                         for name, ramp in CANDY.items() if name != own]
    for pid in g["passives"]:
        items[f"passive:{pid}"] = sprite(PASSIVES.get(pid, f"pa_{pid}"), 16, box=True)
    for aid in g["arcanas"]:
        card = sprite(f"ar_{aid}", CARD_H)[0]
        if card.height < CARD_H:  # a coarser render: enlarge it so every card is the same size
            card = card.resize((round(card.width * CARD_H / card.height), CARD_H), Image.NEAREST)
        items[f"arcana:{aid}"] = [card]
        items[f"arcana_icon:{aid}"] = sprite(f"ar_{aid}", 20)

    q = Image.new("P", (1, 1))
    colors = [tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in BASE + NEON]
    q.putpalette([v for c in colors for v in c] + [0] * 3 * (256 - len(colors)))
    # pack each distinct frame once: most keys share their frames with other keys
    frames = {id(f): f for fs in items.values() for f in fs}
    pages, rects = pack({str(n): [f] for n, f in frames.items()}, colors, q)
    index = {key: [rects[str(id(f))][0] for f in fs] for key, fs in items.items()}

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
    # "body": the size of the character inside frames that are padded for movement
    (OUT / "atlas.json").write_text(json.dumps({"palette": NEON, "sprites": index, "body": sizes}))
    fams = {}
    for eid in g["enemies"]:
        fams[family(eid)] = fams.get(family(eid), 0) + 1
    print(f"{len(index)} keys, {len(frames)} distinct frames, {len(pages)} pages")
    print("enemy families:", dict(sorted(fams.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
