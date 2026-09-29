"""Weapon lab: 300 enemies, 12 heavy weapons (performance check)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import weapon_lab
weapon_lab.Lab(["death_spiral", "unholy_vespers", "hellfire", "soul_eater", "la_borra", "thunder_loop",
                "vandalier", "phieraggi", "mannajja", "tri_bracelet:6", "thousand_edge", "la_robba:8"],
               n_enemies=300)
