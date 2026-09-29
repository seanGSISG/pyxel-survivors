"""Scenario: skip menus, Antonio at 0:00."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"char": 0})
