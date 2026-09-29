"""Browser benchmark startup script (packaged by tools/build_web.py --bench).

Starts a minute-20 god-mode run with one Whip, so the horde piles up (worst case), and writes the measured
frame rate and enemy count into the page title every 3 seconds, e.g.
"fps 29.8 | enemies 312 | 15:08", so a browser driver can read it.
"""

import time

import pyxel

import main

# silent: a benchmark tab must not play music through the tester's speakers
pyxel.play = pyxel.playm = lambda *a, **k: None

try:
    import js  # Pyodide's bridge to the page
except ImportError:
    js = None

_update = main.App.update
_t = [time.perf_counter(), 0]


def update(self):
    _update(self)
    _t[1] += 1
    now = time.perf_counter()
    if now - _t[0] >= 3:
        fps = _t[1] / (now - _t[0])
        n = len(getattr(self, "enemies", []))
        msg = f"fps {fps:.1f} | enemies {n} | {int(self.t // 1800):02d}:{int(self.t // 30 % 60):02d}"
        print(msg)
        if js:
            js.document.title = msg
        _t[0], _t[1] = now, 0


main.App.update = update
main.App({"char": 0, "stage": "mad_forest", "art": "90s", "god": True, "autopilot": True,
          "minute": 20, "level": 10, "weapons": {"whip": 1}})
