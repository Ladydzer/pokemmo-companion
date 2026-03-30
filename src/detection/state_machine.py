"""Game state machine — detects whether player is in overworld, battle, menu, etc."""
import time
import numpy as np
import cv2

from ..utils.constants import GameState
from ..utils.logger import log


class GameStateDetector:
    """Detects the current game state using pixel sampling and template matching.

    Detection strategy (fast to slow):
    1. Pixel color sampling at key positions (<1ms)
    2. Histogram comparison for state confirmation (~5ms)
    3. Template matching for specific UI elements (~10ms, only when needed)
    """

    def __init__(self):
        self.current_state: str = GameState.UNKNOWN
        self.previous_state: str = GameState.UNKNOWN
        self.state_since: float = time.time()
        self.state_confidence: float = 0.0

        # Reference colors/positions will be calibrated on first run
        self._calibrated = False
        self._game_size: tuple[int, int] = (1920, 1080)

        # Battle detection: PokeMMO battle screen has a distinct dark border
        # and HP bars in specific positions
        self._battle_border_color_range = (
            np.array([20, 20, 20]),   # dark gray lower
            np.array([60, 60, 60]),   # dark gray upper
        )

    def calibrate(self, game_width: int, game_height: int) -> None:
        """Set game window dimensions for proportional position calculations."""
        self._game_size = (game_width, game_height)
        self._calibrated = True
        log.info(f"State detector calibrated for {game_width}x{game_height}")

    def _scale_pos(self, x_ratio: float, y_ratio: float) -> tuple[int, int]:
        """Convert a proportional position to actual pixel coordinates."""
        return (int(x_ratio * self._game_size[0]),
                int(y_ratio * self._game_size[1]))

    def detect_state(self, frame: np.ndarray) -> str:
        """Detect the current game state from a screenshot.

        Returns the detected GameState string.
        """
        if frame is None or frame.size == 0:
            return self.current_state

        # Auto-calibrate if needed
        if not self._calibrated:
            h, w = frame.shape[:2]
            self.calibrate(w, h)

        new_state = self._detect_from_frame(frame)
        confidence = self._calculate_confidence(frame, new_state)

        # Only change state if confident enough (prevents flickering)
        if new_state != self.current_state and confidence > 0.7:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_since = time.time()
            self.state_confidence = confidence
            log.info(f"State change: {self.previous_state} → {self.current_state} "
                     f"(confidence: {confidence:.0%})")

        return self.current_state

    def _detect_from_frame(self, frame: np.ndarray) -> str:
        """Core detection logic using pixel sampling."""
        h, w = frame.shape[:2]

        # === BATTLE DETECTION ===
        # Check for dark battle border (top and bottom of screen)
        # Battle screens have distinctive dark borders
        top_strip = frame[0:int(h * 0.05), :, :]
        bottom_strip = frame[int(h * 0.95):, :, :]

        top_mean = np.mean(top_strip, axis=(0, 1))
        bottom_mean = np.mean(bottom_strip, axis=(0, 1))

        # Check if HP bar region exists (green/yellow/red bar)
        # Enemy HP is typically in top-right area
        hp_region = frame[int(h * 0.08):int(h * 0.15), int(w * 0.55):int(w * 0.85), :]
        hp_green = np.sum((hp_region[:, :, 1] > 100) &
                          (hp_region[:, :, 0] < 80) &
                          (hp_region[:, :, 2] < 80))
        hp_yellow = np.sum((hp_region[:, :, 1] > 150) &
                           (hp_region[:, :, 2] > 150) &
                           (hp_region[:, :, 0] < 80))
        hp_pixels = hp_green + hp_yellow

        # If dark borders + HP bar detected = battle
        if (np.all(top_mean < 60) and np.all(bottom_mean < 60) and
                hp_pixels > (hp_region.shape[0] * hp_region.shape[1] * 0.01)):
            return GameState.BATTLE

        # === MENU DETECTION ===
        # Menu screens in PokeMMO have a semi-transparent dark overlay
        center = frame[int(h * 0.3):int(h * 0.7), int(w * 0.3):int(w * 0.7), :]
        center_std = np.std(center)
        center_mean = np.mean(center)

        # Menu = low variance (uniform dark overlay) + medium brightness
        if center_std < 30 and 40 < center_mean < 120:
            return GameState.MENU

        # === DIALOG DETECTION ===
        # Dialog boxes appear at the bottom of the screen
        dialog_region = frame[int(h * 0.75):int(h * 0.95), int(w * 0.1):int(w * 0.9), :]
        dialog_mean = np.mean(dialog_region)
        dialog_std = np.std(dialog_region)

        # Dialog box = relatively uniform (text box), bright region at bottom
        if dialog_std < 40 and dialog_mean > 150:
            return GameState.DIALOG

        # === LOADING DETECTION ===
        # Full black screen = loading
        full_mean = np.mean(frame)
        if full_mean < 15:
            return GameState.LOADING

        # Default = overworld
        return GameState.OVERWORLD

    def _calculate_confidence(self, frame: np.ndarray, state: str) -> float:
        """Calculate confidence score for the detected state."""
        # Simple confidence based on how distinct the detection signals are
        h, w = frame.shape[:2]

        if state == GameState.BATTLE:
            # Check multiple battle indicators
            score = 0.0
            top_strip = frame[0:int(h * 0.05), :, :]
            if np.mean(top_strip) < 50:
                score += 0.4

            hp_region = frame[int(h * 0.08):int(h * 0.15), int(w * 0.55):int(w * 0.85), :]
            hp_green = np.sum(hp_region[:, :, 1] > 100)
            if hp_green > hp_region.size * 0.01:
                score += 0.4

            # Consistent state adds confidence
            if self.current_state == GameState.BATTLE:
                score += 0.2
            return min(score, 1.0)

        elif state == GameState.OVERWORLD:
            # Overworld = colorful, varied
            full_std = np.std(frame)
            if full_std > 40:
                return 0.9
            return 0.6

        elif state == GameState.LOADING:
            if np.mean(frame) < 10:
                return 0.95
            return 0.5

        return 0.75  # Default moderate confidence

    def time_in_state(self) -> float:
        """Get seconds spent in current state."""
        return time.time() - self.state_since

    def just_entered(self, state: str) -> bool:
        """Check if we just entered a specific state (within last 2 seconds)."""
        return self.current_state == state and self.time_in_state() < 2.0


if __name__ == "__main__":
    detector = GameStateDetector()
    detector.calibrate(1920, 1080)

    # Test with a synthetic black screen (loading)
    black = np.zeros((1080, 1920, 3), dtype=np.uint8)
    state = detector.detect_state(black)
    print(f"Black screen → {state}")  # Should be LOADING

    # Test with a colorful screen (overworld)
    colorful = np.random.randint(50, 200, (1080, 1920, 3), dtype=np.uint8)
    state = detector.detect_state(colorful)
    print(f"Colorful screen → {state}")  # Should be OVERWORLD
