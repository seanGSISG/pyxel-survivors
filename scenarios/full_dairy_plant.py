"""Scenario: full 30-minute god-mode autopilot run on dairy_plant (crash/coverage check)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "dairy_plant", "god": True, "autopilot": True})
