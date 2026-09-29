"""Showcase: the Late Fee arrives at 30:00 (README footage, 90s theme)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "mad_forest", "art": "90s", "god": True,
          "autopilot": True, "minute": 29.97, "level": 20,
          "weapons": {"whip": 2}})
