"""Scenario: 90s theme, hero Snapjaw on mad_forest at minute 8 (theme sprites in play)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "mad_forest", "art": "90s", "god": True, "minute": 8,
          "autopilot": True, "weapons": {"whip": 3, "garlic": 2}})
