"""Side-by-side sheet of style arms: one row per arm, one column per subject.

    uv run --with pillow --with numpy tools/sprite_gen/compare.py out.png --height 40 base qpixel1.0 cartoon1.0

Each cell shows the raw render (small) above the pixelized sprite at 4x and 1x
on the game's dark background, so styles are judged at the size they will play.
"""

import sys
import pathlib

from PIL import Image, ImageDraw

from pixelize import pixelize

HERE = pathlib.Path(__file__).parent
BG = (26, 16, 51, 255)
CELL, THUMB, ZOOM = 220, 140, 4


def main(dst, height, arms):
    subjects = sorted({p.stem for a in arms for p in (HERE / "raw" / a).glob("*.png")})
    sheet = Image.new("RGBA", (110 + CELL * len(subjects), 24 + CELL * len(arms)), (12, 8, 24, 255))
    d = ImageDraw.Draw(sheet)
    for c, s in enumerate(subjects):
        d.text((110 + c * CELL + 4, 6), s, fill=(230, 230, 230))
    for r, arm in enumerate(arms):
        y = 24 + r * CELL
        d.text((6, y + CELL // 2), arm, fill=(255, 43, 214))
        for c, s in enumerate(subjects):
            src = HERE / "raw" / arm / f"{s}.png"
            if not src.exists():
                continue
            x = 110 + c * CELL
            sheet.paste(Image.open(src).convert("RGBA").resize((THUMB // 2, THUMB // 2)), (x + 4, y + 4))
            spr = pixelize(src, height)
            tile = Image.new("RGBA", spr.size, BG)
            tile.alpha_composite(spr)
            big = tile.resize((spr.width * ZOOM, spr.height * ZOOM), Image.NEAREST)
            big.thumbnail((CELL - 8, CELL - THUMB // 2 - 12), Image.NEAREST)
            sheet.paste(big, (x + 4, y + THUMB // 2 + 8))
            sheet.paste(tile, (x + 4 + THUMB // 2 + 8, y + 4))  # 1x, as in game
            d.text((x + THUMB // 2 + 8, y + 4 + spr.height + 4), f"{spr.width}x{spr.height}", fill=(160, 160, 160))
    sheet.save(dst)


if __name__ == "__main__":
    dst, height, *arms = sys.argv[1:]
    main(dst, int(height.removeprefix("--height=")), arms)
