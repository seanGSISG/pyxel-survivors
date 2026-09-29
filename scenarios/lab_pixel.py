"""Weapon lab in pixel-art mode (procedural fallbacks)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["knife:8", "axe:8", "peachone:8", "gatti_amari:8", "bone:8", "cherry_bomb:8",
                "carrello:8", "celestial_dusting:8", "la_robba:8", "death_spiral", "shadow_pinion:8"],
               art_prefer="pixel")
