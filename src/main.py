"""PokeMMO Companion — Main entry point.

Real-time overlay for PokeMMO with route detection, spawn data,
battle type counters, and game guides.

Usage:
    python -m src.main
    python src/main.py
"""
import sys
import time
import threading

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

from .utils.config import AppConfig, DB_PATH
from .utils.constants import GameState
from .utils.logger import log
from .capture.screen_capture import ScreenCapture
from .detection.state_machine import GameStateDetector
from .detection.route_detector import RouteDetector
from .detection.battle_detector import BattleDetector
from .data.database import Database
from .ui.overlay import OverlayWindow, ToastNotification


class GameEngine(QObject):
    """Core game detection engine — runs capture + detection pipeline.

    Emits Qt signals when game state changes, which the UI consumes.
    """
    route_changed = pyqtSignal(str, str, list)  # route_name, region, spawns
    battle_started = pyqtSignal(dict)            # battle_info
    battle_ended = pyqtSignal()
    state_changed = pyqtSignal(str, str)         # new_state, old_state
    game_found = pyqtSignal(bool)                # connected/disconnected

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.capture = ScreenCapture(config.capture.game_window_title)
        self.state_detector = GameStateDetector()
        self.route_detector = RouteDetector()
        self.battle_detector: BattleDetector | None = None
        self.db: Database | None = None
        self._running = False
        self._game_connected = False

    def initialize(self) -> bool:
        """Initialize all engines."""
        # Database
        if DB_PATH.exists():
            self.db = Database()
            self.battle_detector = BattleDetector(self.db)
            pokemon_count = self.db.get_pokemon_count()
            log.info(f"Database loaded: {pokemon_count} Pokemon")
        else:
            log.warning(f"Database not found at {DB_PATH}. Run scripts/build_database.py first.")
            self.battle_detector = BattleDetector()

        # Screen capture
        if self.capture.initialize():
            self._game_connected = True
            log.info("Game window found — capture engine ready")
            size = self.capture.get_game_size()
            if size:
                self.state_detector.calibrate(*size)
        else:
            self._game_connected = False
            log.info("Game window not found — will retry")

        return True

    def tick(self) -> None:
        """Run one detection cycle. Called by QTimer."""
        if not self._game_connected:
            # Try to find game window
            if self.capture.initialize():
                self._game_connected = True
                self.game_found.emit(True)
                log.info("Game window connected!")
                size = self.capture.get_game_size()
                if size:
                    self.state_detector.calibrate(*size)
            return

        # Check game still running
        if not self.capture.is_game_running():
            self._game_connected = False
            self.game_found.emit(False)
            log.info("Game window lost — will retry")
            return

        # Capture frame
        frame = self.capture.capture_full()
        if frame is None:
            return

        # Detect game state
        old_state = self.state_detector.current_state
        new_state = self.state_detector.detect_state(frame)

        if new_state != old_state:
            self.state_changed.emit(new_state, old_state)

        # Route detection (overworld)
        if new_state == GameState.OVERWORLD:
            route_name = self.route_detector.detect_route(frame)
            if route_name:
                region = self.route_detector.current_region
                spawns = []
                if self.db:
                    spawns = self.db.get_spawns_for_route(route_name, region or None)
                self.route_changed.emit(route_name, region, spawns)

        # Battle detection
        elif new_state == GameState.BATTLE:
            if self.battle_detector and self.state_detector.just_entered(GameState.BATTLE):
                info = self.battle_detector.detect_opponent(frame)
                if info:
                    self.battle_started.emit(info)

            # Periodically re-read in battle (opponent might change)
            elif self.battle_detector and self.state_detector.time_in_state() > 2.0:
                info = self.battle_detector.detect_opponent(frame)
                if info and info.get("name") != self.battle_detector.current_opponent:
                    self.battle_started.emit(info)

        # Battle ended
        if old_state == GameState.BATTLE and new_state != GameState.BATTLE:
            self.battle_ended.emit()

    def cleanup(self):
        """Clean up resources."""
        self.capture.cleanup()


