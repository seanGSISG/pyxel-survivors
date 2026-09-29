"""Scenario: Arcana T08_MAD_FOREST test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T08_MAD_FOREST"], "weapons": {"magic_wand": 4}, "passives": {}})
