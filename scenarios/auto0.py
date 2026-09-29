"""Scenario: autopilot run with character 0 from 0:00 (balance check)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0, "autopilot": True})
