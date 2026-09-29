"""Re-pose picked sprites into movement frames with the Krea 2 identity-edit workflow.

    uv run tools/sprite_gen/pose.py hero_snapjaw mon_mall_zombie      # these ids
    uv run tools/sprite_gen/pose.py --prefix vil_ --missing           # every villain not done yet
    uv run tools/sprite_gen/pose.py --cast --missing                  # everything the game draws

The picked render of each id (seed from picks.json) is the reference image; the
edit model redraws the same character in each pose of POSES. Frames land next to
the render as raw/qpixel0.5/<id>_s<seed>_<pose>.png.

The edit model renders a little brighter than its source and sometimes draws a
creature a new body; build_theme.py matches the colours (pixelize_pose), drops a
pose whose size is far off (POSE_AREA) and skips the ones listed in BAD_POSES.
"""

import argparse
import json
import pathlib
import shutil
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
RAW = HERE / "raw" / "qpixel0.5"
COMFY = "http://127.0.0.1:8188"
COMFY_INPUT = pathlib.Path.home() / "comfy" / "ComfyUI" / "input"
KEEP = ("Redraw the character from the image in a new pose. Keep the exact same character, the same "
        "pixel art style, the same colours, outfit and held items, the same size in the frame and the "
        "same three-quarter view facing right, on the same flat solid magenta background with no "
        "shadow. New pose: ")
# How each design moves. A design not listed walks. build_theme.py plays the picked sprite and
# then poses a, b, c in order, so b is the in-between of a and c.
MOVES = {
    "fly": ["mon_pizza_bat", "mon_gargoyle"],
    "float": ["mon_vhs_ghost", "mon_crt_head", "mon_slime_jelly", "mon_dialup_demon", "mon_late_fee",
              "mon_glutton_ghost", "mon_eyeball_orb", "mon_squid", "mon_thwomper", "mon_whirl_devil",
              "vil_dr_yolk", "vil_sea_witch", "char_couch"],
    "hop": ["mon_toxic_ooze", "mon_chattering_teeth", "mon_slinky_snake", "mon_grass_pot",
            "mon_tomato", "mon_clip", "mon_sack", "mon_arcade_mimic", "mon_sandworm",
            "mon_beanbag_bear", "mon_wheel_bug", "mon_bomb", "mon_shroom"],
}
MOVE_OF = {tid: move for move, tids in MOVES.items() for tid in tids}
POSES = {
    "walk": {
        "a": "walking, caught mid step in a long stride, the leg nearest the viewer stretched forward "
             "with its heel down and the far leg stretched back behind, arms swinging.",
        "b": "walking, caught mid step balancing on one straight leg with the other knee lifted high "
             "in front, body upright, arms swinging the other way.",
        "c": "walking, caught mid step in a long stride, the far leg stretched forward and the leg "
             "nearest the viewer stretched back behind with its heel lifted, arms swinging.",
    },
    "fly": {
        "a": "flying with both wings raised high above its body.",
        "b": "flying with both wings spread straight out to the sides.",
        "c": "flying with both wings swept down below its body.",
    },
    "float": {
        "a": "drifting forward, tilted forward, its trailing parts swept back behind it.",
        "b": "hovering upright, its trailing parts hanging straight down and curling.",
        "c": "drifting, tilted back, its trailing parts swung forward underneath it.",
    },
    "hop": {
        "a": "squashed down low and wide, flattened against the ground, about to jump.",
        "b": "stretched tall and thin in mid air at the top of a hop, well clear of the ground.",
        "c": "landing, slightly squashed and leaning forward.",
    },
}


def call(path, body=None):
    req = urllib.request.Request(COMFY + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def render(wf, image, prompt, seed, boost):
    g = json.loads(json.dumps(wf))
    g["6"]["inputs"]["image"] = image
    g["8"]["inputs"]["ref_boost"] = boost
    g["9"]["inputs"]["prompt"] = KEEP + prompt
    g["12"]["inputs"]["seed"] = seed
    pid = call("/prompt", {"prompt": g})["prompt_id"]
    while not (h := call(f"/history/{pid}")):
        time.sleep(1)
    status = h[pid]["status"]
    if status.get("status_str") != "success":
        raise RuntimeError(f"{image}: {status}")
    img = h[pid]["outputs"]["14"]["images"][0]
    q = urllib.parse.urlencode({k: img[k] for k in ("filename", "subfolder", "type")})
    return urllib.request.urlopen(f"{COMFY}/view?{q}").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--prefix", action="append", default=[])
    ap.add_argument("--missing", action="store_true", help="skip frames that already exist")
    ap.add_argument("--cast", action="store_true", help="every character and enemy design")
    ap.add_argument("--boost", type=float, default=4.0, help="reference lock (ref_boost)")
    ap.add_argument("--seed", type=int, default=90)
    a = ap.parse_args()
    wf = json.loads((HERE / "workflow_edit_api.json").read_text())
    picks = json.loads((HERE / "picks.json").read_text())
    prompts = json.loads((HERE / "theme90s_prompts.json").read_text())
    ids = [i for i in prompts if i in a.ids or any(i.startswith(p) for p in a.prefix)
           or (a.cast and i.startswith(("hero_", "char_", "mon_", "vil_")))]
    for tid in ids:
        src = RAW / f"{tid}_s{picks.get(tid, 90)}.png"
        shutil.copy(src, COMFY_INPUT / f"pyxel90s_{src.name}")
        for pose, prompt in POSES[MOVE_OF.get(tid, "walk")].items():
            dst = src.with_name(f"{src.stem}_{pose}.png")
            if a.missing and dst.exists():
                continue
            t = time.time()
            dst.write_bytes(render(wf, f"pyxel90s_{src.name}", prompt, a.seed, a.boost))
            print(f"{tid:22} {MOVE_OF.get(tid, 'walk'):5} {pose} {time.time() - t:5.1f}s", flush=True)


if __name__ == "__main__":
    main()
