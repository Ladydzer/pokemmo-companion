"""Standalone overlay runner — launched as subprocess by web server.

Runs the PyQt6 overlay with OCR detection pipeline.
Communicates with web server API for Pokemon data.
"""
import sys
import os
import json
import time
import threading
import requests

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import log
from src.utils.config import AppConfig

API_BASE = "http://127.0.0.1:8080"


def load_ocr_regions():
    """Load OCR regions from config file (saved via Studio OCR in web app)."""
    config_path = os.path.join(PROJECT_ROOT, "data", "ocr_regions.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            log.info(f"OCR regions chargees depuis {config_path}")
            return data.get("regions", [])
        except Exception as e:
            log.warning(f"Erreur lecture OCR regions: {e}")
    return None


def apply_ocr_regions(route_det, battle_det, regions):
    """Apply saved OCR regions to detectors."""
    if not regions:
        return
    for r in regions:
        rid = r.get("id", "")
        x, y, w, h = r.get("x", 0) / 100, r.get("y", 0) / 100, r.get("w", 10) / 100, r.get("h", 4) / 100
        if rid == "route_name":
            route_det.set_roi(x, y, w, h)
            log.info(f"ROI route: x={x:.2f} y={y:.2f} w={w:.2f} h={h:.2f}")
        elif rid == "opponent_name":
            battle_det.set_name_roi(x, y, w, h)
            log.info(f"ROI adversaire: x={x:.2f} y={y:.2f} w={w:.2f} h={h:.2f}")


def fetch_spawns(route_name):
    """Fetch spawn data from web API."""
    try:
        r = requests.get(f"{API_BASE}/api/spawns/{route_name}", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def detection_loop(overlay, qt_update_fn):
    """Background thread: capture screen, run OCR, update overlay via Qt signals."""
    from src.detection.ocr_engine import init_tesseract
    from src.detection.state_machine import GameStateDetector
    from src.utils.constants import GameState

    if not init_tesseract():
        log.error("Tesseract non disponible — OCR desactive")
        qt_update_fn(lambda: overlay.update_status("Tesseract non installe !"))
        return

    try:
        from src.capture.screen_capture import ScreenCapture
        cap = ScreenCapture()
        qt_update_fn(lambda: overlay.update_status("Recherche PokeMMO..."))
        while not cap.initialize():
            log.info("PokeMMO non detecte — nouvelle tentative dans 5s...")
            time.sleep(5)
        log.info("PokeMMO detecte !")
        qt_update_fn(lambda: overlay.update_status("PokeMMO connecte !"))
    except Exception as e:
        log.error(f"Capture ecran non disponible: {e}")
        qt_update_fn(lambda: overlay.update_status(f"Erreur capture: {str(e)[:50]}"))
        return

    from src.detection.route_detector import RouteDetector
    from src.detection.battle_detector import BattleDetector
    from src.data.database import Database

    db = Database()
    route_det = RouteDetector()
    battle_det = BattleDetector(db=db)
    state_det = GameStateDetector()

    # Apply saved OCR regions from Studio OCR
    regions = load_ocr_regions()
    apply_ocr_regions(route_det, battle_det, regions)

    last_route = ""
    last_opponent = ""
    in_battle = False

    log.info("Pipeline OCR demarre — detection en cours...")
    qt_update_fn(lambda: overlay.update_status("Detection active"))

    while True:
        try:
            frame = cap.capture_full()
            if frame is None:
                time.sleep(1)
                continue

            # Detect game state
            game_state = state_det.detect_state(frame)

            if game_state == GameState.BATTLE:
                if not in_battle:
                    in_battle = True
                    log.info("Combat detecte !")

                # Detect opponent
                battle_info = battle_det.detect_opponent(frame)
                if battle_info and battle_info.get("name"):
                    opponent = battle_info["name"]
                    if opponent != last_opponent:
                        last_opponent = opponent
                        log.info(f"Adversaire: {opponent} ({'/'.join(battle_info.get('types', []))})")
                        # Thread-safe Qt update
                        info = dict(battle_info)  # Copy for closure
                        qt_update_fn(lambda: overlay.show_battle(info))
                        # Increment encounter counter
                        qt_update_fn(lambda: overlay.increment_encounter())

            else:
                if in_battle:
                    in_battle = False
                    last_opponent = ""
                    qt_update_fn(lambda: overlay.hide_battle())

                # Detect route (only outside battle)
                route_name = route_det.detect_route(frame)
                if route_name and route_name != last_route:
                    last_route = route_name
                    region = route_det.current_region
                    log.info(f"Route: {last_route} ({region})")

                    # Update overlay route display
                    name, reg = last_route, region  # Copies for closure
                    qt_update_fn(lambda: overlay.update_route(name, reg))

                    # Fetch and display spawns
                    spawns = fetch_spawns(last_route)
                    qt_update_fn(lambda: overlay.update_spawns(spawns))

                    # Update encounter counter location
                    qt_update_fn(lambda: overlay.update_counter_location(name, reg))

            time.sleep(0.5)  # 2 FPS — sufficient for PokeMMO turn-based
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
    overlay.update_status("Demarrage pipeline OCR...")

    # Thread-safe Qt update function
    def qt_update(fn):
        """Schedule a function to run on the Qt main thread."""
        QTimer.singleShot(0, fn)

    # Start detection loop in background
    det_thread = threading.Thread(target=detection_loop, args=(overlay, qt_update), daemon=True)
    det_thread.start()

    # Setup hotkeys
    try:
        import keyboard
        keyboard.add_hotkey(config.overlay.toggle_hotkey,
                          lambda: QTimer.singleShot(0, overlay.toggle_visibility))
        keyboard.add_hotkey("f10",
                          lambda: QTimer.singleShot(0, overlay.toggle_extended))
        keyboard.add_hotkey("f11",
                          lambda: QTimer.singleShot(0, overlay.toggle_debug))
        log.info(f"Hotkeys: F9=toggle, F10=etendu, F11=debug")
    except ImportError:
        log.info("Hotkeys: pip install keyboard pour activer")
    except Exception as e:
        log.info(f"Hotkeys: {e}")

    log.info("Overlay actif — F9=masquer, F10=etendu, F11=debug")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
