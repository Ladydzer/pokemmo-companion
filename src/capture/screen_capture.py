"""Screen capture engine using BetterCam for PokeMMO window."""
import time
import ctypes
import ctypes.wintypes
import numpy as np

from ..utils.logger import log

# Win32 API for finding game window
user32 = ctypes.windll.user32

# Set DPI awareness early — ensures GetWindowRect returns unscaled pixel coordinates
# PROCESS_PER_MONITOR_DPI_AWARE = 2
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    # Fallback for older Windows (pre-8.1)
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def _normalize_title(text: str) -> str:
    """Normalize window title for matching — handles Cyrillic lookalikes.

    PokeMMO uses a Cyrillic М (U+041C) instead of Latin M in its window title.
    This makes "PokeMMO" != "PokeMМO" even though they look identical.
    """
    import unicodedata
    # Replace common Cyrillic lookalikes with Latin equivalents
    cyrillic_to_latin = {
        '\u0410': 'A', '\u0412': 'B', '\u0421': 'C', '\u0415': 'E',
        '\u041D': 'H', '\u041A': 'K', '\u041C': 'M', '\u041E': 'O',
        '\u0420': 'P', '\u0422': 'T', '\u0425': 'X',
        '\u0430': 'a', '\u0432': 'b', '\u0441': 'c', '\u0435': 'e',
        '\u043D': 'h', '\u043A': 'k', '\u043C': 'm', '\u043E': 'o',
        '\u0440': 'p', '\u0442': 't', '\u0445': 'x',
    }
    return ''.join(cyrillic_to_latin.get(c, c) for c in text)


def find_window(title: str = "PokeMMO") -> int | None:
    """Find the PokeMMO game window handle.

    Handles Cyrillic М in PokeMMO's window title (PokeMМO vs PokeMMO).
    Excludes our own overlay/companion windows to avoid self-detection.
    """
    _exclude = ["companion", "overlay", "runner"]
    title_norm = _normalize_title(title).lower()

    # First try exact match
    hwnd = user32.FindWindowW(None, title)
    if hwnd != 0:
        wt = get_window_title(hwnd).lower()
        if not any(ex in wt for ex in _exclude):
            log.info(f"Found game window (exact): '{get_window_title(hwnd)}'")
            return hwnd

    # Also try with Cyrillic М variant
    title_cyrillic = title.replace("M", "\u041C")  # Replace second M with Cyrillic
    hwnd2 = user32.FindWindowW(None, title_cyrillic)
    if hwnd2 != 0:
        wt = get_window_title(hwnd2).lower()
        if not any(ex in wt for ex in _exclude):
            log.info(f"Found game window (Cyrillic): '{get_window_title(hwnd2)}'")
            return hwnd2

    # Enumerate all windows with normalized title matching
    _found_windows = []

    def _enum_callback(h, _lparam):
        if not user32.IsWindowVisible(h):
            return True
        length = user32.GetWindowTextLengthW(h)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(h, buf, length + 1)
            wt_norm = _normalize_title(buf.value).lower()
            if title_norm in wt_norm and not any(ex in wt_norm for ex in _exclude):
                _found_windows.append((h, buf.value))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

    if _found_windows:
        # Prefer the largest window (the game, not a launcher)
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


def capture_window_by_hwnd(hwnd: int) -> np.ndarray | None:
    """Capture a specific window by its HWND using PrintWindow API.

    Works even if the window is partially covered by other windows.
    Returns BGR numpy array or None.
    """
    try:
        import win32gui
        import win32ui
        import win32con

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bottom - top
        if w <= 0 or h <= 0:
            return None

        # Get device contexts
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        # Create bitmap
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bitmap)

        # PrintWindow captures the window content even if covered
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)  # PW_RENDERFULLCONTENT=3

        if result:
            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            frame = np.frombuffer(bmpstr, dtype=np.uint8).reshape(
                bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4
            )
            frame = frame[:, :, :3]  # BGRA -> BGR (drop alpha)
        else:
            frame = None

        # Cleanup
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return frame
    except ImportError:
        return None
    except Exception as e:
        log.warning(f"PrintWindow capture failed: {e}")
        return None


# === Capture backends ===

class CaptureBackend:
    """Protocol for capture backends. Subclass to add new capture methods."""

    name: str = "base"

    def initialize(self, hwnd: int, window_rect: tuple) -> bool:
        """Initialize the backend. Returns True if ready."""
        raise NotImplementedError

    def capture(self, hwnd: int, window_rect: tuple) -> np.ndarray | None:
        """Capture a frame. Returns BGR numpy array or None."""
        raise NotImplementedError

    def cleanup(self) -> None:
        """Release resources."""
        pass


class PrintWindowBackend(CaptureBackend):
    """Captures via Win32 PrintWindow API. Works even if window is covered."""

    name = "printwindow"

    def initialize(self, hwnd: int, window_rect: tuple) -> bool:
        frame = capture_window_by_hwnd(hwnd)
        if frame is not None:
            log.info(f"Capture engine: PrintWindow (HWND, {frame.shape[1]}x{frame.shape[0]})")
            return True
        return False

    def capture(self, hwnd: int, window_rect: tuple) -> np.ndarray | None:
        frame = capture_window_by_hwnd(hwnd)
        if frame is not None:
            # Crop window borders (8px on maximized windows)
            h, w = frame.shape[:2]
            border = 8
            if h > border * 2 and w > border * 2:
                frame = frame[border:h-border, border:w-border]
        return frame


