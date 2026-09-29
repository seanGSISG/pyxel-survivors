"""Seed-picking sheet: every subject's seeds side by side, pixelized at 3x.

    uv run --with pillow --with numpy tools/sprite_gen/picksheet.py raw/picks_heroes.png hero_ char_
    uv run --with pillow --with numpy tools/sprite_gen/picksheet.py raw/picks_icons.png --box 16 wp_ pa_

Arguments after the output path are id prefixes to include. --box N judges the
seeds at game size: pixelized to fit an N px box, as build_theme.py does for
icons and projectiles. Record the chosen seed per id in picks.json
({"hero_dash": 91}); unlisted ids use seed 90.
"""

import pathlib
import re
import sys

from PIL import Image, ImageDraw

from pixelize import pixelize

HERE = pathlib.Path(__file__).parent
RAW = HERE / "raw" / "qpixel0.5"
BG, ZOOM, CELL = (58, 74, 64, 255), 3, 150  # a mid tone: dark outlines and highlights both show


def main(dst, prefixes, box=0):
    runs = {}
    for p in sorted(RAW.glob("*.png")):
        m = re.match(r"(.+)_s(\d+)$", p.stem)
        if not m:  # a pose frame (pose.py), not a seed
            continue
        tid, seed = m.groups()
        if any(tid.startswith(x) for x in prefixes):
            runs.setdefault(tid, []).append((int(seed), p))
    cols = 4  # subjects per row, each with its seeds
    per = max(len(v) for v in runs.values())
    rows = -(-len(runs) // cols)
    sheet = Image.new("RGBA", (cols * per * CELL, rows * (CELL + 16)), (12, 8, 24, 255))
    d = ImageDraw.Draw(sheet)
    for i, (tid, seeds) in enumerate(runs.items()):
        x0, y0 = (i % cols) * per * CELL, (i // cols) * (CELL + 16)
        d.text((x0 + 4, y0 + 2), tid, fill=(230, 230, 230))
        for j, (seed, p) in enumerate(seeds):
            spr = pixelize(p, box or 40)
            if box and spr.width > box:
                spr = pixelize(p, max(1, box * spr.height // spr.width))
            tile = Image.new("RGBA", spr.size, BG)
            tile.alpha_composite(spr)
            zoom = max(ZOOM, (CELL - 8) // max(spr.size)) if box else ZOOM
            big = tile.resize((spr.width * zoom, spr.height * zoom), Image.NEAREST)
            big.thumbnail((CELL - 8, CELL - 8), Image.NEAREST)
            sheet.paste(big, (x0 + j * CELL + 4, y0 + 16))
            d.text((x0 + j * CELL + 4, y0 + 16 + big.height), f"s{seed}", fill=(255, 43, 214))
    sheet.save(dst)


if __name__ == "__main__":
    args = sys.argv[1:]
    size = int(args.pop(args.index("--box") + 1)) if "--box" in args else 0
    main(args[0], [a for a in args[1:] if a != "--box"], size)
