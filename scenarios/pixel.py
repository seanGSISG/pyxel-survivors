"""Scenario: forced pixel-art mode with a mixed loadout (art fallback check)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 4, "stage": "gallo_tower", "art": "pixel", "god": True, "minute": 8,
          "weapons": {"peachone": 3, "clock_lancet": 2, "song_of_mana": 2, "cherry_bomb": 2},
          "passives": {"spinach": 2, "wings": 1}})
