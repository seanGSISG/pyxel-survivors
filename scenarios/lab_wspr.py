"""Show all wspr:* atlas sprites with their weapon ids (lab reference sheet)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pyxel
import art, icons, sprites


class Sheet:
    def __init__(self):
        pyxel.init(480, 270)
        pyxel.colors.extend([0x1E3D22, 0x26502A, 0x33662F, 0x173019, 0x4A7A3A])
        sprites.load(); icons.load(); art.init()
        self.keys = sorted(k for k in art._index if k.startswith("wspr:"))
        pyxel.run(lambda: None, self.draw)

    def draw(self):
        pyxel.cls(16)
        for i, k in enumerate(self.keys):
            x, y = 4 + (i % 10) * 47, 4 + (i // 10) * 53
            art.draw(k, x + 22, y + 18)
            pyxel.text(x, y + 40, k[5:15], 7)


Sheet()
