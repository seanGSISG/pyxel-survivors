"""Browser benchmark startup script (packaged by tools/build_web.py --bench).

Starts a minute-15 autopilot run with an evolved build and writes the measured
frame rate and enemy count into the page title every 3 seconds, e.g.
"fps 29.8 | enemies 312 | 15:08", so a browser driver can read it.
"""

import time

import main

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
          "minute": 15, "level": 45,
          "weapons": {"death_spiral": 1, "unholy_vespers": 1, "hellfire": 1, "la_borra": 1,
                      "thunder_loop": 1, "heaven_sword": 1},
          "passives": {"hollow_heart": 5, "spinach": 5}})
