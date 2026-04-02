"""Standalone overlay runner — launched as subprocess by web server.

Runs the PyQt6 overlay with OCR detection pipeline.
Communicates with web server API for Pokemon data.
Uses QThread + moveToThread() for proper Qt integration.
"""
import sys
import os
import json
import time
import requests

# Late-import PyQt6 (not available on dev server, only on game machine)
try:
    from PyQt6.QtCore import QObject, pyqtSlot
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False
    # Stub for when PyQt6 isn't installed
    class QObject:  # type: ignore[no-redef]
        pass
    def pyqtSlot(*args, **kwargs):  # type: ignore[no-redef]
        def decorator(fn):
            return fn
        return decorator

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


def push_detection(route="", region="", opponent="", opponent_types=None,
                   in_battle=False, level=None):
    """Push live detection state to web backend for dashboard sync."""
    try:
        requests.post(f"{API_BASE}/api/ocr/detection", json={
            "route": route, "region": region, "opponent": opponent,
            "opponent_types": opponent_types or [], "in_battle": in_battle,
            "level": level,
        }, timeout=1)
    except Exception:
        pass  # non-blocking, best-effort


class DetectionWorker(QObject):
    """Background worker: capture screen, run OCR, call update callbacks.

    Uses QThread with moveToThread() for proper Qt lifecycle management.
    Emits updates via callbacks scheduled on the Qt main thread.
    """

    def __init__(self, overlay, qt_update_fn):
        super().__init__()
        self.overlay = overlay
        self.qt_update = qt_update_fn
        self._running = True

    def stop(self):
        self._running = False

    @pyqtSlot()
    def run(self):
        """Main detection loop — runs in QThread via moveToThread."""
        import traceback
        print("[THREAD] Detection loop started", flush=True)

        try:
            from src.detection.ocr_engine import init_tesseract
            print("[THREAD] OCR engine imported", flush=True)

            if not init_tesseract():
                print("[THREAD] Tesseract not found!", flush=True)
                self.qt_update(lambda: self.overlay.update_status(
                    "Tesseract non installe — voir Options > Diagnostic"))
                return

            from src.capture.screen_capture import ScreenCapture
            cap = ScreenCapture()
            print("[THREAD] ScreenCapture created", flush=True)

            while self._running and not cap.initialize():
                print("[THREAD] Waiting for PokeMMO...", flush=True)
                time.sleep(5)

            if not self._running:
                return

            print(f"[THREAD] PokeMMO found! rect={cap.window_rect}", flush=True)
            self.qt_update(lambda: self.overlay.update_status("PokeMMO connecte !"))

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
        last_region_reload = time.time()
        REGION_RELOAD_INTERVAL = 10

        # Load all route names for fuzzy matching
        try:
            import sqlite3
            conn = sqlite3.connect(str(os.path.join(PROJECT_ROOT, "data", "pokemon.db")))
            _routes_fr = [r[0] for r in conn.execute(
                "SELECT name_fr FROM routes WHERE name_fr IS NOT NULL"
            ).fetchall()]
            _routes_en = [r[0] for r in conn.execute(
                "SELECT name FROM routes"
            ).fetchall()]
            all_routes = list(set(_routes_fr + _routes_en))
            conn.close()
            log.info(f"Loaded {len(all_routes)} route names for fuzzy matching")
        except Exception:
            all_routes = []

        print("[THREAD] Entering main detection loop", flush=True)
        log.info("Pipeline OCR demarre — detection en cours...")
        self.qt_update(lambda: self.overlay.update_status("OCR actif | F10: Normal"))

        frame_count = 0
        ocr_reads = 0  # successful OCR reads counter
        while self._running:
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

                # Detect route
                route_name = route_det.detect_route(frame)
                if frame_count <= 3:
                    from src.detection.ocr_engine import read_route_name
                    h, w = frame.shape[:2]
                    roi = route_det._route_roi
                    rx, ry = int(roi["x_ratio"] * w), int(roi["y_ratio"] * h)
                    rw, rh = int(roi["w_ratio"] * w), int(roi["h_ratio"] * h)
                    route_region = frame[ry:ry+rh, rx:rx+rw]
                    if route_region.size > 0:
                        raw_text = read_route_name(route_region)
                        log.info(f"OCR debug frame {frame_count}: route region {rw}x{rh} at ({rx},{ry}) -> '{raw_text}'")

                if route_name:
                    ocr_reads += 1
                if route_name and route_name != last_route:
                    # Fuzzy match against known routes (rapidfuzz 77x faster)
                    if all_routes:
                        from src.detection.ocr_engine import fuzzy_match_name
                        matched = fuzzy_match_name(route_name, all_routes, cutoff=0.5)
                        if matched:
                            log.info(f"Route fuzzy: '{route_name}' -> '{matched}'")
                            route_name = matched

                    last_route = route_name
                    region = route_det.current_region
                    log.info(f"Route detectee: {last_route} ({region})")

                    name, reg = last_route, region
                    self.qt_update(lambda: self.overlay.update_route(name, reg))

                    spawns = fetch_spawns(last_route)
                    if spawns:
                        log.info(f"Spawns: {len(spawns)} Pokemon dans {last_route}")
                    self.qt_update(lambda: self.overlay.update_spawns(spawns))
                    self.qt_update(lambda: self.overlay.update_counter_location(name, reg))
                    push_detection(route=route_name, region=route_det.current_region)

                # Detect battle opponent (anti-flipflop: 3 reads + 1.5s cooldown)
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
                        self.qt_update(lambda: self.overlay.show_battle(info))
                        self.qt_update(lambda: self.overlay.increment_encounter())
                        ocr_reads += 1
                        push_detection(route=last_route, region=route_det.current_region,
                                       opponent=opponent, opponent_types=battle_info.get('types', []),
                                       in_battle=True, level=battle_info.get('level'))
                elif in_battle and battle_info is None:
                    in_battle = False
                    last_opponent = ""
                    self.qt_update(lambda: self.overlay.hide_battle())
                    push_detection(route=last_route, region=route_det.current_region, in_battle=False)

                # Periodically reload OCR regions + update status
                now = time.time()
                if now - last_region_reload > REGION_RELOAD_INTERVAL:
                    last_region_reload = now
                    new_regions = load_ocr_regions()
                    if new_regions:
                        apply_ocr_regions(route_det, battle_det, new_regions)
                    # Update status with OCR stats
                    reads = ocr_reads
                    status = f"OCR actif — {reads} lectures"
                    if last_route:
                        status += f" | {last_route}"
                    self.qt_update(lambda: self.overlay.update_status(status))

                time.sleep(0.2)  # 200ms interval (was 500ms)
            except Exception as e:
                log.warning(f"Detection error: {e}")
                time.sleep(1)


def main():
    log.info("Overlay Runner demarre...")

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer, QThread
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

    # Start detection in QThread (moveToThread pattern)
    worker = DetectionWorker(overlay, qt_update)
    det_thread = QThread()
    worker.moveToThread(det_thread)
    det_thread.started.connect(worker.run)
    app.aboutToQuit.connect(worker.stop)
    app.aboutToQuit.connect(det_thread.quit)
    worker_ref = worker  # prevent GC
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
