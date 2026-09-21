"""Light and dark Qt stylesheets for the application."""

LIGHT_QSS = """
QWidget { background-color: #f4f6f8; color: #1c1e21; font-size: 13px; }
QMainWindow { background-color: #f4f6f8; }
QMenuBar { background-color: #ffffff; border-bottom: 1px solid #dfe3e8; }
QMenuBar::item:selected { background-color: #e3edf9; }
QMenu { background-color: #ffffff; border: 1px solid #dfe3e8; }
QMenu::item:selected { background-color: #e3edf9; }
QToolBar { background-color: #ffffff; border-bottom: 1px solid #dfe3e8; spacing: 4px; padding: 4px; }
QDockWidget { titlebar-close-icon: none; font-weight: 600; }
QDockWidget::title { background-color: #e9edf1; padding: 6px; }
QGraphicsView { background-color: #ffffff; border: 1px solid #dfe3e8; }
QTableWidget, QListWidget, QTreeWidget { background-color: #ffffff; border: 1px solid #dfe3e8; gridline-color: #e3e6ea; }
QHeaderView::section { background-color: #e9edf1; padding: 4px; border: none; }
QPushButton { background-color: #2d6fd6; color: white; border-radius: 4px; padding: 6px 12px; }
QPushButton:hover { background-color: #255bb0; }
QPushButton:disabled { background-color: #b7c3d6; }
QPushButton#secondary { background-color: #e9edf1; color: #1c1e21; }
QPushButton#secondary:hover { background-color: #d8dee5; }
QLineEdit, QComboBox, QSpinBox { background-color: #ffffff; border: 1px solid #c7ccd3; border-radius: 4px; padding: 4px; }
QTabWidget::pane { border: 1px solid #dfe3e8; }
QTabBar::tab { background: #e9edf1; padding: 6px 12px; }
QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #2d6fd6; }
QStatusBar { background-color: #ffffff; border-top: 1px solid #dfe3e8; }
"""

DARK_QSS = """
QWidget { background-color: #1e2126; color: #e6e6e6; font-size: 13px; }
QMainWindow { background-color: #1e2126; }
QMenuBar { background-color: #26292f; border-bottom: 1px solid #33373e; }
QMenuBar::item:selected { background-color: #33373e; }
QMenu { background-color: #26292f; border: 1px solid #33373e; }
QMenu::item:selected { background-color: #33373e; }
QToolBar { background-color: #26292f; border-bottom: 1px solid #33373e; spacing: 4px; padding: 4px; }
QDockWidget { titlebar-close-icon: none; font-weight: 600; }
QDockWidget::title { background-color: #26292f; padding: 6px; color: #e6e6e6; }
QGraphicsView { background-color: #14161a; border: 1px solid #33373e; }
QTableWidget, QListWidget, QTreeWidget { background-color: #22252b; border: 1px solid #33373e; gridline-color: #33373e; color: #e6e6e6; }
QHeaderView::section { background-color: #2c2f36; padding: 4px; border: none; color: #e6e6e6; }
QPushButton { background-color: #3d7de3; color: white; border-radius: 4px; padding: 6px 12px; }
QPushButton:hover { background-color: #5a92e8; }
QPushButton:disabled { background-color: #3a3f47; color: #7c828b; }
QPushButton#secondary { background-color: #2c2f36; color: #e6e6e6; }
QPushButton#secondary:hover { background-color: #383c44; }
QLineEdit, QComboBox, QSpinBox { background-color: #22252b; border: 1px solid #3a3f47; border-radius: 4px; padding: 4px; color: #e6e6e6; }
QTabWidget::pane { border: 1px solid #33373e; }
QTabBar::tab { background: #26292f; padding: 6px 12px; color: #cfd3d9; }
QTabBar::tab:selected { background: #1e2126; border-bottom: 2px solid #3d7de3; color: white; }
QStatusBar { background-color: #26292f; border-top: 1px solid #33373e; }
"""


def stylesheet(dark: bool) -> str:
    return DARK_QSS if dark else LIGHT_QSS
