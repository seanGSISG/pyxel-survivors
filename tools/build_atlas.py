"""Pack the wiki sprites the game uses into Pyxel-ready atlas pages.

Reads gamedata.json + wiki/sprites/manifest.json, restores native pixel size
(many wiki files are integer-upscaled), splits animated GIFs into frames,
quantises everything to one shared palette, and writes:

    wiki/atlas/page_N.png   256x256 RGB pages, transparent = #FF00FF
    wiki/atlas/atlas.json   {"palette": [...], "sprites": {key: [[page,x,y,w,h], ...]}}

Keys: enemy:<id>  char:<id>  wicon:<id>  wspr:<id>  passive:<id>  pickup:<kind>
      light:<kind>  arcana:<id>  arcana_icon:<id>

    uv run --with pillow tools/build_atlas.py
"""

import json
import pathlib
import re

from PIL import Image, ImageSequence

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPR = ROOT / "wiki" / "sprites"
OUT = ROOT / "wiki" / "atlas"
PAGE = 256
KEY = (255, 0, 255)
N_COLORS = 232  # palette slots left after 16 base + 5 terrain + key + spares

PICKUPS = {
    "gem": "Experience Gem", "gem_green": "Experience Gem-Green", "gem_red": "Experience Gem-Red",
    "chicken": "Floor Chicken", "coin": "Gold Coin", "coinbag": "Coin Bag",
    "richbag": "Rich Coin Bag", "rosary": "Rosary", "clock": "Orologion", "vacuum": "Vacuum",
    "nduja": "Nduja Fritta Tanto", "clover": "Little Clover", "chest": "Treasure Chest",
    "chest_evo": "Treasure Chest 2", "chest_arcana": "Treasure Chest 5",
}
LIGHTS = {"brazier": "Normal brazier", "candelabrone": "Candelabrone", "lantern": "Lantern",
          "lampost": "Lampost", "blue_brazier": "Blue brazier"}
# Max frame height per key kind; larger art (non-integer wiki upscales) is shrunk.
MAX_DIM = {"arcana": 96, "char": 40, "enemy": 64, "wspr": 28, "wicon": 16, "passive": 16,
           "pickup": 16, "light": 32, "arcana_icon": 16}


def find(manifest, *names):
    """Path of the first existing file among candidate wiki file names."""
    for n in names:
        if not n:
            continue
        for key in (f"File:{n}", f"File:{n.replace('_', ' ')}"):
            if key in manifest:
                p = SPR / manifest[key]
                if p.exists():
                    return p
    return None


