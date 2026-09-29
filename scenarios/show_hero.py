"""Showcase: evolved build at minute 15 on Mad Forest (README footage, 90s theme)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "mad_forest", "art": "90s", "god": True, "autopilot": True,
          "minute": 15, "level": 45,
          "weapons": {"death_spiral": 1, "unholy_vespers": 1, "hellfire": 1, "la_borra": 1,
                      "thunder_loop": 1, "heaven_sword": 1},
          "passives": {"hollow_heart": 5, "spinach": 5}})
