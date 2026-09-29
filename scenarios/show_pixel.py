"""Showcase: the built-in 16-colour pixel-art mode (README footage, pixel-art mode)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 4, "stage": "gallo_tower", "art": "pixel", "god": True,
          "autopilot": True, "minute": 8, "level": 25,
          "weapons": {"peachone": 5, "clock_lancet": 4, "song_of_mana": 4, "cherry_bomb": 4}})
