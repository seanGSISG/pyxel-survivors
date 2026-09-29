"""Weapon lab group evo1."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["bloody_tear", "holy_wand", "thousand_edge", "death_spiral", "heaven_sword", "unholy_vespers"])
