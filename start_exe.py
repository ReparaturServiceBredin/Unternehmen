"""Einstiegspunkt für die EXE (PyInstaller)."""
import multiprocessing
import sys

from rsb.__main__ import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(errors="replace")  # Umlaute nie zum Absturz werden lassen
        except (AttributeError, ValueError):
            pass
    main()
