"""Weapon lab group evo3."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["vandalier", "phieraggi", "vicious_hunger", "mannajja", "valkyrie_turner"])
