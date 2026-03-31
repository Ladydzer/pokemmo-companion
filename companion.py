"""PokeMMO Companion — All-in-one: web UI + overlay + game detection.

Launches:
1. FastAPI web server (localhost:8080) -> opens browser
2. PyQt6 overlay (toggle with sidebar button or F9)
3. Game detection thread (checks for PokeMMO window)

Usage:
    python companion.py
"""
import sys
import os
import threading
import time
import webbrowser

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
    sys.path.insert(0, sys._MEIPASS)

from src.utils.logger import log

PORT = 8080


def start_web_server():
    """Start FastAPI server in a background thread."""
    import uvicorn
    uvicorn.run("src.web.server:app", host="127.0.0.1", port=PORT, log_level="warning")


def open_browser():
    """Open browser after server is ready."""
    time.sleep(2)
    # Try Edge in app mode first (looks like native app)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for edge in edge_paths:
        if os.path.exists(edge):
            os.system(f'"{edge}" --app=http://localhost:{PORT}')
            return
    webbrowser.open(f"http://localhost:{PORT}")


def start_overlay():
    """Start PyQt6 overlay in the main thread (Qt requires main thread)."""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        from src.ui.overlay import OverlayWindow
        from src.utils.config import AppConfig

        app = QApplication(sys.argv)
        config = AppConfig.load()
        overlay = OverlayWindow(config)

        # Don't show overlay by default — user toggles it
        overlay.hide()

        # Setup hotkeys
        try:
            import keyboard
            def toggle():
                QTimer.singleShot(0, overlay.toggle_visibility)
            def extend():
                QTimer.singleShot(0, overlay.toggle_extended)
            keyboard.add_hotkey(config.overlay.toggle_hotkey, toggle)
            keyboard.add_hotkey("f10", extend)
            log.info(f"Hotkeys: {config.overlay.toggle_hotkey.upper()}=overlay, F10=etendu")
        except ImportError:
            log.info("Hotkeys: pip install keyboard pour activer")
        except Exception as e:
            log.info(f"Hotkeys: {e}")

        log.info("Overlay pret (masque par defaut, F9 pour afficher)")
        app.exec()
    except Exception as e:
        log.warning(f"Overlay non disponible: {e}")
        log.info("L'interface web fonctionne sans l'overlay.")
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def main():
    log.info("=" * 50)
    log.info("PokeMMO Companion v0.5.0")
    log.info("=" * 50)

    # Start web server in background
    server_thread = threading.Thread(target=start_web_server, daemon=True)
    server_thread.start()
    log.info(f"Serveur web demarre sur http://localhost:{PORT}")

    # Open browser in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Start overlay in main thread (Qt requires it)
    log.info("Interface web: http://localhost:{PORT}")
    log.info("Overlay: F9 pour afficher/masquer")
    start_overlay()


if __name__ == "__main__":
    main()
