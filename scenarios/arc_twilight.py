"""Scenario: Arcana T02_TWILIGHT test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T02_TWILIGHT"], "weapons": {"king_bible": 4, "runetracer": 4, "lightning_ring": 3}, "passives": {"skull_omaniac": 3}})
