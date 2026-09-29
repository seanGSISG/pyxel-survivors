"""Queue sprite prompts through the Krea 2 sprite workflow on a local ComfyUI.

    uv run tools/sprite_gen/gen.py prompts.json --arm base --arm qpixel=1.0 --seed 90 --seed 91

An arm is `name` or `name=strength` for one style LoRA (base = no LoRA), so each
arm differs from the control by exactly one variable. Raw 1024px renders land in
tools/sprite_gen/raw/<arm>/<id>_s<seed>.png (gitignored).
"""

import argparse
import json
import pathlib
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
COMFY = "http://127.0.0.1:8188"
LORA_NODE = {"qpixel": "4", "cartoon": "5"}
STYLE = ("Bold dark outline, chunky readable silhouette, limited bright saturated palette, "
         "1990s arcade game sprite. A single subject centred on a flat solid magenta "
         "(#FF00FF) background with no shadow, no ground, no text and no border.")


def call(path, body=None):
    req = urllib.request.Request(COMFY + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def render(wf, prompt, seed, arm):
    g = json.loads(json.dumps(wf))
    g["6"]["inputs"]["text"] = f"{prompt} {STYLE}"
    g["9"]["inputs"]["seed"] = seed
    name, _, s = arm.partition("=")
    if name != "base":
        g[LORA_NODE[name]]["inputs"]["strength_model"] = float(s or 1.0)
    pid = call("/prompt", {"prompt": g})["prompt_id"]
    while not (h := call(f"/history/{pid}")):
        time.sleep(1)
    status = h[pid]["status"]
    if status.get("status_str") != "success":
        raise RuntimeError(f"{arm} s{seed}: {status}")
    img = h[pid]["outputs"]["11"]["images"][0]
    q = urllib.parse.urlencode({k: img[k] for k in ("filename", "subfolder", "type")})
    return urllib.request.urlopen(f"{COMFY}/view?{q}").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts")
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--seed", action="append", type=int, default=[])
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    wf = json.loads((HERE / "workflow_api.json").read_text())
    prompts = json.loads(pathlib.Path(a.prompts).read_text())
    for arm in a.arm or ["base"]:
        out = HERE / "raw" / arm.replace("=", "")
        out.mkdir(parents=True, exist_ok=True)
        for pid, prompt in prompts.items():
            if a.only and pid not in a.only:
                continue
            for seed in a.seed or [90]:
                t = time.time()
                (out / f"{pid}_s{seed}.png").write_bytes(render(wf, prompt, seed, arm))
                print(f"{arm:14} {pid:12} s{seed} {time.time() - t:5.1f}s", flush=True)


if __name__ == "__main__":
    main()
