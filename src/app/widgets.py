"""Reusable widgets for the companion app — stat bars, radar chart, type badges."""
import math
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPolygonF, QBrush

from .theme import COLORS, TYPE_COLORS


class TypeBadge(QLabel):
    """Colored type badge widget."""

    def __init__(self, type_name: str, parent=None):
        super().__init__(type_name, parent)
        color = TYPE_COLORS.get(type_name, "#888")
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(65)
        self.setStyleSheet(f"""
            color: white;
            background-color: {color};
            border-radius: 4px;
            padding: 2px 8px;
        """)


class StatBar(QWidget):
    """Colored stat bar — shows a Pokemon stat value as a horizontal bar."""

    def __init__(self, label: str, value: int, max_val: int = 255, parent=None):
        super().__init__(parent)
        self.label = label
        self.value = value
        self.max_val = max_val
        self.setFixedHeight(22)
        self.setMinimumWidth(200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Label
        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(0, 0, 35, h, Qt.AlignmentFlag.AlignVCenter, self.label)

        # Value
        painter.drawText(36, 0, 30, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                         str(self.value))

        # Bar background
        bar_x = 72
        bar_w = w - bar_x - 4
        bar_h = 12
        bar_y = (h - bar_h) // 2
        painter.fillRect(bar_x, bar_y, bar_w, bar_h, QColor(COLORS["bg_secondary"]))

        # Bar fill
        ratio = min(self.value / self.max_val, 1.0)
        fill_w = int(bar_w * ratio)

        if self.value < 50:
            color = QColor("#ef5350")
        elif self.value < 80:
            color = QColor("#ffb74d")
        elif self.value < 100:
            color = QColor("#66bb6a")
        else:
            color = QColor("#42a5f5")

        painter.fillRect(bar_x, bar_y, fill_w, bar_h, color)

        # Border
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawRect(bar_x, bar_y, bar_w, bar_h)

        painter.end()


class RadarChart(QWidget):
    """Hexagonal radar chart for Pokemon base stats."""

    STAT_LABELS = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]

    def __init__(self, stats: list[int] | None = None, parent=None):
        super().__init__(parent)
        self.stats = stats or [0, 0, 0, 0, 0, 0]
        self.setFixedSize(200, 200)

    def set_stats(self, stats: list[int]) -> None:
        self.stats = stats[:6]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) - 25
        n = 6
        max_stat = 255

        # Draw grid lines (3 levels)
        for level in [0.33, 0.66, 1.0]:
            points = []
            for i in range(n):
                angle = math.radians(60 * i - 90)
                r = radius * level
                points.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
            polygon = QPolygonF(points)
            painter.setPen(QPen(QColor(COLORS["border"]), 1))
            painter.drawPolygon(polygon)

        # Draw axis lines
        for i in range(n):
            angle = math.radians(60 * i - 90)
            painter.setPen(QPen(QColor(COLORS["border"]), 1))
            painter.drawLine(
                QPointF(cx, cy),
                QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            )

        # Draw stat polygon
        stat_points = []
        for i, val in enumerate(self.stats):
            angle = math.radians(60 * i - 90)
            r = radius * min(val / max_stat, 1.0)
            stat_points.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))

        stat_polygon = QPolygonF(stat_points)
        fill_color = QColor(COLORS["accent_blue"])
        fill_color.setAlpha(80)
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(QColor(COLORS["accent_blue"]), 2))
        painter.drawPolygon(stat_polygon)

        # Draw labels
        painter.setPen(QColor(COLORS["text_primary"]))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for i, label in enumerate(self.STAT_LABELS):
            angle = math.radians(60 * i - 90)
            lx = cx + (radius + 18) * math.cos(angle)
            ly = cy + (radius + 18) * math.sin(angle)
            painter.drawText(
                QRectF(lx - 20, ly - 8, 40, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"{label}\n{self.stats[i]}"
            )

        painter.end()


class PokemonCard(QWidget):
    """A card widget showing a Pokemon sprite, name, and types."""

    def __init__(self, pokemon_id: int, name: str, type1: str,
                 type2: str | None = None, parent=None):
        super().__init__(parent)
        self.pokemon_id = pokemon_id
        self.setFixedSize(120, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QWidget:hover {{
                border-color: {COLORS['accent_blue']};
                background-color: {COLORS['bg_hover']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sprite
        from .sprite_cache import get_sprite
        sprite_label = QLabel()
        sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = get_sprite(pokemon_id, 64)
        if pixmap:
            sprite_label.setPixmap(pixmap)
        else:
            sprite_label.setText(f"#{pokemon_id}")
            sprite_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 20px;")
        layout.addWidget(sprite_label)

        # Name
        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
        layout.addWidget(name_label)

        # Type badges
        types_row = QHBoxLayout()
        types_row.setSpacing(2)
        types_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t1 = QLabel(type1[:3])
        t1.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setFixedHeight(14)
        t1.setStyleSheet(f"color: white; background: {TYPE_COLORS.get(type1, '#888')}; "
                         f"border-radius: 2px; padding: 0 4px; border: none;")
        types_row.addWidget(t1)

        if type2:
            t2 = QLabel(type2[:3])
            t2.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t2.setFixedHeight(14)
            t2.setStyleSheet(f"color: white; background: {TYPE_COLORS.get(type2, '#888')}; "
                             f"border-radius: 2px; padding: 0 4px; border: none;")
            types_row.addWidget(t2)

        layout.addLayout(types_row)
