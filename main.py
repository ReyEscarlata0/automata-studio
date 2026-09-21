"""Entry point for AutomataStudio."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from utils import theme
from views.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AutomataStudio")
    app.setStyleSheet(theme.stylesheet(dark=False))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
