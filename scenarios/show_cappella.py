"""Showcase: Cappella Magna (README footage, 90s theme)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 12, "stage": "cappella_magna", "art": "90s", "god": True,
          "autopilot": True, "minute": 14, "level": 35,
          "weapons": {"song_of_mana": 6, "pentagram": 4, "clock_lancet": 5, "cherry_bomb": 5}})
