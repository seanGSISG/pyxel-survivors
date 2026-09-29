"""Scenario: 90s terrain for gallo_tower at minute 6 (autopilot, god mode)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "gallo_tower", "art": "90s", "god": True, "minute": 6,
          "autopilot": True, "weapons": {"whip": 3, "garlic": 2}})
