"""Standalone overlay runner — launched as subprocess by web server.

Runs the PyQt6 overlay with OCR detection pipeline.
Communicates with web server API for Pokemon data.
"""
import sys
import os
import time
import threading
import requests

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import log
from src.utils.config import AppConfig

API_BASE = "http://127.0.0.1:8080"


def detection_loop(overlay):
    """Background thread: capture screen, run OCR, update overlay."""
    from src.detection.ocr_engine import init_tesseract, read_route_name, read_pokemon_name
    from src.detection.state_machine import GameState

    if not init_tesseract():
        log.error("Tesseract non disponible — OCR desactive")
        return

    try:
        from src.capture.screen_capture import ScreenCapture
        cap = ScreenCapture()
        if not cap.initialize():
            log.warning("PokeMMO non detecte — en attente...")
            # Retry every 5 seconds
            while True:
                time.sleep(5)
                if cap.initialize():
                    log.info("PokeMMO detecte !")
                    break
    except Exception as e:
        log.error(f"Capture ecran non disponible: {e}")
        return

    from src.detection.route_detector import RouteDetector
    from src.detection.battle_detector import BattleDetector
    from src.data.database import Database

    db = Database()
    route_det = RouteDetector(db=db)
    battle_det = BattleDetector(db=db)
    state = GameState()
    last_route = ""
    last_opponent = ""

    log.info("Pipeline OCR demarre — detection en cours...")

    while True:
        try:
            frame = cap.capture_full()
            if frame is None:
                time.sleep(1)
                continue

            # Detect route
            route_info = route_det.detect_route(frame)
            if route_info and route_info.get("name") and route_info["name"] != last_route:
                last_route = route_info["name"]
                log.info(f"Route detectee: {last_route}")
                # Fetch spawns from API
                try:
                    spawns = requests.get(
                        f"{API_BASE}/api/spawns/{last_route}",
                        timeout=2
                    ).json()
                    overlay.update_route(last_route, spawns)
                except Exception:
                    overlay.update_route(last_route, [])

            # Detect battle
            battle_info = battle_det.detect_opponent(frame)
            if battle_info and battle_info.get("name") and battle_info["name"] != last_opponent:
                last_opponent = battle_info["name"]
                log.info(f"Combat: {last_opponent}")
                overlay.update_battle(battle_info)

            time.sleep(0.5)  # 2 FPS detection — enough for PokeMMO
        except Exception as e:
            log.debug(f"Detection error: {e}")
            time.sleep(1)


def main():
    log.info("Overlay Runner demarre...")

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        from src.ui.overlay import OverlayWindow
    except ImportError as e:
        log.error(f"PyQt6 non installe: {e}")
        log.error("Installez: py -m pip install PyQt6 opencv-python pytesseract numpy")
        sys.exit(1)

    config = AppConfig.load()
    app = QApplication(sys.argv)
    overlay = OverlayWindow(config)
    overlay.show()

    # Start detection loop in background
    det_thread = threading.Thread(target=detection_loop, args=(overlay,), daemon=True)
    det_thread.start()

    # Setup hotkeys
    try:
        import keyboard
        keyboard.add_hotkey(config.overlay.toggle_hotkey,
                          lambda: QTimer.singleShot(0, overlay.toggle_visibility))
        keyboard.add_hotkey("f10",
                          lambda: QTimer.singleShot(0, overlay.toggle_extended))
        log.info(f"Hotkeys: {config.overlay.toggle_hotkey.upper()}=toggle, F10=etendu")
    except ImportError:
        log.info("Hotkeys: pip install keyboard pour activer")
    except Exception as e:
        log.info(f"Hotkeys: {e}")

    log.info("Overlay actif — F9 pour masquer/afficher, F10 pour mode etendu")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
