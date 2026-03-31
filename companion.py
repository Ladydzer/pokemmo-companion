"""Launch the PokeMMO Companion desktop app (standalone, without overlay).

Usage:
    python companion.py
"""
import sys
import os

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    os.chdir(base_path)
    sys.path.insert(0, base_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from src.data.database import Database
from src.app.main_window import MainWindow
from src.utils.config import DB_PATH
from src.utils.logger import log


def main():
    log.info("PokeMMO Companion Desktop v0.2.0 starting...")

    app = QApplication(sys.argv)
    app.setApplicationName("PokeMMO Companion")
    app.setFont(QFont("Segoe UI", 10))

    # Load database
    db = None
    if DB_PATH.exists():
        db = Database()
        log.info(f"Database loaded: {db.get_pokemon_count()} Pokemon")
    else:
        log.warning(f"Database not found at {DB_PATH}")

    # Create and show main window
    window = MainWindow(db)
    window.show()

    log.info("Companion app displayed.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
