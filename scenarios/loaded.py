"""Scenario: minute 12, god mode, a wide loadout to exercise every weapon."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "minute": 12, "god": True, "level": 30,
          "weapons": {"whip": 8, "magic_wand": 5, "axe": 4, "king_bible": 4,
                      "garlic": 4, "lightning_ring": 4},
          "passives": {"hollow_heart": 2, "candelabrador": 2}})
