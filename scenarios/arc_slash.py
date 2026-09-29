"""Scenario: Arcana T16_SLASH test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T16_SLASH"], "weapons": {"knife": 5, "axe": 3}, "passives": {}})
