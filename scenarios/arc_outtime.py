"""Scenario: Arcana T12_OUT_OF_TIME test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T12_OUT_OF_TIME"], "weapons": {"clock_lancet": 4, "magic_wand": 4}, "passives": {}})
