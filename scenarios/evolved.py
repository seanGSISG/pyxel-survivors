"""Scenario: minute 16, god mode, all six slots evolved."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "minute": 16, "god": True, "level": 50,
          "weapons": {"whip": 1, "death_spiral": 1, "unholy_vespers": 1, "hellfire": 1,
                      "la_borra": 1, "thunder_loop": 1},
          "passives": {"hollow_heart": 5}})
