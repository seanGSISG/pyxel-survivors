"""Scenario: Arcana T05_CRASH test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T05_CRASH"], "weapons": {"magic_wand": 4, "knife": 4}, "passives": {}})
