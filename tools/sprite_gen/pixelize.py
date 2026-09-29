"""Turn a 1024px magenta-backed render into a palette-locked game sprite.

    uv run --with pillow --with numpy tools/sprite_gen/pixelize.py raw/base/snapjaw_s90.png out.png --height 32

Steps: key out the magenta background, crop to the subject, snap every pixel
to the theme palette at full resolution, then downsample by taking the most
common colour in each block (a mode filter keeps outlines crisp where a box
average would smear them). Transparent pixels come out as alpha 0.
"""

import argparse

import numpy as np
from PIL import Image

# Pyxel's 16 base colours, then the 16-colour 90s extension (theme slots 22-37).
BASE = ["000000", "2B335F", "7E2072", "19959C", "8B4852", "395C98", "A9C1FF", "EEEEEE",
        "D4186C", "D38441", "E9C35B", "70C6A9", "7696DE", "A3A3A3", "FF9798", "EDC7B0"]
NEON = ["2E5A1C", "5E8C31", "9BC53D", "6B3E26", "B0703A", "FF2BD6", "00F0E0", "9D4EDD",
        "FFE14D", "FF7A1A", "1A1033", "3D2C5E", "5C5C70", "C4122F", "7A0F2A", "F5E6C8"]
PALETTE = np.array([[int(c[i:i + 2], 16) for i in (0, 2, 4)] for c in BASE + NEON], float)


def key_mask(rgb, tol=70, hole_tol=30):
    """True where the pixel is subject.

    Background is whatever connects to the border and sits within `tol` of the
    border's median colour, so a pink pog enclosed by its outline survives.
    Shadows the model casts on the backdrop count as background too.
    Enclosed pockets (between arm and body) count as background only when they
    are a near-exact match (`hole_tol`), which spares deliberate pinks.
    """
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    back = np.median(border, 0)
    dist = np.sqrt(((rgb - back) ** 2).sum(-1))
    # a cast shadow is the background, only darker: red and blue dimmed by the same factor
    k = rgb / np.maximum(back, 1)
    shadow = (np.abs(k[..., 0] - k[..., 2]) < 0.1) & (k[..., 0] > 0.4) & (k[..., 0] < 1.05) \
        & (rgb[..., 1] < back[1] + 25)
    near = (dist < tol) | shadow
    bg = np.zeros((h, w), bool)
    stack = [(y, x) for y in range(h) for x in (0, w - 1)] + [(y, x) for x in range(w) for y in (0, h - 1)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < h and 0 <= x < w and near[y, x] and not bg[y, x]:
            bg[y, x] = True
            stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    return ~(bg | (dist < hole_tol))


def snap(rgb):
    """Index of the nearest palette colour for every pixel."""
    d = ((rgb[..., None, :] - PALETTE) ** 2).sum(-1)
    return d.argmin(-1)


def _steps(rgb, axis):
    """Colour-step profile across one axis; it peaks on the cell borders."""
    step = np.abs(np.diff(rgb, axis=axis)).sum(-1).sum(1 - axis)
    return step - step.mean()


def period(step, lo=8, hi=80):
    """Fundamental period of a step profile.

    The first autocorrelation peak within 60% of the strongest wins: sparse
    sprites often correlate best at a multiple of the cell (48, 64 for 16).
    """
    ac = np.correlate(step, step, "full")[len(step) - 1:]
    top = ac[lo:hi].max()
    p = next(i for i in range(lo, hi) if ac[i] >= 0.6 * top and ac[i] >= ac[i - 1] and ac[i] >= ac[i + 1])
    a, b, c = ac[p - 1], ac[p], ac[p + 1]  # parabola through the peak refines it
    return p + 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else p


def phase(step, per):
    """Offset of the best-aligned comb of cell borders."""
    n = len(step)
    phases = np.arange(0, per, 0.5)
    score = [step[np.clip(np.round(np.arange(ph, n, per)).astype(int), 0, n - 1)].sum() for ph in phases]
    return phases[int(np.argmax(score))] + 1


def native(src):
    """Sample one colour per detected grid cell: the render at its own resolution.

    Cells are square, so one period (the finer of the two axes) serves both;
    each axis keeps its own phase.
    """
    rgb = np.asarray(Image.open(src).convert("RGB"), float)
    sx, sy = _steps(rgb, 1), _steps(rgb, 0)
    per = min(period(sx), period(sy))
    ox, oy = phase(sx, per), phase(sy, per)
    xs = np.arange(ox + per / 2 - per, rgb.shape[1], per)
    ys = np.arange(oy + per / 2 - per, rgb.shape[0], per)
    xs = xs[(xs >= 0) & (xs < rgb.shape[1])].astype(int)
    ys = ys[(ys >= 0) & (ys < rgb.shape[0])].astype(int)
    # median of the cell's central quarter resists anti-aliased borders
    r = max(1, int(per / 4))
    cells = np.array([[np.median(rgb[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].reshape(-1, 3), 0)
                       for x in xs] for y in ys])
    return cells, per


def pixelize(src, height):
    rgb, _ = native(src)
    mask = key_mask(rgb)
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb, mask = rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    idx = np.where(mask, snap(rgb), -1)  # -1 = transparent
    h, w = idx.shape
    th = min(height, h)  # never upscale; only shrink sprites taller than the cap
    tw = max(1, round(w * th / h))
    out = np.full((th, tw), -1)
    for ty in range(th):
        for tx in range(tw):
            cell = idx[ty * h // th:(ty + 1) * h // th, tx * w // tw:(tx + 1) * w // tw].ravel()
            vals, counts = np.unique(cell, return_counts=True)
            opaque = vals >= 0
            # keep the pixel if at least 40% of the block is subject
            if counts[opaque].sum() >= 0.4 * cell.size:
                out[ty, tx] = vals[opaque][counts[opaque].argmax()]
    img = np.zeros((th, tw, 4), np.uint8)
    img[out >= 0, :3] = PALETTE[out[out >= 0]].astype(np.uint8)
    img[out >= 0, 3] = 255
    return Image.fromarray(img, "RGBA")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--height", type=int, default=64)
    a = ap.parse_args()
    pixelize(a.src, a.height).save(a.dst)
