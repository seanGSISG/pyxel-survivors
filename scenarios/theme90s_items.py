"""Scenario: 90s theme with a full loadout, for the themed item names, icons and projectiles
(press P for the pause list; the level-up menu shows names and descriptions)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "mad_forest", "art": "90s", "god": True, "minute": 5, "autopilot": True,
          "weapons": {"whip": 4, "king_bible": 6, "knife": 5, "axe": 4, "cross": 4, "runetracer": 4},
          "passives": {"spinach": 2, "wings": 1, "armor": 1, "clover": 1, "pummarola": 1, "empty_tome": 2}})
