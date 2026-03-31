"""PokeMMO Companion — All-in-one desktop app + overlay.

One app to rule them all:
- Desktop companion with 8 pages (Pokedex, Battle, Team, etc.)
- Game overlay (toggle with F9) on top of PokeMMO
- Game detection + OCR route reading

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
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont

from src.utils.config import DB_PATH, AppConfig
from src.utils.logger import log


def main():
    log.info("PokeMMO Companion v0.3.0 starting...")

    app = QApplication(sys.argv)
    app.setApplicationName("PokeMMO Companion")
    app.setFont(QFont("Segoe UI", 10))

    # Apply professional dark theme
    try:
        import qdarktheme
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        log.info("Dark theme applied")
    except Exception:
        log.info("Using built-in theme")

    # Show splash screen
    from src.app.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    splash.set_progress(10, "Chargement de la base...")

    # Load database
    db = None
    if DB_PATH.exists():
        from src.data.database import Database
        db = Database()
        log.info(f"Database loaded: {db.get_pokemon_count()} Pokemon")
        splash.set_progress(30, f"{db.get_pokemon_count()} Pokemon charges...")
    else:
        log.warning(f"Database not found at {DB_PATH}")
        splash.set_progress(30, "Base de donnees introuvable !")

    splash.set_progress(50, "Construction de l'interface...")

    # Create main window
    from src.app.main_window import MainWindow
    window = MainWindow(db)

    splash.set_progress(70, "Preparation de l'overlay...")

    # Create overlay (integrated)
    from src.ui.overlay import OverlayWindow
    config = AppConfig.load()
    overlay = OverlayWindow(config)

    # Pass DB to overlay widgets
    if db:
        overlay.guide_panel.db = db
        overlay.pokedex_widget.db = db
        overlay.tools_panel.iv_tab.db = db

    # Setup overlay toggle from main window
    window._overlay = overlay
    window._overlay_visible = False

    def toggle_overlay():
        window._overlay_visible = not window._overlay_visible
        if window._overlay_visible:
            overlay.show()
            log.info("Overlay affiche")
        else:
            overlay.hide()
            log.info("Overlay masque")

    window._toggle_overlay = toggle_overlay

    # Setup hotkeys (F9 for overlay toggle)
    try:
        import keyboard
        keyboard.add_hotkey(config.overlay.toggle_hotkey, toggle_overlay)
        keyboard.add_hotkey("f10", overlay.toggle_extended)
        log.info(f"Hotkeys: {config.overlay.toggle_hotkey.upper()}=overlay, F10=etendu")
    except ImportError:
        log.warning("keyboard non installe -- hotkeys desactives. Pip install keyboard")
    except OSError:
        log.warning("Hotkeys necessitent les droits admin. Lance en administrateur.")
    except Exception as e:
        log.warning(f"Hotkeys: {e}")

    splash.set_progress(90, "Presque pret...")

    # Check if first launch — show onboarding
    if config.first_run:
        splash.close()
        from src.app.onboarding import OnboardingDialog
        dialog = OnboardingDialog()
        if dialog.exec():
            data = dialog.result_data
            log.info(f"Onboarding: {data['region']}, {data['badges']} badges, {data['starter']}")
            config.first_run = False
            config.save()

    # Show main window, close splash
    window.show()
    splash.set_progress(100, "Bienvenue !")

    import time
    time.sleep(0.3)
    splash.close()

    log.info("PokeMMO Companion pret ! F9 = overlay, F10 = mode etendu")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
