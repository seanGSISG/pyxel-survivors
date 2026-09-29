"""Scenario: 90s theme menus, to check the themed display names (title, select, game over)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main
main.App({"art": "90s"})
