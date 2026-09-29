"""Showcase: the first seconds of Dairy Plant, 90s theme (README footage).

A small director replaces the autopilot's steering: whip the nearest starting
light source, grab what it drops, then walk to the Armor stage item two
tilesets northeast. Level-ups are still auto-picked by the autopilot.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main


def director(self):
    p = self.p
    if self.t < 20:
        return 0.0, 0.0
    lights = [e for e in self.enemies if e.prop and not e.dead]
    drops = [it for it in self.pickups if it.kind not in ("gem", "chest") and not it.kind.startswith("item:")]
    items = [it for it in self.pickups if it.kind == "item:armor"]
    if drops:
        tx, ty = min(((it.x, it.y) for it in drops), key=lambda q: math.dist(q, (p.x, p.y)))
    elif lights and not getattr(self, "broke", False):
        e = min(lights, key=lambda e: math.dist((e.x, e.y), (p.x, p.y)))
        tx, ty = e.x - 40, e.y  # stand left of it so the Whip's slash lands
        if math.dist((tx, ty), (p.x, p.y)) < 6:
            p.face_x = 1
            return 0.0, 0.0
    elif items:
        tx, ty = items[0].x, items[0].y
    else:
        return 0.0, 0.0
    dx, dy = tx - p.x, ty - p.y
    d = math.hypot(dx, dy) or 1
    return dx / d, dy / d


_collect = main.App.collect


def collect(self, it):
    if it.kind != "gem":
        self.broke = True
        self.first_drop = getattr(self, "first_drop", None) or it.kind
    _collect(self, it)


main.App.autopilot = director
main.App.collect = collect
main.App({"char": 0, "stage": "dairy_plant", "art": "90s", "god": True, "autopilot": True})
