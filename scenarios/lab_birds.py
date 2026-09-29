"""Weapon lab group birds."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["peachone:8", "ebony_wings:8", "phiera_der_tuphello:8", "eight_the_sparrow:8"])
