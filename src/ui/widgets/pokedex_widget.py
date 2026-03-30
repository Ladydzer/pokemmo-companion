"""Pokedex widget — search and display Pokemon information."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .battle_panel import TypeBadge


class PokedexWidget(QWidget):
    """Searchable Pokedex with stats, types, and locations."""

    pokemon_selected = pyqtSignal(dict)  # Emitted when a Pokemon is selected

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(156, 39, 176, 80);")
        layout.addWidget(sep)

        # Header
        header = QLabel("Pokedex")
        header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header.setStyleSheet("color: #CE93D8;")
        layout.addWidget(header)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Pokemon...")
        self.search_input.setFont(QFont("Segoe UI", 9))
        self.search_input.setStyleSheet("""
            QLineEdit {
                color: #E0E0E0;
                background-color: rgba(40, 40, 60, 200);
                border: 1px solid rgba(156, 39, 176, 100);
                border-radius: 4px;
                padding: 3px 6px;
            }
        """)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        # Results area
        self.results_label = QLabel("")
        self.results_label.setFont(QFont("Consolas", 8))
        self.results_label.setStyleSheet("color: #E0E0E0;")
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)

        # Pokemon detail area
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(2)
        self.detail_widget.hide()
        layout.addWidget(self.detail_widget)

        # Name + number
        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #FFFFFF;")
        self.detail_layout.addWidget(self.name_label)

        # Types row
        self.types_layout = QHBoxLayout()
        self.types_layout.setSpacing(4)
        self.types_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.detail_layout.addLayout(self.types_layout)

        # Stats
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Consolas", 8))
        self.stats_label.setStyleSheet("color: #B0BEC5;")
        self.detail_layout.addWidget(self.stats_label)

        # Abilities
        self.abilities_label = QLabel("")
        self.abilities_label.setFont(QFont("Segoe UI", 8))
        self.abilities_label.setStyleSheet("color: #90A4AE;")
        self.detail_layout.addWidget(self.abilities_label)

        # Locations
        self.locations_label = QLabel("")
        self.locations_label.setFont(QFont("Consolas", 8))
        self.locations_label.setStyleSheet("color: #A5D6A7;")
        self.locations_label.setWordWrap(True)
        self.detail_layout.addWidget(self.locations_label)

    def _on_search(self, text: str) -> None:
        """Handle search input changes."""
        if not self.db or len(text) < 2:
            self.results_label.setText("")
            self.detail_widget.hide()
            return

        # Search for Pokemon
        results = self.db.search_pokemon(text, limit=5)
        if not results:
            self.results_label.setText("No Pokemon found")
            self.detail_widget.hide()
            return

        if len(results) == 1 or text.lower() == results[0]["name"].lower():
            # Show detailed view for exact/single match
            self._show_detail(results[0])
            self.results_label.setText("")
        else:
            # Show search results list
            lines = []
            for p in results:
                t2 = f"/{p['type2']}" if p.get('type2') else ""
                lines.append(f"#{p['id']:03d} {p['name']} ({p['type1']}{t2})")
            self.results_label.setText("\n".join(lines))
            self.detail_widget.hide()

    def _show_detail(self, pokemon: dict) -> None:
        """Show detailed Pokemon information."""
        self.detail_widget.show()

        # Name + number
        self.name_label.setText(f"#{pokemon['id']:03d} {pokemon['name']}")

        # Type badges
        while self.types_layout.count():
            item = self.types_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.types_layout.addWidget(TypeBadge(pokemon["type1"]))
        if pokemon.get("type2"):
            self.types_layout.addWidget(TypeBadge(pokemon["type2"]))
        self.types_layout.addStretch()

        # Stats with bar visualization
        stats = [
            ("HP", pokemon.get("hp", 0)),
            ("Atk", pokemon.get("attack", 0)),
            ("Def", pokemon.get("defense", 0)),
            ("SpA", pokemon.get("sp_attack", 0)),
            ("SpD", pokemon.get("sp_defense", 0)),
            ("Spe", pokemon.get("speed", 0)),
        ]
        total = sum(v for _, v in stats)
        stat_lines = []
        for name, val in stats:
            bar_len = val // 10
            bar = "#" * bar_len
            stat_lines.append(f"{name:3}: {val:3} {bar}")
        stat_lines.append(f"BST: {total}")
        self.stats_label.setText("\n".join(stat_lines))

        # Abilities
        abilities = []
        if pokemon.get("ability1"):
            abilities.append(pokemon["ability1"])
        if pokemon.get("ability2"):
            abilities.append(pokemon["ability2"])
        if pokemon.get("hidden_ability"):
            abilities.append(f"{pokemon['hidden_ability']} (HA)")
        self.abilities_label.setText(f"Abilities: {', '.join(abilities)}" if abilities else "")

        # Locations
        if self.db:
            locations = self.db.get_pokemon_locations(pokemon["name"])
            if locations:
                loc_lines = ["Locations:"]
                seen = set()
                for loc in locations[:6]:
                    key = f"{loc['route_name']}_{loc['region']}"
                    if key not in seen:
                        seen.add(key)
                        loc_lines.append(
                            f"  {loc['route_name']} ({loc['region']}) "
                            f"Lv.{loc['level_min']}-{loc['level_max']}"
                        )
                self.locations_label.setText("\n".join(loc_lines))
            else:
                self.locations_label.setText("Locations: Not found in wild")

        self.pokemon_selected.emit(pokemon)

    def show_pokemon(self, name: str) -> None:
        """Programmatically show a Pokemon's details."""
        if not self.db:
            return
        pokemon = self.db.get_pokemon_by_name(name)
        if pokemon:
            self.search_input.setText(name)
            self._show_detail(pokemon)
