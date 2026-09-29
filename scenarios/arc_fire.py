"""Scenario: Arcana T19_FIRE test."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "god": True, "minute": 5, "level": 20, "arcanas": ["T19_FIRE"], "weapons": {"fire_wand": 4, "phiera_der_tuphello": 3}, "passives": {"armor": 2}})
