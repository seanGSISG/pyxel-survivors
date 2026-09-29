"""Weapon lab group classic1."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["whip:8", "magic_wand:8", "knife:8", "axe:8", "cross:8", "king_bible:8"])
