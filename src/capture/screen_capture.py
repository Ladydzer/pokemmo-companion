"""Screen capture engine using BetterCam for PokeMMO window."""
import time
import ctypes
import ctypes.wintypes
import numpy as np

from ..utils.logger import log

# Win32 API for finding game window
user32 = ctypes.windll.user32


def find_window(title: str = "PokeMMO") -> int | None:
    """Find the PokeMMO game window handle.

    Excludes our own overlay/companion windows to avoid self-detection.
    Logs all candidate windows for debugging.
    """
    # Words that indicate it's OUR window, not the game
    _exclude = ["companion", "overlay", "runner"]

    # First try exact match
    hwnd = user32.FindWindowW(None, title)
    if hwnd != 0:
        wt = get_window_title(hwnd).lower()
        if not any(ex in wt for ex in _exclude):
            log.info(f"Found game window (exact): '{get_window_title(hwnd)}'")
            return hwnd

    # Try partial match — enumerate ALL windows
    _found_windows = []
    _all_pokemmo = []  # For debug logging

    def _enum_callback(h, _lparam):
        if not user32.IsWindowVisible(h):
            return True
        length = user32.GetWindowTextLengthW(h)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(h, buf, length + 1)
            wt = buf.value.lower()
            if "poke" in wt or "mmo" in wt:
                _all_pokemmo.append(buf.value)
            if title.lower() in wt and not any(ex in wt for ex in _exclude):
                _found_windows.append((h, buf.value))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

    if _found_windows:
        # Prefer the largest window (the game, not a launcher/splash)
        best = _found_windows[0]
        if len(_found_windows) > 1:
            best_size = 0
            for h, name in _found_windows:
                rect = get_window_rect(h)
                if rect:
                    size = (rect[2] - rect[0]) * (rect[3] - rect[1])
                    if size > best_size:
                        best_size = size
                        best = (h, name)
        log.info(f"Found game window: '{best[1]}' (from {len(_found_windows)} candidates)")
        return best[0]

    # Log what we DID find for debugging
    if _all_pokemmo:
        log.warning(f"No game window matched. Similar windows found: {_all_pokemmo}")
    return None


def get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Get window position and size (left, top, right, bottom)."""
    rect = ctypes.wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def get_window_title(hwnd: int) -> str:
    """Read the window title text. May contain game location info."""
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    return ""


def get_window_size(hwnd: int) -> tuple[int, int] | None:
    """Get window width and height."""
    rect = get_window_rect(hwnd)
    if rect:
        return (rect[2] - rect[0], rect[3] - rect[1])
    return None


class ScreenCapture:
    """Captures the PokeMMO game window using BetterCam."""

    def __init__(self, window_title: str = "PokeMMO"):
        self.window_title = window_title
        self.camera = None
        self.hwnd: int | None = None
        self.window_rect: tuple[int, int, int, int] | None = None
        self._last_frame: np.ndarray | None = None

    def initialize(self) -> bool:
        """Initialize the capture engine. Returns True if game window found."""
        self.hwnd = find_window(self.window_title)
        if not self.hwnd:
            log.warning(f"Game window '{self.window_title}' not found")
            return False

        self.window_rect = get_window_rect(self.hwnd)
        if not self.window_rect:
            log.warning("Could not get window rect")
            return False

        try:
            import bettercam
            self.camera = bettercam.create(output_color="BGR")
            log.info(f"BetterCam initialized. Window: {self.window_rect}")
            return True
        except ImportError:
            log.warning("BetterCam not installed, using fallback capture")
            return self._init_fallback()
        except Exception as e:
            log.warning(f"BetterCam init failed: {e}, using fallback")
            return self._init_fallback()

    def _init_fallback(self) -> bool:
        """Initialize fallback capture using MSS."""
        try:
            import mss
            self.camera = mss.mss()
            log.info("Using MSS fallback capture")
            return True
        except ImportError:
            log.error("Neither BetterCam nor MSS available")
            return False

    def refresh_window(self) -> bool:
        """Refresh the game window position (call if window moved/resized)."""
        self.hwnd = find_window(self.window_title)
        if self.hwnd:
            self.window_rect = get_window_rect(self.hwnd)
            return self.window_rect is not None
        return False

    def capture_full(self) -> np.ndarray | None:
        """Capture the full game window."""
        if not self.window_rect:
            if not self.refresh_window():
                return self._last_frame

        try:
            if hasattr(self.camera, 'grab'):
                # BetterCam
                frame = self.camera.grab(region=self.window_rect)
            else:
                # MSS fallback
                left, top, right, bottom = self.window_rect
                monitor = {"left": left, "top": top, "width": right - left, "height": bottom - top}
                screenshot = self.camera.grab(monitor)
                frame = np.array(screenshot)[:, :, :3]  # Remove alpha channel

            if frame is not None:
                self._last_frame = frame
            return frame
        except Exception as e:
            log.debug(f"Capture failed: {e}")
            return self._last_frame

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray | None:
        """Capture a specific region relative to the game window.

        Args:
            x, y: Top-left corner relative to game window
            w, h: Width and height of region
        """
        if not self.window_rect:
            if not self.refresh_window():
                return None

        wl, wt, wr, wb = self.window_rect
        # Convert to absolute screen coordinates
        abs_region = (wl + x, wt + y, wl + x + w, wt + y + h)

        try:
            if hasattr(self.camera, 'grab'):
                return self.camera.grab(region=abs_region)
            else:
                monitor = {"left": abs_region[0], "top": abs_region[1],
                          "width": w, "height": h}
                screenshot = self.camera.grab(monitor)
                return np.array(screenshot)[:, :, :3]
        except Exception as e:
            log.debug(f"Region capture failed: {e}")
            return None

    def get_game_size(self) -> tuple[int, int] | None:
        """Get the current game window size."""
        if self.hwnd:
            return get_window_size(self.hwnd)
        return None

    def is_game_running(self) -> bool:
        """Check if the game window still exists."""
        if self.hwnd:
            return bool(user32.IsWindow(self.hwnd))
        return False

    def cleanup(self) -> None:
        """Clean up capture resources."""
        if self.camera:
            if hasattr(self.camera, 'release'):
                self.camera.release()
            elif hasattr(self.camera, 'close'):
                self.camera.close()
            self.camera = None


if __name__ == "__main__":
    cap = ScreenCapture()
    if cap.initialize():
        print(f"Game found! Window: {cap.window_rect}")
        print(f"Game size: {cap.get_game_size()}")

        frame = cap.capture_full()
        if frame is not None:
            print(f"Captured frame: {frame.shape}")
        else:
            print("No frame captured")

        cap.cleanup()
    else:
        print("PokeMMO window not found. Is the game running?")
