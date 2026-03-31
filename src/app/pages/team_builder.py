"""Team Builder page — build and analyze a team with sprites and type coverage."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGridLayout, QFrame, QPushButton, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..theme import COLORS, TYPE_COLORS
from ..sprite_cache import get_sprite
from ..widgets import TypeBadge
from ...utils.constants import TYPES
from ...data.type_chart import get_effectiveness, get_dual_effectiveness


class TeamSlot(QFrame):
    """A team slot showing a Pokemon sprite and info, or empty."""

    def __init__(self, slot_index: int, parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self.pokemon: dict | None = None
        self.setFixedSize(150, 180)
        self._setup_empty()

    def _setup_empty(self):
        self.setStyleSheet(f"""
            TeamSlot {{
                background-color: {COLORS['bg_card']};
                border: 2px dashed {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(f"Slot {self.slot_index + 1}")
        label.setFont(QFont("Segoe UI", 11))
        label.setStyleSheet(f"color: {COLORS['text_muted']};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        hint = QLabel("Empty")
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def set_pokemon(self, pokemon: dict) -> None:
        """Set a Pokemon in this slot."""
        self.pokemon = pokemon

        # Clear layout
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.setStyleSheet(f"""
            TeamSlot {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['accent_blue']};
                border-radius: 12px;
            }}
        """)

        # Sprite
        sprite_label = QLabel()
        sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = get_sprite(pokemon["id"], 80)
        if pixmap:
            sprite_label.setPixmap(pixmap)
        self.layout().addWidget(sprite_label)

        # Name
        name = QLabel(pokemon["name"])
        name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.layout().addWidget(name)

        # Types
        types_row = QHBoxLayout()
        types_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        types_row.setSpacing(3)
        t1 = QLabel(pokemon["type1"][:3])
        t1.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setFixedHeight(16)
        t1.setStyleSheet(f"color: white; background: {TYPE_COLORS.get(pokemon['type1'], '#888')}; "
                         f"border-radius: 3px; padding: 0 4px;")
        types_row.addWidget(t1)
        if pokemon.get("type2"):
            t2 = QLabel(pokemon["type2"][:3])
            t2.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t2.setFixedHeight(16)
            t2.setStyleSheet(f"color: white; background: {TYPE_COLORS.get(pokemon['type2'], '#888')}; "
                             f"border-radius: 3px; padding: 0 4px;")
            types_row.addWidget(t2)
        self.layout().addLayout(types_row)

    def clear(self) -> None:
        """Clear this slot."""
        self.pokemon = None
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._setup_empty()


class TeamBuilderPage(QWidget):
    """Team builder with type coverage matrix."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_slot = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Constructeur d Equipe")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # Search + add
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tape un nom de Pokemon et appuie Entree...")
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.returnPressed.connect(self._add_pokemon)
        search_row.addWidget(self.search_input)

        clear_btn = QPushButton("Tout Effacer")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['accent_red']};
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['accent_red']};
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        clear_btn.clicked.connect(self._clear_all)
        search_row.addWidget(clear_btn)
        layout.addLayout(search_row)

        # Team slots
        slots_row = QHBoxLayout()
        slots_row.setSpacing(12)
        self.slots: list[TeamSlot] = []
        for i in range(6):
            slot = TeamSlot(i)
            self.slots.append(slot)
            slots_row.addWidget(slot)
        layout.addLayout(slots_row)

        # Coverage analysis
        coverage_frame = QFrame()
        coverage_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        coverage_layout = QVBoxLayout(coverage_frame)
        coverage_layout.setContentsMargins(16, 12, 16, 12)

        cov_title = QLabel("Analyse de Couverture")
        cov_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        cov_title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        coverage_layout.addWidget(cov_title)

        self.coverage_label = QLabel("Ajoute des Pokemon pour voir la couverture")
        self.coverage_label.setFont(QFont("Consolas", 10))
        self.coverage_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.coverage_label.setWordWrap(True)
        coverage_layout.addWidget(self.coverage_label)

        self.weakness_label = QLabel("")
        self.weakness_label.setFont(QFont("Segoe UI", 10))
        self.weakness_label.setStyleSheet(f"color: {COLORS['accent_red']};")
        self.weakness_label.setWordWrap(True)
        coverage_layout.addWidget(self.weakness_label)

        layout.addWidget(coverage_frame)
        layout.addStretch()

    def _add_pokemon(self) -> None:
        """Add a Pokemon to the next empty slot."""
        name = self.search_input.text().strip()
        if not name or not self.db:
            return

        pokemon = self.db.get_pokemon_by_name(name)
        if not pokemon:
            results = self.db.search_pokemon(name, limit=1)
            if results:
                pokemon = results[0]

        if not pokemon:
            return

        # Find next empty slot
        for slot in self.slots:
            if slot.pokemon is None:
                slot.set_pokemon(pokemon)
                self.search_input.clear()
                self._update_coverage()
                return

        self.search_input.clear()

    def _clear_all(self) -> None:
        """Clear all team slots."""
        for slot in self.slots:
            slot.clear()
        self.coverage_label.setText("Ajoute des Pokemon pour voir la couverture")
        self.weakness_label.setText("")

    def _update_coverage(self) -> None:
        """Recalculate and display type coverage."""
        team = [s.pokemon for s in self.slots if s.pokemon]
        if not team:
            return

        # Offensive coverage
        covered = set()
        for p in team:
            p_types = [p["type1"]]
            if p.get("type2"):
                p_types.append(p["type2"])
            for atk in p_types:
                for def_type in TYPES:
                    if get_effectiveness(atk, def_type) > 1.0:
                        covered.add(def_type)

        uncovered = set(TYPES) - covered
        pct = len(covered) / len(TYPES) * 100

        cov_text = f"Offensive coverage: {pct:.0f}% ({len(covered)}/{len(TYPES)} types hit super-effectively)"
        if uncovered:
            cov_text += f"\nNot covered: {', '.join(sorted(uncovered))}"
        self.coverage_label.setText(cov_text)

        # Defensive weaknesses
        type_weak: dict[str, int] = {t: 0 for t in TYPES}
        for p in team:
            p_types = [p["type1"]]
            if p.get("type2"):
                p_types.append(p["type2"])
            for atk in TYPES:
                if get_dual_effectiveness(atk, p_types) > 1.0:
                    type_weak[atk] += 1

        dangers = {t: c for t, c in type_weak.items() if c >= 3}
        warnings = {t: c for t, c in type_weak.items() if c == 2}

        parts = []
        if dangers:
            d_parts = [f"{t} ({c}/{len(team)})" for t, c in sorted(dangers.items(), key=lambda x: -x[1])]
            parts.append(f"DANGER: {', '.join(d_parts)}")
        if warnings:
            w_parts = [f"{t} ({c}/{len(team)})" for t, c in sorted(warnings.items(), key=lambda x: -x[1])[:4]]
            parts.append(f"Watch: {', '.join(w_parts)}")
        if not dangers and not warnings:
            parts.append("Good defensive balance!")

        self.weakness_label.setText("\n".join(parts))
        if dangers:
            self.weakness_label.setStyleSheet(f"color: {COLORS['accent_red']};")
        elif warnings:
            self.weakness_label.setStyleSheet(f"color: {COLORS['accent_orange']};")
        else:
            self.weakness_label.setStyleSheet(f"color: {COLORS['accent_green']};")