class CompanionApp:
    """Main application controller."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("PokeMMO Companion")
        self.config = AppConfig.load()
        self.overlay: OverlayWindow | None = None
        self.engine: GameEngine | None = None
        self.timer: QTimer | None = None

    def run(self) -> int:
        """Start the companion app."""
        log.info("=" * 50)
        log.info("PokeMMO Companion v0.1.0 starting...")
        log.info("=" * 50)

        # Setup overlay
        self.overlay = OverlayWindow(self.config)

        # Setup game engine
        self.engine = GameEngine(self.config)
        self.engine.initialize()

        # Pass database to overlay widgets that need it
        if self.engine.db:
            self.overlay.guide_panel.db = self.engine.db
            self.overlay.pokedex_widget.db = self.engine.db
            self.overlay.tools_panel.iv_tab.db = self.engine.db

        # Connect signals
        self.engine.route_changed.connect(self._on_route_changed)
        self.engine.battle_started.connect(self._on_battle_started)
        self.engine.battle_ended.connect(self._on_battle_ended)
        self.engine.state_changed.connect(self._on_state_changed)
        self.engine.game_found.connect(self._on_game_found)

        # Setup hotkeys
        self._setup_hotkeys()

        # Start detection loop
        interval_ms = int(1000 / self.config.capture.target_fps)
        self.timer = QTimer()
        self.timer.timeout.connect(self.engine.tick)
        self.timer.start(interval_ms)
        log.info(f"Detection loop started ({self.config.capture.target_fps} FPS, "
                 f"{interval_ms}ms interval)")

        # Show overlay
        self.overlay.show()

        if self.engine._game_connected:
            self.overlay.update_status("PokeMMO Companion | Connected | F9: Toggle")
        else:
            self.overlay.update_status("PokeMMO Companion | Waiting for game... | F9: Toggle")

        log.info("Overlay displayed. Press F9 to toggle visibility.")

        # Run
        ret = self.app.exec()

        # Cleanup — save state before exit
        self.overlay.save_position()
        self.overlay.encounter_counter.save()
        self.engine.cleanup()
        self.config.save()

        return ret

    def _on_route_changed(self, route_name: str, region: str, spawns: list) -> None:
        """Handle route change."""
        self.overlay.update_route(route_name, region)
        self.overlay.update_spawns(spawns)
        self.overlay.hide_battle()
        self.overlay.update_counter_location(route_name, region)
        # Update guide panel with new location (Mode Coach GPS)
        self.overlay.guide_panel.update_location(route_name, region)

    def _on_battle_started(self, info: dict) -> None:
        """Handle battle detection — show battle panel + increment counter."""
        self.overlay.show_battle(info)
        # Auto-increment encounter counter on wild battles
        # TODO: distinguish wild vs trainer battles
        self.overlay.increment_encounter(is_horde=False)

    def _on_battle_ended(self) -> None:
        """Handle battle end."""
        self.overlay.hide_battle()

    def _on_state_changed(self, new_state: str, old_state: str) -> None:
        """Handle game state change."""
        state_display = {
            GameState.OVERWORLD: "Exploring",
            GameState.BATTLE: "In Battle",
            GameState.MENU: "Menu",
            GameState.DIALOG: "Dialog",
            GameState.LOADING: "Loading...",
            GameState.UNKNOWN: "Detecting...",
        }
        status = state_display.get(new_state, new_state)
        self.overlay.update_status(f"PokeMMO Companion | {status} | F9: Toggle")

    def _on_game_found(self, connected: bool) -> None:
        """Handle game connection/disconnection."""
        if connected:
            self.overlay.update_status("PokeMMO Companion | Connected | F9: Toggle")
            self._toast = ToastNotification("PokeMMO detected! Companion active.", 3000, "#4CAF50")
        else:
            self.overlay.update_status("PokeMMO Companion | Game not found | F9: Toggle")

    def _setup_hotkeys(self) -> None:
        """Setup global hotkeys."""
        try:
            import keyboard
            keyboard.add_hotkey(
                self.config.overlay.toggle_hotkey,
                self._toggle_overlay
            )
            keyboard.add_hotkey("f10", self._toggle_extended)
            keyboard.add_hotkey("f11", self._toggle_debug)
            log.info(f"Hotkeys registered: {self.config.overlay.toggle_hotkey.upper()}=toggle, F10=extended, F11=debug")
        except ImportError:
            log.warning("keyboard library not installed -- hotkeys disabled")
        except Exception as e:
            log.warning(f"Failed to register hotkeys: {e}")

    def _toggle_overlay(self) -> None:
        """Toggle overlay visibility (called from hotkey thread)."""
        QTimer.singleShot(0, self.overlay.toggle_visibility)

    def _toggle_extended(self) -> None:
        """Toggle extended mode (called from hotkey thread)."""
        QTimer.singleShot(0, self.overlay.toggle_extended)

    def _toggle_debug(self) -> None:
        """Toggle debug mode (called from hotkey thread)."""
        QTimer.singleShot(0, self.overlay.toggle_debug)


def main():
    app = CompanionApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
