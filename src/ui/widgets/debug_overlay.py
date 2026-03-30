"""Debug overlay — shows OCR regions of interest as colored rectangles.

Toggle with F11. Shows exactly where the app is trying to read text,
so the user can see if the ROI positions match their game layout.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class DebugOverlay(QWidget):
    """Transparent overlay that draws colored rectangles on OCR regions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible = False
        self._regions: list[dict] = []
        self._game_rect: tuple[int, int, int, int] | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_game_rect(self, left: int, top: int, width: int, height: int) -> None:
        """Set the game window position and size."""
        self._game_rect = (left, top, width, height)

    def set_regions(self, regions: list[dict]) -> None:
        """Set the OCR regions to display.

        Each region: {"name": str, "x_ratio": float, "y_ratio": float,
                      "w_ratio": float, "h_ratio": float, "color": str}
        """
        self._regions = regions
        if self._visible:
            self.update()

    def toggle(self) -> None:
        """Toggle debug overlay visibility."""
        self._visible = not self._visible
        self.update()

    def paintEvent(self, event):
        if not self._visible or not self._regions:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get parent size as reference
        w = self.width()
        h = self.height()

        for region in self._regions:
            name = region.get("name", "")
            x = int(region["x_ratio"] * w)
            y = int(region["y_ratio"] * h)
            rw = int(region["w_ratio"] * w)
            rh = int(region["h_ratio"] * h)
            color_name = region.get("color", "red")

            color_map = {
                "red": QColor(255, 0, 0, 100),
                "green": QColor(0, 255, 0, 100),
                "blue": QColor(0, 100, 255, 100),
                "yellow": QColor(255, 255, 0, 100),
                "purple": QColor(200, 0, 255, 100),
            }
            fill_color = color_map.get(color_name, QColor(255, 0, 0, 100))
            border_color = QColor(fill_color.red(), fill_color.green(), fill_color.blue(), 200)

            # Draw filled rectangle
            painter.fillRect(x, y, rw, rh, fill_color)

            # Draw border
            pen = QPen(border_color, 2)
            painter.setPen(pen)
            painter.drawRect(x, y, rw, rh)

            # Draw label
            painter.setPen(QColor(255, 255, 255, 230))
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(x + 3, y + 12, name)

        painter.end()


# Default OCR regions for PokeMMO (ratios relative to game window)
# Calibrated from real PokeMMO screenshot (2026-03-31)
DEFAULT_OCR_REGIONS = [
    {
        "name": "Route Name",
        "x_ratio": 0.01,
        "y_ratio": 0.01,
        "w_ratio": 0.18,
        "h_ratio": 0.04,
        "color": "green",
    },
    {
        "name": "Opponent Name",
        "x_ratio": 0.52,
        "y_ratio": 0.05,
        "w_ratio": 0.35,
        "h_ratio": 0.04,
        "color": "red",
    },
    {
        "name": "Opponent Level",
        "x_ratio": 0.80,
        "y_ratio": 0.05,
        "w_ratio": 0.12,
        "h_ratio": 0.04,
        "color": "yellow",
    },
    {
        "name": "Battle Border (top)",
        "x_ratio": 0.0,
        "y_ratio": 0.0,
        "w_ratio": 1.0,
        "h_ratio": 0.05,
        "color": "blue",
    },
    {
        "name": "HP Bar Region",
        "x_ratio": 0.55,
        "y_ratio": 0.08,
        "w_ratio": 0.30,
        "h_ratio": 0.07,
        "color": "purple",
    },
]
