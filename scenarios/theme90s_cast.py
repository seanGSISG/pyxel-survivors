"""Scenario: every distinct 90s enemy design once, at its largest size, cycling its movement
frames. Set CAST_GROUPS (e.g. "wicon,passive,wspr,arcana_icon,arcana") to sheet other keys."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pyxel
import art, icons, sprites

GROUPS = os.environ.get("CAST_GROUPS", "enemy").split(",")


class Sheet:
    def __init__(self):
        pyxel.init(480, 270, title="cast")
        pyxel.colors.extend([0x3A4A40, 0x26502A, 0x33662F, 0x173019, 0x4A7A3A])
        sprites.load(); icons.load(); art.init("90s")
        best = {}  # design (its first frame's rect) -> largest key using it
        for k, rects in art._index.items():
            if k.split(":")[0] in GROUPS:
                design = tuple(rects[0][:3]) if GROUPS != ["enemy"] else self.design(k)
                if design not in best or rects[0][4] > art._index[best[design]][0][4]:
                    best[design] = k
        self.keys = sorted(best.values(), key=lambda k: (GROUPS.index(k.split(":")[0]), -art.size(k)[1], k))
        pyxel.run(lambda: None, self.draw)

    @staticmethod
    def design(key):
        """Enemy sprites of one design differ only in size: group them by their colours."""
        page, u, v, w, h = art._index[key][0]
        img = art._pages[page]
        return tuple(sorted({img.pget(u + x, v + y) for x in range(0, w, 3) for y in range(0, h, 3)}))

    def draw(self):
        pyxel.cls(16)
        x, y, row = 3, 3, 0
        for k in self.keys:
            w, h = art.size(k)
            if x + w > 477:
                x, y, row = 3, y + row + 2, 0
            if y + h > 270:
                break
            art.draw(k, x + w / 2, y + h / 2, pyxel.frame_count // 6)
            x += w + 2
            row = max(row, h)


Sheet()
