"""Seed-picking sheet: every subject's seeds side by side, pixelized at 3x.

    uv run --with pillow --with numpy tools/sprite_gen/picksheet.py raw/picks_heroes.png hero_ char_

Arguments after the output path are id prefixes to include. Record the chosen
seed per id in picks.json ({"hero_dash": 91}); unlisted ids use seed 90.
"""

import pathlib
import re
import sys

from PIL import Image, ImageDraw

from pixelize import pixelize

HERE = pathlib.Path(__file__).parent
RAW = HERE / "raw" / "qpixel0.5"
BG, ZOOM, CELL = (26, 16, 51, 255), 3, 150


def main(dst, prefixes):
    runs = {}
    for p in sorted(RAW.glob("*.png")):
        tid, seed = re.match(r"(.+)_s(\d+)$", p.stem).groups()
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
            spr = pixelize(p, 40)
            tile = Image.new("RGBA", spr.size, BG)
            tile.alpha_composite(spr)
            big = tile.resize((spr.width * ZOOM, spr.height * ZOOM), Image.NEAREST)
            big.thumbnail((CELL - 8, CELL - 8), Image.NEAREST)
            sheet.paste(big, (x0 + j * CELL + 4, y0 + 16))
            d.text((x0 + j * CELL + 4, y0 + 16 + big.height), f"s{seed}", fill=(255, 43, 214))
    sheet.save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
