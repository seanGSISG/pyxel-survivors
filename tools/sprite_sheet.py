"""Preview every sprite at 2x on a grass-coloured background."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pyxel

import sprites


class Sheet:
    def __init__(self):
        pyxel.init(256, 160, title="sprites")
        sprites.load()
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(3)
        for i, name in enumerate(sprites.POS):
            x, y = 20 + (i % 8) * 30, 18 + (i // 8) * 36
            sprites.draw(name, x, y, scale=2)


Sheet()
