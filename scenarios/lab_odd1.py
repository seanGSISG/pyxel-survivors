"""Weapon lab group odd1."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["gatti_amari:8", "song_of_mana:8", "shadow_pinion:8", "clock_lancet:7", "laurel:7"])
