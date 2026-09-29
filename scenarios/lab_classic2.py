"""Weapon lab group classic2."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["fire_wand:8", "garlic:8", "santa_water:8", "runetracer:8", "lightning_ring:8"])
