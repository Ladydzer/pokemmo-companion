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

from src.utils.config import DB_PATH
from src.utils.logger import log


def main():
    log.info("PokeMMO Companion Desktop v0.2.0 starting...")

    app = QApplication(sys.argv)
    app.setApplicationName("PokeMMO Companion")
    app.setFont(QFont("Segoe UI", 10))

    # Show splash screen
    from src.app.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    splash.set_progress(10, "Loading database...")

    # Load database
    db = None
    if DB_PATH.exists():
        from src.data.database import Database
        db = Database()
        log.info(f"Database loaded: {db.get_pokemon_count()} Pokemon")
        splash.set_progress(40, f"Loaded {db.get_pokemon_count()} Pokemon...")
    else:
        log.warning(f"Database not found at {DB_PATH}")
        splash.set_progress(40, "Database not found!")

    splash.set_progress(60, "Building interface...")

    # Create main window
    from src.app.main_window import MainWindow
    window = MainWindow(db)

    splash.set_progress(90, "Almost ready...")

    # Check if first launch — show onboarding
    from src.utils.config import AppConfig
    config = AppConfig.load()
    if config.first_run:
        splash.close()
        from src.app.onboarding import OnboardingDialog
        dialog = OnboardingDialog()
        if dialog.exec():
            data = dialog.result_data
            log.info(f"Onboarding: {data['region']}, {data['badges']} badges, starter {data['starter']}")
            # Update guide panel with onboarding data
            if hasattr(window, 'dashboard') and hasattr(window.dashboard, 'guide_region'):
                pass  # Guide panel will use this data
            config.first_run = False
            config.save()

    # Show main window, close splash
    window.show()
    splash.set_progress(100, "Welcome!")

    import time
    time.sleep(0.3)  # Brief pause so user sees "Welcome!"
    splash.close()

    log.info("Companion app displayed.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