def unscale(img):
    """Undo integer nearest-neighbour upscaling (largest factor that round-trips)."""
    w, h = img.size
    for s in range(8, 1, -1):
        if w % s or h % s:
            continue
        small = img.resize((w // s, h // s), Image.NEAREST)
        if small.resize((w, h), Image.NEAREST).tobytes() == img.tobytes():
            return small
    return img


def frames_of(path):
    im = Image.open(path)
    out = []
    for fr in ImageSequence.Iterator(im):
        f = fr.convert("RGBA")
        out.append(f)
        if len(out) >= 8:
            break
    return out


def crop_frames(frames):
    """Crop all frames to their shared opaque bounding box (keeps alignment)."""
    box = None
    for f in frames:
        b = f.getchannel("A").point(lambda a: 255 if a > 127 else 0).getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                         max(box[2], b[2]), max(box[3], b[3]))
    return [f.crop(box) for f in frames] if box else frames


def load_sprite(path, max_h=None):
    fr = frames_of(path)
    fr = [unscale(f) for f in fr]
    fr = crop_frames(fr)
    big = max(fr[0].height, fr[0].width)
    if max_h and big > max_h:
        k = max_h / big
        fr = [f.resize((max(1, round(f.width * k)), max(1, round(f.height * k))), Image.NEAREST)
              for f in fr]
    return fr


def collect(g, manifest):
    items = {}

    def add(key, *names, max_h=None):
        p = find(manifest, *names)
        if p:
            items[key] = load_sprite(p, max_h or MAX_DIM.get(key.split(":")[0]))

    for eid, e in g["enemies"].items():
        base = re.sub(r"^Sprite-|\.png$", "", e["image"]) if e["image"] else e["name"]
        add(f"enemy:{eid}", f"Animated-{base}.gif", f"Sprite-{base}.png",
            f"Animated-{e['page']}.gif", f"Sprite-{e['page']}.png")
    add("enemy:reaper", "Animated-The Reaper.gif", "Sprite-The Reaper.png")
    add("char:zi_assunta_belpaese", "Sprite-Zi'Assunta Belpaese.png", "Animated-Zi'Assunta Belpaese.gif",
        "Sprite-Zi Assunta Belpaese.png")
    for cid, c in g["characters"].items():
        add(f"char:{cid}", f"Animated-{c['name']}.gif", f"Sprite-{c['name']}.png")
    for wid, w in g["weapons"].items():
        add(f"wicon:{wid}", f"Icon-{w['name']}.png", f"Sprite-{w['name']}.png")
        add(f"wspr:{wid}", f"Sprite-{w['name']}.png")
    for pid, p in g["passives"].items():
        add(f"passive:{pid}", p["sprite"], p["icon"], f"Sprite-{p['name']}.png")
    for k, n in PICKUPS.items():
        add(f"pickup:{k}", f"Sprite-{n}.png")
    for k, n in LIGHTS.items():
        add(f"light:{k}", f"{n}.gif", f"Animated-{n}.gif")
    for aid, a in g["arcanas"].items():
        add(f"arcana:{aid}", f"Sprite-{a['name']}.png", max_h=MAX_DIM["arcana"])
        add(f"arcana_icon:{aid}", re.sub(r"^\[\[File:|\]\]$", "", a["icon"]),
            f"Icon-{a['name'].split(' (')[0]}.png")
    return items


def build_palette(items):
    """Quantise all opaque pixels of all frames to one shared palette."""
    pix = []
    for frames in items.values():
        for f in frames:
            data = f.get_flattened_data() if hasattr(f, 'get_flattened_data') else f.getdata()
            pix.extend(p[:3] for p in data if p[3] > 127)
    side = int(len(pix) ** 0.5) + 1
    mosaic = Image.new("RGB", (side, side), pix[0])
    mosaic.putdata(pix + [pix[0]] * (side * side - len(pix)))
    q = mosaic.quantize(colors=N_COLORS, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: N_COLORS * 3]
    colors = [tuple(pal[i:i + 3]) for i in range(0, len(pal), 3)]
    return [c if c != KEY else (254, 0, 254) for c in colors], q


def pack(items, colors, qref):
    """Shelf-pack frames into pages, remapping pixels onto the palette."""
    pages, cur, x, y, shelf = [], None, PAGE, PAGE, 0
    index = {}
    for key in sorted(items, key=lambda k: -items[k][0].height):
        rects = []
        for f in items[key]:
            w, h = f.size
            if w > PAGE or h > PAGE:
                continue
            if x + w > PAGE:
                x, y, shelf = 0, y + shelf, 0
            if cur is None or y + h > PAGE:
                cur = Image.new("RGB", (PAGE, PAGE), KEY)
                pages.append(cur)
                x, y, shelf = 0, 0, 0
            rgb = f.convert("RGB").quantize(palette=qref, dither=Image.Dither.NONE).convert("RGB")
            mask = f.getchannel("A").point(lambda a: 255 if a > 127 else 0)
            cur.paste(rgb, (x, y), mask)
            rects.append([len(pages) - 1, x, y, w, h])
            x += w + 1
            shelf = max(shelf, h + 1)
        if rects:
            index[key] = rects
    return pages, index


def main():
    g = json.loads((ROOT / "gamedata.json").read_text())
    manifest = json.loads((SPR / "manifest.json").read_text())
    items = collect(g, manifest)
    colors, q = build_palette(items)
    pages, index = pack(items, colors, q)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("page_*.png"):  # includes silhouettes
        old.unlink()
    for i, p in enumerate(pages):
        p.save(OUT / f"page_{i}.png")
        # silhouette page (for hit flash / freeze tint): opaque -> Pyxel colour 7
        sil = Image.new("RGB", p.size, KEY)
        opaque = Image.new("L", p.size, 0)
        opaque.putdata([0 if px == KEY else 255 for px in p.getdata()])
        sil.paste((238, 238, 238), (0, 0), opaque)
        sil.save(OUT / f"page_{i}_s.png")
    (OUT / "atlas.json").write_text(json.dumps(
        {"palette": ["%02x%02x%02x" % c for c in colors], "sprites": index}))
    kinds = {}
    for k in index:
        kinds[k.split(":")[0]] = kinds.get(k.split(":")[0], 0) + 1
    print(f"{len(index)} sprites on {len(pages)} pages, {len(colors)} colours: {kinds}")
    missing = [f"enemy:{e}" for e in g["enemies"] if f"enemy:{e}" not in index]
    missing += [f"char:{c}" for c in g["characters"] if f"char:{c}" not in index]
    missing += [f"wicon:{w}" for w in g["weapons"] if f"wicon:{w}" not in index]
    if missing:
        print("missing:", missing)


if __name__ == "__main__":
    main()
