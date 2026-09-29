"""Scenario: Arcana T21_BLOODY test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T21_BLOODY"], "weapons": {"garlic": 4, "song_of_mana": 3}, "passives": {"duplicator": 2}})
