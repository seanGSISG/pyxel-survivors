"""Preview atlas sprites on a grass background (checks palette + transparency).

Shows enemies, characters, items and arcana cards in a grid, animating frames.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pyxel

import art
import icons
import sprites

GROUPS = sys.argv[1:] or ["enemy", "char", "pickup", "wicon", "passive", "light", "arcana"]


class Preview:
    def __init__(self):
        pyxel.init(480, 270, title="atlas")
        pyxel.colors.extend([0x1E3D22, 0x26502A, 0x33662F, 0x173019, 0x4A7A3A])
        sprites.load()
        icons.load()
        print("mode:", art.init(os.environ.get("ART", "wiki")))
        # one screen per group, advancing every 10 frames
        self.pages = [[k for k in art._index if k.split(":")[0] == g] for g in GROUPS]
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(16)
        x, y, row = 4, 4, 0
        keys = self.pages[(pyxel.frame_count // 10) % len(self.pages)]
        for k in sorted(keys):
            w, h = art.size(k)
            if x + w > 476:
                x, y, row = 4, y + row + 2, 0
            if y + h > 270:
                break
            art.draw(k, x + w / 2, y + h / 2, pyxel.frame_count // 6)
            x += w + 2
            row = max(row, h)


Preview()
