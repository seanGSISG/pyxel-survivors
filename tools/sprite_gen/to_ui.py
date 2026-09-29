"""Write the sprite workflow in ComfyUI UI format (for opening in the browser).

    uv run tools/sprite_gen/to_ui.py ~/comfy/ComfyUI/user/default/workflows/Pyxel90s-Sprite-Krea2.json

gen.py drives workflow_api.json headlessly; this is the same graph laid out for
the editor. Widget order follows each node's /object_info definition.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from gen import STYLE  # noqa: E402
WIDGETS = {
    "UNETLoader": ["unet_name", "weight_dtype"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "VAELoader": ["vae_name"],
    "LoraLoaderModelOnly": ["lora_name", "strength_model"],
    "CLIPTextEncode": ["text"],
    "EmptyLatentImage": ["width", "height", "batch_size"],
    "KSampler": ["seed", None, "steps", "cfg", "sampler_name", "scheduler", "denoise"],
    "VAEDecode": [],
    "SaveImage": ["filename_prefix"],
}
OUTPUTS = {
    "UNETLoader": [("MODEL", "MODEL")], "CLIPLoader": [("CLIP", "CLIP")], "VAELoader": [("VAE", "VAE")],
    "LoraLoaderModelOnly": [("MODEL", "MODEL")], "CLIPTextEncode": [("CONDITIONING", "CONDITIONING")],
    "EmptyLatentImage": [("LATENT", "LATENT")], "KSampler": [("LATENT", "LATENT")],
    "VAEDecode": [("IMAGE", "IMAGE")], "SaveImage": [],
}
POS = {"1": (0, 0), "2": (0, 140), "3": (0, 290), "4": (380, 0), "5": (380, 140), "6": (380, 300),
       "7": (380, 560), "8": (380, 700), "9": (820, 0), "10": (1180, 0), "11": (1180, 120)}
NOTE = ("Pyxel Survivors 90s theme sprites (pyxel-survivors/tools/sprite_gen).\n"
        "Stock Krea 2 turbo; QPixel at 0.5 is the chosen style, 90s Flat Cartoon slot is off.\n"
        "Prompt: describe ONE subject facing right, then keep the style suffix: flat solid magenta "
        "#FF00FF background, no shadow/ground/text. CFG 1 = negative inert.\n"
        "Headless: uv run tools/sprite_gen/gen.py <prompts.json> --arm qpixel=0.5")


def main(dst):
    g = json.loads((HERE / "workflow_api.json").read_text())
    g["4"]["inputs"]["strength_model"] = 0.5  # the locked style
    hero = json.loads((HERE / "theme90s_prompts.json").read_text())["hero_snapjaw"]
    g["6"]["inputs"]["text"] = f"{hero} {STYLE}"
    nodes, links = [], []
    out_links = {}
    for nid, n in g.items():
        for name, v in n["inputs"].items():
            if isinstance(v, list):
                links.append([len(links) + 1, int(v[0]), v[1], int(nid), name])
                out_links.setdefault((v[0], v[1]), []).append(len(links))
    for nid, n in g.items():
        ct = n["class_type"]
        inputs = []
        for lid, src, slot, dst_n, name in links:
            if str(dst_n) == nid:
                typ = OUTPUTS[g[str(src)]["class_type"]][slot][1]
                inputs.append({"name": name, "type": typ, "link": lid})
        widgets = [n["inputs"].get(w, "fixed") if w else "fixed" for w in WIDGETS[ct]]
        nodes.append({
            "id": int(nid), "type": ct, "pos": list(POS[nid]), "size": [340, 100 if ct != "CLIPTextEncode" else 220],
            "flags": {}, "order": int(nid), "mode": 0, "inputs": inputs,
            "outputs": [{"name": nm, "type": t, "links": out_links.get((nid, i), []), "slot_index": i}
                        for i, (nm, t) in enumerate(OUTPUTS[ct])],
            "title": n.get("_meta", {}).get("title", ct), "properties": {"Node name for S&R": ct},
            "widgets_values": widgets,
        })
    nodes.append({"id": 99, "type": "Note", "pos": [820, 300], "size": [420, 200], "flags": {},
                  "order": 99, "mode": 0, "inputs": [], "outputs": [], "title": "README",
                  "properties": {}, "widgets_values": [NOTE]})
    typed = [[lid, src, slot, dst_n, [i["name"] for i in next(x for x in nodes if x["id"] == dst_n)["inputs"]].index(name),
              OUTPUTS[g[str(src)]["class_type"]][slot][1]] for lid, src, slot, dst_n, name in links]
    wf = {"last_node_id": 99, "last_link_id": len(links), "nodes": nodes, "links": typed,
          "groups": [], "config": {}, "extra": {}, "version": 0.4}
    pathlib.Path(dst).expanduser().write_text(json.dumps(wf, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
