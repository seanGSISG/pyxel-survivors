"""Scenario: maxed Whip + Hollow Heart, walk right into an evolution chest."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "chest": True, "weapons": {"whip": 8},
          "passives": {"hollow_heart": 1}})
