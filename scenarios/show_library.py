"""Showcase: Inlaid Library corridor (README footage, 90s theme)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 1, "stage": "inlaid_library", "art": "90s", "god": True,
          "autopilot": True, "minute": 10, "level": 25,
          "weapons": {"king_bible": 6, "magic_wand": 6, "lightning_ring": 5, "santa_water": 5}})