class PILBackend(CaptureBackend):
    """Captures via PIL ImageGrab. Basic fallback, always available."""

    name = "pil"

    def initialize(self, hwnd: int, window_rect: tuple) -> bool:
        try:
            from PIL import ImageGrab
            log.info("Capture engine: PIL (basic)")
            return True
        except ImportError:
            return False

    def capture(self, hwnd: int, window_rect: tuple) -> np.ndarray | None:
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=window_rect)
            return np.array(screenshot)[:, :, ::-1]  # RGB -> BGR
        except Exception:
            return None


class BetterCamBackend(CaptureBackend):
    """Captures via BetterCam (GPU-accelerated screen capture)."""

    name = "bettercam"

    def __init__(self):
        self._cam = None

    def initialize(self, hwnd: int, window_rect: tuple) -> bool:
        try:
            import bettercam
            self._cam = bettercam.create(output_color="BGR")
            log.info("Capture engine: BetterCam")
            return True
        except (ImportError, Exception) as e:
            log.info(f"BetterCam unavailable: {e}")
            return False

    def capture(self, hwnd: int, window_rect: tuple) -> np.ndarray | None:
        if not self._cam:
            return None
        frame = self._cam.grab(region=window_rect)
        if frame is None:
            frame = self._cam.grab()
            if frame is not None and window_rect:
                left, top, right, bottom = window_rect
                frame = frame[top:bottom, left:right]
        return frame

    def cleanup(self) -> None:
        if self._cam:
            if hasattr(self._cam, 'release'):
                self._cam.release()
            elif hasattr(self._cam, 'close'):
                self._cam.close()
            self._cam = None


# Backend registry — order = priority for auto-selection
BACKENDS = {
    "printwindow": PrintWindowBackend,
    "bettercam": BetterCamBackend,
    "pil": PILBackend,
}


class ScreenCapture:
    """Captures the PokeMMO game window using configurable backends.

    Default priority: PrintWindow > BetterCam > PIL.
    Override via config: capture.backend = "printwindow" | "bettercam" | "pil"
    """

    def __init__(self, window_title: str = "PokeMMO", backend_name: str = "auto"):
        self.window_title = window_title
        self.backend: CaptureBackend | None = None
        self.backend_name = backend_name
        self.hwnd: int | None = None
        self.window_rect: tuple[int, int, int, int] | None = None
        self._last_frame: np.ndarray | None = None
        self._pil_fallback = PILBackend()  # always-available fallback

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

        # Clamp to screen bounds
        left, top, right, bottom = self.window_rect
        try:
            screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        except Exception:
            screen_w, screen_h = 1920, 1080
        left = max(0, left)
        top = max(0, top)
        right = max(0, min(right, screen_w))
        bottom = max(0, min(bottom, screen_h))
        w = right - left
        h = bottom - top
        if w < 100 or h < 100:
            log.warning(f"Window too small or invalid: {w}x{h} (raw rect: {self.window_rect}). Window minimized?")
            return False
        self.window_rect = (left, top, right, bottom)
        log.info(f"Game window found: {w}x{h} at {self.window_rect} (screen: {screen_w}x{screen_h})")

        # Select backend
        if self.backend_name != "auto" and self.backend_name in BACKENDS:
            # Explicit backend requested
            backend = BACKENDS[self.backend_name]()
            if backend.initialize(self.hwnd, self.window_rect):
                self.backend = backend
                return True
            log.warning(f"Requested backend '{self.backend_name}' failed, trying auto...")

        # Auto-select: try each backend in priority order
        for name, cls in BACKENDS.items():
            backend = cls()
            if backend.initialize(self.hwnd, self.window_rect):
                self.backend = backend
                return True

        log.error("No capture backend available! Install: pip install pywin32 or pip install Pillow")
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

        frame = None
        if self.backend:
            try:
                frame = self.backend.capture(self.hwnd, self.window_rect)
            except Exception as e:
                log.warning(f"Capture failed ({self.backend.name}): {e}")

        # PIL fallback if primary backend fails
        if frame is None:
            try:
                frame = self._pil_fallback.capture(self.hwnd, self.window_rect)
                if frame is not None and not hasattr(self, '_pil_warned'):
                    self._pil_warned = True
                    log.warning(f"Backend {self.backend.name if self.backend else '?'} failed — PIL fallback")
            except Exception:
                pass

        if frame is not None:
            self._last_frame = frame
        return frame if frame is not None else self._last_frame

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray | None:
        """Capture a specific region relative to the game window."""
        full = self.capture_full()
        if full is None:
            return None
        # Crop from full frame (simpler, works with all backends)
        fh, fw = full.shape[:2]
        x = min(x, fw)
        y = min(y, fh)
        return full[y:y+h, x:x+w]

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
        if self.backend:
            self.backend.cleanup()
            self.backend = None


if __name__ == "__main__":
    cap = ScreenCapture()
    if cap.initialize():
        print(f"Game found! Window: {cap.window_rect}")
        print(f"Backend: {cap.backend.name}")
        print(f"Game size: {cap.get_game_size()}")

        frame = cap.capture_full()
        if frame is not None:
            print(f"Captured frame: {frame.shape}")
        else:
            print("No frame captured")

        cap.cleanup()
    else:
        print("PokeMMO window not found. Is the game running?")
