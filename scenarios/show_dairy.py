"""Showcase: Dairy Plant (README footage, 90s theme)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 3, "stage": "dairy_plant", "art": "90s", "god": True,
          "autopilot": True, "minute": 12, "level": 30,
          "weapons": {"runetracer": 6, "cross": 6, "fire_wand": 6, "bone": 5}})
