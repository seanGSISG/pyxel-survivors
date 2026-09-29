"""Scenario: atlas preview of the 90s theme (chars, enemies, pickups, lights)."""
import os, sys
os.environ["ART"] = "90s"
sys.argv = [sys.argv[0], "char", "enemy", "pickup", "light"]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import atlas_preview  # noqa: E402,F401  (runs on import)
