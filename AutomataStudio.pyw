"""Launcher for AutomataStudio without a console window (double-click on Windows).

Runs with pythonw.exe (the .pyw extension is associated with it by default),
which starts the app with no visible console/CMD window.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import main

if __name__ == "__main__":
    sys.exit(main())
