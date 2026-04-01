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
    import traceback
    print("[THREAD] Detection loop started", flush=True)

    try:
        from src.detection.ocr_engine import init_tesseract
        print("[THREAD] OCR engine imported", flush=True)

        if not init_tesseract():
            print("[THREAD] Tesseract not found!", flush=True)
            return

        from src.capture.screen_capture import ScreenCapture
        cap = ScreenCapture()
        print("[THREAD] ScreenCapture created", flush=True)

        while not cap.initialize():
            print("[THREAD] Waiting for PokeMMO...", flush=True)
            time.sleep(5)

        print(f"[THREAD] PokeMMO found! rect={cap.window_rect}", flush=True)
        qt_update_fn(lambda: overlay.update_status("PokeMMO connecte !"))

    except Exception as e:
        print(f"[THREAD] INIT CRASH: {e}", flush=True)
        traceback.print_exc()
        return

    try:
        from src.detection.route_detector import RouteDetector
        from src.detection.battle_detector import BattleDetector
        from src.data.database import Database
        print("[THREAD] Detectors imported", flush=True)

        db = Database()
        route_det = RouteDetector()
        battle_det = BattleDetector(db=db)
        print("[THREAD] Detectors created", flush=True)
    except Exception as e:
        print(f"[THREAD] DETECTOR INIT CRASH: {e}", flush=True)
        traceback.print_exc()
        return

    # Apply saved OCR regions from Studio OCR
    regions = load_ocr_regions()
    apply_ocr_regions(route_det, battle_det, regions)

    last_route = ""
    last_opponent = ""
    in_battle = False

    print("[THREAD] Entering main detection loop", flush=True)
    log.info("Pipeline OCR demarre — detection en cours...")
    qt_update_fn(lambda: overlay.update_status("Detection active"))

    frame_count = 0
    while True:
        try:
            frame = cap.capture_full()
            if frame is None:
                if frame_count == 0:
                    print("[THREAD] First frame is None!", flush=True)
                time.sleep(1)
                continue

            frame_count += 1
            if frame_count <= 3:
                print(f"[THREAD] Frame {frame_count}: {frame.shape}", flush=True)
            # Skip first 2 frames (may capture our own window during startup)
            if frame_count <= 2:
                time.sleep(0.5)
                continue

            # Always try both route and battle detection
            # (state machine is unreliable without calibration)

            # Detect route
            route_name = route_det.detect_route(frame)
            if frame_count <= 3:
                # Log first few OCR attempts for debugging
                from src.detection.ocr_engine import read_route_name, preprocess_light_text
                h, w = frame.shape[:2]
                roi = route_det._route_roi
                rx, ry = int(roi["x_ratio"] * w), int(roi["y_ratio"] * h)
                rw, rh = int(roi["w_ratio"] * w), int(roi["h_ratio"] * h)
                route_region = frame[ry:ry+rh, rx:rx+rw]
                if route_region.size > 0:
                    raw_text = read_route_name(route_region)
                    log.info(f"OCR debug frame {frame_count}: route region {rw}x{rh} at ({rx},{ry}) -> '{raw_text}'")

            if route_name and route_name != last_route:
                last_route = route_name
                region = route_det.current_region
                log.info(f"Route detectee: {last_route} ({region})")

                name, reg = last_route, region
                qt_update_fn(lambda: overlay.update_route(name, reg))

                spawns = fetch_spawns(last_route)
                if spawns:
                    log.info(f"Spawns: {len(spawns)} Pokemon dans {last_route}")
                qt_update_fn(lambda: overlay.update_spawns(spawns))
                qt_update_fn(lambda: overlay.update_counter_location(name, reg))

            # Detect battle opponent
            battle_info = battle_det.detect_opponent(frame)
            if battle_info and battle_info.get("name"):
                opponent = battle_info["name"]
                if opponent != last_opponent:
                    if not in_battle:
                        in_battle = True
                        log.info("Combat detecte !")
                    last_opponent = opponent
                    types_str = '/'.join(battle_info.get('types', []))
                    log.info(f"Adversaire: {opponent} ({types_str})")
                    info = dict(battle_info)
                    qt_update_fn(lambda: overlay.show_battle(info))
                    qt_update_fn(lambda: overlay.increment_encounter())
            elif in_battle and not battle_info:
                # No opponent detected for a while — battle probably ended
                in_battle = False
                last_opponent = ""
                qt_update_fn(lambda: overlay.hide_battle())

            time.sleep(0.5)
        except Exception as e:
            log.warning(f"Detection error: {e}")
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
