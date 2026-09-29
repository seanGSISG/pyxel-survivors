"""Scenario: Arcana T00_KILLER test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T00_KILLER"], "weapons": {"magic_wand": 4}, "passives": {"crown": 3}})
