"""Re-pose picked sprites into movement frames with the Krea 2 identity-edit workflow.

    uv run tools/sprite_gen/pose.py hero_snapjaw mon_mall_zombie      # these ids
    uv run tools/sprite_gen/pose.py --prefix vil_ --missing           # every villain not done yet

The picked render of each id (seed from picks.json) is the reference image; the
edit model redraws the same character in each pose of POSES. Frames land next to
the render as raw/qpixel0.5/<id>_s<seed>_<pose>.png.

Experimental: build_theme.py does not use these frames yet (it derives its cycle
from the picked sprite). A first test kept the character identical and drew a real
stride, but the frames come out brighter than the source and both poses put the
same leg forward, so a whole cycle has to come from this script, prompts included.
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
        "same three-quarter view facing right, on the same flat solid magenta background. New pose: ")
POSES = {
    "walk": {
        "a": "mid stride walking, the front leg stepping far forward and the back leg pushed back, "
             "the arms swung the opposite way.",
        "b": "mid stride walking, the legs swapped: the other leg stepping far forward and the first "
             "leg pushed back, the arms swung the other way.",
    },
    "float": {
        "a": "hovering a little higher and leaning forward, wings or trailing parts swept upward.",
        "b": "hovering a little lower and leaning back, wings or trailing parts swept downward.",
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
    ap.add_argument("--float", nargs="*", default=[], help="ids that hover instead of walking")
    ap.add_argument("--missing", action="store_true", help="skip frames that already exist")
    ap.add_argument("--boost", type=float, default=4.0, help="reference lock (ref_boost)")
    ap.add_argument("--seed", type=int, default=90)
    a = ap.parse_args()
    wf = json.loads((HERE / "workflow_edit_api.json").read_text())
    picks = json.loads((HERE / "picks.json").read_text())
    prompts = json.loads((HERE / "theme90s_prompts.json").read_text())
    ids = [i for i in prompts if i in a.ids or any(i.startswith(p) for p in a.prefix)]
    for tid in ids:
        src = RAW / f"{tid}_s{picks.get(tid, 90)}.png"
        shutil.copy(src, COMFY_INPUT / f"pyxel90s_{src.name}")
        for pose, prompt in POSES["float" if tid in a.float else "walk"].items():
            dst = src.with_name(f"{src.stem}_{pose}.png")
            if a.missing and dst.exists():
                continue
            t = time.time()
            dst.write_bytes(render(wf, f"pyxel90s_{src.name}", prompt, a.seed, a.boost))
            print(f"{tid:22} {pose} {time.time() - t:5.1f}s", flush=True)


if __name__ == "__main__":
    main()
