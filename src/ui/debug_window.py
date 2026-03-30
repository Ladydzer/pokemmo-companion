"""Debug window — transparent overlay that draws colored rectangles on the game.

This is a SEPARATE window from the main overlay, positioned exactly over
the game window. It draws rectangles showing where the OCR tries to read.
"""
import ctypes
import ctypes.wintypes
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

from ..capture.screen_capture import find_window, get_window_rect

user32 = ctypes.windll.user32

# OCR regions (ratios relative to game window)
OCR_REGIONS = [
    ("Route Name", 0.01, 0.01, 0.18, 0.04, QColor(0, 255, 0, 120)),
    ("Opponent Name", 0.52, 0.05, 0.35, 0.04, QColor(255, 0, 0, 120)),
    ("Opponent Level", 0.80, 0.05, 0.12, 0.04, QColor(255, 255, 0, 120)),
    ("Battle Top", 0.0, 0.0, 1.0, 0.05, QColor(0, 100, 255, 60)),
    ("HP Bar", 0.55, 0.08, 0.30, 0.07, QColor(200, 0, 255, 80)),
]


class DebugWindow(QWidget):
    """Transparent window that overlays the game with OCR region rectangles."""

    def __init__(self):
        super().__init__()
        self._active = False
        self._game_rect = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowTitle("PokeMMO Companion Debug")

        # Timer to follow game window position
        self._track_timer = QTimer()
        self._track_timer.timeout.connect(self._track_game)
        self._track_timer.setInterval(500)

    def toggle(self) -> None:
        """Toggle debug overlay on/off."""
        self._active = not self._active
        if self._active:
            self._track_game()
            self._track_timer.start()
            self.show()
        else:
            self._track_timer.stop()
            self.hide()

    def _track_game(self) -> None:
        """Find and follow the game window."""
        hwnd = find_window("PokeMMO")
        if hwnd:
            rect = get_window_rect(hwnd)
            if rect:
                left, top, right, bottom = rect
                w = right - left
                h = bottom - top
                self._game_rect = (left, top, w, h)
                self.setGeometry(left, top, w, h)
                self.update()

    def paintEvent(self, event):
        if not self._active or not self._game_rect:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        for name, xr, yr, wr, hr, color in OCR_REGIONS:
            x = int(xr * w)
            y = int(yr * h)
            rw = int(wr * w)
            rh = int(hr * h)

            # Fill
            painter.fillRect(x, y, rw, rh, color)

            # Border
            border = QColor(color.red(), color.green(), color.blue(), 220)
            painter.setPen(QPen(border, 2))
            painter.drawRect(x, y, rw, rh)

            # Label
            painter.setPen(QColor(255, 255, 255, 240))
            painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            painter.drawText(x + 4, y + 14, name)

        painter.end()
