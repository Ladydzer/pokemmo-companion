"""Battle Assistant page — interactive type chart with sprites and suggestions."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGridLayout, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..theme import COLORS, TYPE_COLORS
from ..sprite_cache import get_sprite
from ..widgets import TypeBadge, StatBar, RadarChart
from ...utils.constants import TYPES
from ...data.type_chart import get_battle_summary, get_dual_effectiveness


class TypeChartGrid(QWidget):
    """Interactive 17x17 type effectiveness grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Type Effectiveness Chart")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        layout.addWidget(title)

        # Grid
        grid = QGridLayout()
        grid.setSpacing(1)

        # Header row (defending types)
        header = QLabel("ATK\\DEF")
        header.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_muted']};")
        header.setFixedSize(45, 22)
        grid.addWidget(header, 0, 0)

        for j, def_type in enumerate(TYPES):
            lbl = QLabel(def_type[:3])
            lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(28, 22)
            color = TYPE_COLORS.get(def_type, "#888")
            lbl.setStyleSheet(f"color: white; background: {color}; border-radius: 2px;")
            grid.addWidget(lbl, 0, j + 1)

        # Rows (attacking types)
        for i, atk_type in enumerate(TYPES):
            # Row header
            lbl = QLabel(atk_type[:3])
            lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(45, 22)
            color = TYPE_COLORS.get(atk_type, "#888")
            lbl.setStyleSheet(f"color: white; background: {color}; border-radius: 2px;")
            grid.addWidget(lbl, i + 1, 0)

            # Effectiveness cells
            for j, def_type in enumerate(TYPES):
                mult = get_dual_effectiveness(atk_type, [def_type])
                cell = QLabel()
                cell.setFixedSize(28, 22)
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(QFont("Consolas", 7, QFont.Weight.Bold))

                if mult >= 2.0:
                    cell.setText("2")
                    cell.setStyleSheet("color: white; background: #c62828; border-radius: 2px;")
                elif mult == 0.0:
                    cell.setText("0")
                    cell.setStyleSheet("color: white; background: #1a237e; border-radius: 2px;")
                elif mult <= 0.5:
                    cell.setText(u"\u00BD")
                    cell.setStyleSheet("color: white; background: #1b5e20; border-radius: 2px;")
                else:
                    cell.setText("")
                    cell.setStyleSheet(f"background: {COLORS['bg_secondary']}; border-radius: 2px;")

                grid.addWidget(cell, i + 1, j + 1)

        layout.addLayout(grid)


class BattlePage(QWidget):
    """Battle Assistant page with type lookup and interactive chart."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Battle Assistant")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # Quick lookup
        lookup_frame = QFrame()
        lookup_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        lookup_layout = QVBoxLayout(lookup_frame)
        lookup_layout.setContentsMargins(16, 12, 16, 12)

        lookup_title = QLabel("Quick Type Lookup")
        lookup_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lookup_title.setStyleSheet(f"color: {COLORS['accent_red']};")
        lookup_layout.addWidget(lookup_title)

        # Search
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter Pokemon name (e.g., Geodude)")
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.returnPressed.connect(self._lookup)
        self.search_input.textChanged.connect(self._on_search_change)
        search_row.addWidget(self.search_input)
        lookup_layout.addLayout(search_row)

        # Result area
        self.result_widget = QWidget()
        self.result_layout = QHBoxLayout(self.result_widget)
        self.result_layout.setContentsMargins(0, 8, 0, 0)
        self.result_layout.setSpacing(16)

        # Left: sprite + info
        self.info_col = QVBoxLayout()
        self.info_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_sprite = QLabel()
        self.result_sprite.setFixedSize(96, 96)
        self.result_sprite.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_col.addWidget(self.result_sprite)
        self.result_name = QLabel("")
        self.result_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.result_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_col.addWidget(self.result_name)
        self.result_types_layout = QHBoxLayout()
        self.result_types_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_col.addLayout(self.result_types_layout)
        self.result_layout.addLayout(self.info_col)

        # Right: weaknesses / resistances / immunities
        self.matchup_col = QVBoxLayout()
        self.matchup_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.weak_label = QLabel("")
        self.weak_label.setFont(QFont("Segoe UI", 10))
        self.weak_label.setStyleSheet(f"color: {COLORS['accent_red']};")
        self.weak_label.setWordWrap(True)
        self.matchup_col.addWidget(self.weak_label)

        self.resist_label = QLabel("")
        self.resist_label.setFont(QFont("Segoe UI", 10))
        self.resist_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        self.resist_label.setWordWrap(True)
        self.matchup_col.addWidget(self.resist_label)

        self.immune_label = QLabel("")
        self.immune_label.setFont(QFont("Segoe UI", 10))
        self.immune_label.setStyleSheet(f"color: {COLORS['accent_blue']};")
        self.matchup_col.addWidget(self.immune_label)

        self.result_layout.addLayout(self.matchup_col, 2)

        self.result_widget.hide()
        lookup_layout.addWidget(self.result_widget)

        layout.addWidget(lookup_frame)

        # Type chart in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        chart = TypeChartGrid()
        scroll.setWidget(chart)
        layout.addWidget(scroll)

    def _on_search_change(self, text: str) -> None:
        if len(text) >= 3:
            self._lookup()

    def _lookup(self) -> None:
        """Look up a Pokemon and show type matchups."""
        name = self.search_input.text().strip()
        if not name or not self.db:
            return

        pokemon = self.db.get_pokemon_by_name(name)
        if not pokemon:
            results = self.db.search_pokemon(name, limit=1)
            if results:
                pokemon = results[0]

        if not pokemon:
            self.result_widget.hide()
            return

        self.result_widget.show()

        # Sprite
        pixmap = get_sprite(pokemon["id"], 96)
        if pixmap:
            self.result_sprite.setPixmap(pixmap)

        # Name
        self.result_name.setText(f"#{pokemon['id']:03d} {pokemon['name']}")

        # Types
        while self.result_types_layout.count():
            item = self.result_types_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.result_types_layout.addWidget(TypeBadge(pokemon["type1"]))
        if pokemon.get("type2"):
            self.result_types_layout.addWidget(TypeBadge(pokemon["type2"]))

        # Battle summary
        types = [pokemon["type1"]]
        if pokemon.get("type2"):
            types.append(pokemon["type2"])
        summary = get_battle_summary(types)

        # Weaknesses
        weak = summary["weak_to"]
        if weak:
            parts = [f"{t} x{m:g}" for t, m in weak.items()]
            self.weak_label.setText(f"WEAK TO: {', '.join(parts)}")
        else:
            self.weak_label.setText("WEAK TO: None")

        # Resistances
        resists = summary["resists"]
        if resists:
            parts = [f"{t} x{m:g}" for t, m in resists.items()]
            self.resist_label.setText(f"RESISTS: {', '.join(parts)}")
        else:
            self.resist_label.setText("RESISTS: None")

        # Immunities
        immune = summary["immune_to"]
        if immune:
            self.immune_label.setText(f"IMMUNE TO: {', '.join(immune)}")
        else:
            self.immune_label.setText("IMMUNE TO: None")

    def show_opponent(self, battle_info: dict) -> None:
        """Auto-show opponent from overlay detection."""
        name = battle_info.get("name", "")
        if name:
            self.search_input.setText(name)
            self._lookup()
