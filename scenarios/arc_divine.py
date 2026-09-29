"""Scenario: Arcana T09_DIVINE test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T09_DIVINE"], "weapons": {"cross": 4, "garlic": 4}, "passives": {"armor": 5}})
