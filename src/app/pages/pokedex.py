"""Pokedex page — grid of Pokemon sprites with detailed view."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QGridLayout, QFrame, QStackedWidget, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..theme import COLORS
from ..sprite_cache import get_sprite
from ..widgets import TypeBadge, StatBar, RadarChart, PokemonCard


class PokemonDetail(QWidget):
    """Detailed Pokemon view with sprite, stats radar, types, locations."""

    back_clicked = pyqtSignal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Back button
        back_btn = QLabel("< Back to Pokedex")
        back_btn.setFont(QFont("Segoe UI", 10))
        back_btn.setStyleSheet(f"color: {COLORS['accent_blue']}; padding: 4px;")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.mousePressEvent = lambda e: self.back_clicked.emit()
        layout.addWidget(back_btn)

        # Top: sprite + basic info + radar chart
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # Sprite + name column
        info_col = QVBoxLayout()
        info_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.sprite_label = QLabel()
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setFixedSize(128, 128)
        info_col.addWidget(self.sprite_label)

        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_col.addWidget(self.name_label)

        self.types_layout = QHBoxLayout()
        self.types_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.types_layout.setSpacing(6)
        info_col.addLayout(self.types_layout)

        self.abilities_label = QLabel("")
        self.abilities_label.setFont(QFont("Segoe UI", 9))
        self.abilities_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.abilities_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_col.addWidget(self.abilities_label)

        top_row.addLayout(info_col)

        # Radar chart
        self.radar = RadarChart()
        top_row.addWidget(self.radar)

        # Stat bars column
        stats_col = QVBoxLayout()
        stats_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        stats_title = QLabel("Base Stats")
        stats_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        stats_title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        stats_col.addWidget(stats_title)

        self.stat_bars = {}
        for stat_key, label in [("hp", "HP"), ("attack", "Atk"), ("defense", "Def"),
                                 ("sp_attack", "SpA"), ("sp_defense", "SpD"), ("speed", "Spe")]:
            bar = StatBar(label, 0)
            self.stat_bars[stat_key] = bar
            stats_col.addWidget(bar)

        self.bst_label = QLabel("BST: 0")
        self.bst_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.bst_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        stats_col.addWidget(self.bst_label)

        top_row.addLayout(stats_col)
        layout.addLayout(top_row)

        # Locations
        loc_frame = QFrame()
        loc_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        loc_layout = QVBoxLayout(loc_frame)
        loc_layout.setContentsMargins(12, 8, 12, 8)

        loc_title = QLabel("Locations in PokeMMO")
        loc_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        loc_title.setStyleSheet(f"color: {COLORS['accent_green']};")
        loc_layout.addWidget(loc_title)

        self.locations_label = QLabel("")
        self.locations_label.setFont(QFont("Consolas", 9))
        self.locations_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.locations_label.setWordWrap(True)
        loc_layout.addWidget(self.locations_label)

        layout.addWidget(loc_frame)

        # Nature advisor
        nature_frame = QFrame()
        nature_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        nature_layout = QVBoxLayout(nature_frame)
        nature_layout.setContentsMargins(12, 8, 12, 8)

        nature_title = QLabel("Recommended Natures")
        nature_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        nature_title.setStyleSheet(f"color: {COLORS['accent_purple']};")
        nature_layout.addWidget(nature_title)

        self.nature_label = QLabel("")
        self.nature_label.setFont(QFont("Consolas", 9))
        self.nature_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.nature_label.setWordWrap(True)
        nature_layout.addWidget(self.nature_label)

        layout.addWidget(nature_frame)

        # Move Recommender
        moves_frame = QFrame()
        moves_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        moves_layout = QVBoxLayout(moves_frame)
        moves_layout.setContentsMargins(12, 8, 12, 8)

        moves_title = QLabel("Recommended Moveset (PvE)")
        moves_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        moves_title.setStyleSheet(f"color: {COLORS['accent_orange']};")
        moves_layout.addWidget(moves_title)

        self.moves_label = QLabel("")
        self.moves_label.setFont(QFont("Consolas", 9))
        self.moves_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.moves_label.setWordWrap(True)
        moves_layout.addWidget(self.moves_label)

        layout.addWidget(moves_frame)
        layout.addStretch()

    def show_pokemon(self, pokemon: dict) -> None:
        """Display detailed info for a Pokemon."""
        pid = pokemon["id"]

        # Sprite
        pixmap = get_sprite(pid, 128)
        if pixmap:
            self.sprite_label.setPixmap(pixmap)
        else:
            self.sprite_label.setText(f"#{pid}")

        # Name
        self.name_label.setText(f"#{pid:03d} {pokemon['name']}")

        # Types
        while self.types_layout.count():
            item = self.types_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.types_layout.addWidget(TypeBadge(pokemon["type1"]))
        if pokemon.get("type2"):
            self.types_layout.addWidget(TypeBadge(pokemon["type2"]))

        # Abilities
        abilities = []
        if pokemon.get("ability1"):
            abilities.append(pokemon["ability1"])
        if pokemon.get("ability2"):
            abilities.append(pokemon["ability2"])
        if pokemon.get("hidden_ability"):
            abilities.append(f"{pokemon['hidden_ability']} (HA)")
        self.abilities_label.setText(f"Abilities: {' / '.join(abilities)}")

        # Stats
        stats = [pokemon["hp"], pokemon["attack"], pokemon["defense"],
                 pokemon["sp_attack"], pokemon["sp_defense"], pokemon["speed"]]
        self.radar.set_stats(stats)

        stat_keys = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
        bst = 0
        for key, val in zip(stat_keys, stats):
            self.stat_bars[key].value = val
            self.stat_bars[key].update()
            bst += val
        self.bst_label.setText(f"BST: {bst}")

        # Locations
        if self.db:
            locs = self.db.get_pokemon_locations(pokemon["name"])
            if locs:
                seen = set()
                lines = []
                for loc in locs[:10]:
                    key = f"{loc['route_name']}_{loc['region']}"
                    if key not in seen:
                        seen.add(key)
                        lines.append(
                            f"{loc['route_name']:20} ({loc['region']:6}) "
                            f"Lv.{loc['level_min']}-{loc['level_max']}  "
                            f"{loc['rate']:.0f}%  [{loc['method']}]"
                        )
                self.locations_label.setText("\n".join(lines))
            else:
                self.locations_label.setText("Not found in wild — may be starter/evolution only")

        # Nature advisor
        atk = pokemon.get("attack", 0)
        spa = pokemon.get("sp_attack", 0)
        spe = pokemon.get("speed", 0)
        defn = pokemon.get("defense", 0)
        spd = pokemon.get("sp_defense", 0)

        natures = []
        if atk > spa:
            # Physical attacker
            natures.append(f"Physical Attacker: Adamant (+Atk, -SpA) or Jolly (+Spe, -SpA)")
        if spa > atk:
            # Special attacker
            natures.append(f"Special Attacker: Modest (+SpA, -Atk) or Timid (+Spe, -Atk)")
        if atk == spa and atk > 80:
            natures.append(f"Mixed Attacker: Naive (+Spe, -SpD) or Hasty (+Spe, -Def)")
        if defn > 90 or spd > 90:
            natures.append(f"Tank: Bold (+Def, -Atk) or Calm (+SpD, -Atk)")
        if spe > 100:
            natures.append(f"Speed: Jolly (+Spe, -SpA) or Timid (+Spe, -Atk)")
        if not natures:
            natures.append("Flexible — choose based on your team's needs")

        self.nature_label.setText("\n".join(natures))

        # Move recommender
        from ...tools.move_recommender import recommend_moves, format_recommendations
        types = [pokemon["type1"]]
        if pokemon.get("type2"):
            types.append(pokemon["type2"])
        recs = recommend_moves(types, pokemon.get("attack", 0),
                               pokemon.get("sp_attack", 0), pokemon.get("speed", 0))
        self.moves_label.setText(format_recommendations(recs))


class PokedexPage(QWidget):
    """Pokedex page with grid of sprites and detail view."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._all_pokemon: list[dict] = []
        self._setup_ui()
        self._load_pokemon()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel("Pokedex")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # Stacked widget: grid view / detail view
        self.stack = QStackedWidget()

        # Grid view
        grid_container = QWidget()
        grid_layout = QVBoxLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search Pokemon by name, number, or type...")
        self.search.setFont(QFont("Segoe UI", 12))
        self.search.textChanged.connect(self._filter_grid)
        grid_layout.addWidget(self.search)

        # Type filter buttons
        from ...utils.constants import TYPES
        from ..theme import TYPE_COLORS
        type_row = QHBoxLayout()
        type_row.setSpacing(3)
        self._active_type_filter: str | None = None

        all_btn = QPushButton("All")
        all_btn.setFixedHeight(24)
        all_btn.setStyleSheet(f"""
            QPushButton {{
                color: white; background: {COLORS['accent_blue']};
                border-radius: 3px; padding: 2px 8px; font-size: 10px; font-weight: bold;
            }}
        """)
        all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        all_btn.clicked.connect(lambda: self._filter_by_type(None))
        type_row.addWidget(all_btn)

        for t in TYPES:
            btn = QPushButton(t[:3])
            btn.setFixedHeight(24)
            btn.setFixedWidth(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(t)
            color = TYPE_COLORS.get(t, "#888")
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: white; background: {color};
                    border-radius: 3px; font-size: 9px; font-weight: bold;
                }}
                QPushButton:hover {{ border: 2px solid white; }}
            """)
            btn.clicked.connect(lambda checked, type_name=t: self._filter_by_type(type_name))
            type_row.addWidget(btn)
        type_row.addStretch()
        grid_layout.addLayout(type_row)

        # Scroll area with grid of cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(8)
        scroll.setWidget(self.grid_widget)
        grid_layout.addWidget(scroll)

        self.stack.addWidget(grid_container)

        # Detail view
        self.detail = PokemonDetail(self.db)
        self.detail.back_clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.detail)

        layout.addWidget(self.stack)

    def _load_pokemon(self):
        """Load all Pokemon from database and create cards."""
        if not self.db:
            return

        # Load all Pokemon
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, name, type1, type2 FROM pokemon ORDER BY id"
            ).fetchall()
            self._all_pokemon = [dict(r) for r in rows]

        self._populate_grid(self._all_pokemon)

    def _populate_grid(self, pokemon_list: list[dict]) -> None:
        """Fill the grid with Pokemon cards."""
        # Clear existing
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 6  # Cards per row
        for i, p in enumerate(pokemon_list[:150]):  # Limit to 150 for performance
            card = PokemonCard(p["id"], p["name"], p["type1"], p.get("type2"))
            card.mousePressEvent = lambda e, pid=p["id"]: self._show_detail(pid)
            self.grid.addWidget(card, i // cols, i % cols)

    def _filter_by_type(self, type_name: str | None) -> None:
        """Filter grid by type."""
        self._active_type_filter = type_name
        self.search.clear()
        if type_name is None:
            self._populate_grid(self._all_pokemon)
        else:
            filtered = [p for p in self._all_pokemon
                        if p["type1"] == type_name or p.get("type2") == type_name]
            self._populate_grid(filtered)

    def _filter_grid(self, text: str) -> None:
        """Filter Pokemon grid by search text."""
        self._active_type_filter = None
        if not text or len(text) < 2:
            self._populate_grid(self._all_pokemon)
            return

        text_lower = text.lower()
        filtered = [p for p in self._all_pokemon
                    if text_lower in p["name"].lower()
                    or text_lower in str(p["id"])
                    or text_lower in p["type1"].lower()
                    or text_lower in (p.get("type2", "") or "").lower()]
        self._populate_grid(filtered)

    def _show_detail(self, pokemon_id: int) -> None:
        """Show detailed view for a Pokemon."""
        if not self.db:
            return
        pokemon = self.db.get_pokemon_by_id(pokemon_id)
        if pokemon:
            self.detail.show_pokemon(pokemon)
            self.stack.setCurrentIndex(1)
