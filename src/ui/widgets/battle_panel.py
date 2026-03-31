"""Battle assistant panel — compact and extended modes.

Compact: opponent name + type icons + weakness icons (glanceable in 1 second)
Extended: full type chart, suggestions, stats
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

# Type colors for visual identification (Pokemon official colors)
TYPE_COLORS = {
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0",
    "Electric": "#F7D02C", "Grass": "#7AC74C", "Ice": "#96D9D6",
    "Fighting": "#C22E28", "Poison": "#A33EA1", "Ground": "#E2BF65",
    "Flying": "#A98FF3", "Psychic": "#F95587", "Bug": "#A6B91A",
    "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC",
    "Dark": "#705746", "Steel": "#B7B7CE",
}


class TypeBadge(QLabel):
    """Small colored badge showing a Pokemon type."""

    def __init__(self, type_name: str, parent=None):
        super().__init__(type_name, parent)
        color = TYPE_COLORS.get(type_name, "#888888")
        self.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(18)
        self.setMinimumWidth(55)
        self.setStyleSheet(f"""
            color: white;
            background-color: {color};
            border-radius: 3px;
            padding: 1px 6px;
        """)


class EffectivenessBadge(QLabel):
    """Badge showing type effectiveness with color coding."""

    def __init__(self, type_name: str, multiplier: float, parent=None):
        super().__init__(parent)
        color = TYPE_COLORS.get(type_name, "#888888")
        mult_str = f"x{multiplier:g}"

        # Color intensity based on multiplier
        if multiplier >= 4.0:
            bg = "#D32F2F"  # Deep red for x4
            text = f"!! {type_name} {mult_str}"
        elif multiplier >= 2.0:
            bg = "#F44336"  # Red for x2
            text = f"! {type_name} {mult_str}"
        elif multiplier == 0.0:
            bg = "#1565C0"  # Blue for immune
            text = f"X {type_name} x0"
        elif multiplier <= 0.25:
            bg = "#2E7D32"  # Dark green for x0.25
            text = f"{type_name} {mult_str}"
        else:
            bg = "#388E3C"  # Green for x0.5
            text = f"{type_name} {mult_str}"

        self.setText(text)
        self.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(18)
        self.setStyleSheet(f"""
            color: white;
            background-color: {bg};
            border-radius: 3px;
            padding: 1px 4px;
        """)


class BattlePanelWidget(QWidget):
    """Battle assistant panel with compact and extended modes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_extended = False
        self._current_info: dict | None = None
        self._setup_ui()
        self.hide()  # Hidden until battle starts

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(3)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255, 100, 100, 100);")
        self.main_layout.addWidget(sep)

        # Opponent name + types (always visible)
        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #EF5350;")
        self.main_layout.addWidget(self.name_label)

        # Type badges row
        self.type_row = QHBoxLayout()
        self.type_row.setSpacing(4)
        self.type_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addLayout(self.type_row)

        # Compact weakness summary (always visible)
        self.compact_weak_label = QLabel("")
        self.compact_weak_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.compact_weak_label.setStyleSheet("color: #FFCDD2;")
        self.compact_weak_label.setWordWrap(True)
        self.main_layout.addWidget(self.compact_weak_label)

        # Extended details container
        self.extended_container = QWidget()
        self.extended_layout = QVBoxLayout(self.extended_container)
        self.extended_layout.setContentsMargins(0, 4, 0, 0)
        self.extended_layout.setSpacing(2)
        self.extended_container.hide()
        self.main_layout.addWidget(self.extended_container)

        # Weaknesses detail (extended)
        self.weak_header = QLabel("FAIBLE CONTRE :")
        self.weak_header.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.weak_header.setStyleSheet("color: #EF9A9A;")
        self.extended_layout.addWidget(self.weak_header)

        self.weak_badges_layout = QHBoxLayout()
        self.weak_badges_layout.setSpacing(3)
        self.weak_badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.extended_layout.addLayout(self.weak_badges_layout)

        # Resistances detail (extended)
        self.resist_header = QLabel("RESISTE :")
        self.resist_header.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.resist_header.setStyleSheet("color: #A5D6A7;")
        self.extended_layout.addWidget(self.resist_header)

        self.resist_badges_layout = QHBoxLayout()
        self.resist_badges_layout.setSpacing(3)
        self.resist_badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.extended_layout.addLayout(self.resist_badges_layout)

        # Immunities (extended)
        self.immune_label = QLabel("")
        self.immune_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.immune_label.setStyleSheet("color: #90CAF9;")
        self.extended_layout.addWidget(self.immune_label)

        # Stats (extended)
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Consolas", 8))
        self.stats_label.setStyleSheet("color: #B0BEC5;")
        self.extended_layout.addWidget(self.stats_label)

    def show_battle(self, battle_info: dict) -> None:
        """Display battle information for an opponent.

        Args:
            battle_info: {
                "name": str,
                "level": int|None,
                "types": list[str],
                "battle_summary": dict|None,
                "pokemon_data": dict|None,
            }
        """
        self._current_info = battle_info
        name = battle_info.get("name", "???")
        level = battle_info.get("level")
        types = battle_info.get("types", [])
        summary = battle_info.get("battle_summary")
        pokemon_data = battle_info.get("pokemon_data")

        # Name + level
        name_text = f"VS: {name}"
        if level:
            name_text += f" Lv.{level}"
        self.name_label.setText(name_text)

        # Clear old type badges
        self._clear_layout(self.type_row)
        for t in types:
            self.type_row.addWidget(TypeBadge(t))
        self.type_row.addStretch()

        if summary:
            # Compact: show top weaknesses as text
            weak = summary.get("weak_to", {})
            immune = summary.get("immune_to", [])
            compact_parts = []
            for t, m in list(weak.items())[:4]:
                prefix = "!!" if m >= 4 else "!"
                compact_parts.append(f"{prefix}{t}")
            if immune:
                compact_parts.append(f"IMMUNE:{','.join(immune)}")
            self.compact_weak_label.setText("  ".join(compact_parts))

            # Extended: weakness badges
            self._clear_layout(self.weak_badges_layout)
            for t, m in weak.items():
                self.weak_badges_layout.addWidget(EffectivenessBadge(t, m))

            # Extended: resistance badges
            self._clear_layout(self.resist_badges_layout)
            resists = summary.get("resists", {})
            for t, m in list(resists.items())[:6]:
                self.resist_badges_layout.addWidget(EffectivenessBadge(t, m))

            # Immunities
            if immune:
                self.immune_label.setText(f"IMMUNE A : {', '.join(immune)}")
                self.immune_label.show()
            else:
                self.immune_label.hide()
        else:
            self.compact_weak_label.setText("Donnees de type indisponibles")

        # Stats (extended)
        if pokemon_data:
            stats = (f"HP:{pokemon_data.get('hp',0)} "
                     f"Atk:{pokemon_data.get('attack',0)} "
                     f"Def:{pokemon_data.get('defense',0)} "
                     f"SpA:{pokemon_data.get('sp_attack',0)} "
                     f"SpD:{pokemon_data.get('sp_defense',0)} "
                     f"Spe:{pokemon_data.get('speed',0)}")
            self.stats_label.setText(stats)
            self.stats_label.show()
        else:
            self.stats_label.hide()

        self.show()

    def hide_battle(self) -> None:
        """Hide battle panel (battle ended)."""
        self._current_info = None
        self.hide()

    def toggle_extended(self) -> None:
        """Toggle between compact and extended mode."""
        self._is_extended = not self._is_extended
        if self._is_extended:
            self.extended_container.show()
        else:
            self.extended_container.hide()

    def set_extended(self, extended: bool) -> None:
        """Set extended mode on/off."""
        self._is_extended = extended
        if extended:
            self.extended_container.show()
        else:
            self.extended_container.hide()

    def _clear_layout(self, layout):
        """Remove all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
