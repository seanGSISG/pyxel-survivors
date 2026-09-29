"""Showcase: Gallo Tower (README footage, 90s theme)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 2, "stage": "gallo_tower", "art": "90s", "god": True,
          "autopilot": True, "minute": 9, "level": 25,
          "weapons": {"axe": 6, "knife": 6, "peachone": 5, "ebony_wings": 5}})
