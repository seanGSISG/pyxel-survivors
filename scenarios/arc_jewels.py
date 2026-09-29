"""Scenario: Arcana T14_JEWELS test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T14_JEWELS"], "weapons": {"magic_wand": 6, "runetracer": 4}, "passives": {}})
