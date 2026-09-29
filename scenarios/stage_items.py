"""Scenario: Mad Forest from 0:00 in god mode; walk north to collect the Hollow Heart stage item."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "stage": "mad_forest", "art": "90s", "god": True})
