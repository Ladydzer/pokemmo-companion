"""Dashboard page — hub central with overview of current game state."""
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from ..theme import COLORS
from ..sprite_cache import get_sprite, sprite_count
from ..widgets import TypeBadge, StatBar
from ...utils.constants import SHINY_RATE_BASE


class DashboardCard(QFrame):
    """A styled card container."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            DashboardCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(8)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['accent_blue']};")
        self._layout.addWidget(header)

    def add_widget(self, widget):
        self._layout.addWidget(widget)

    def add_layout(self, layout):
        self._layout.addLayout(layout)


class DashboardPage(QWidget):
    """Main dashboard page."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # Top row: Route + Status + Encounters
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Current location card
        self.location_card = DashboardCard("Current Location")
        self.route_label = QLabel("Not connected to game")
        self.route_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.route_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.location_card.add_widget(self.route_label)
        self.region_label = QLabel("")
        self.region_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.location_card.add_widget(self.region_label)
        top_row.addWidget(self.location_card)

        # Encounter stats card
        self.encounter_card = DashboardCard("Encounters")
        self.encounter_label = QLabel("0 encounters")
        self.encounter_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.encounter_label.setStyleSheet(f"color: {COLORS['accent_orange']};")
        self.encounter_card.add_widget(self.encounter_label)
        self.shiny_prob_label = QLabel("Shiny: 0.00%")
        self.shiny_prob_label.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        self.encounter_card.add_widget(self.shiny_prob_label)
        top_row.addWidget(self.encounter_card)

        # DB stats card
        self.db_card = DashboardCard("Database")
        if self.db:
            db_text = (f"Pokemon: {self.db.get_pokemon_count()}\n"
                       f"Routes: {self.db.get_route_count()}\n"
                       f"Spawns: {self.db.get_spawn_count()}\n"
                       f"Sprites: {sprite_count()}")
        else:
            db_text = "Database not loaded"
        db_label = QLabel(db_text)
        db_label.setFont(QFont("Consolas", 10))
        db_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.db_card.add_widget(db_label)
        top_row.addWidget(self.db_card)

        layout.addLayout(top_row)

        # Middle row: Spawns + Pokemon spotlight
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Spawns card
        self.spawns_card = DashboardCard("Route Spawns")
        self.spawns_label = QLabel("Waiting for route detection...")
        self.spawns_label.setFont(QFont("Consolas", 10))
        self.spawns_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.spawns_label.setWordWrap(True)
        self.spawns_card.add_widget(self.spawns_label)
        mid_row.addWidget(self.spawns_card, 2)

        # Pokemon spotlight card
        self.spotlight_card = DashboardCard("Pokemon Spotlight")
        self._setup_spotlight()
        mid_row.addWidget(self.spotlight_card, 1)

        layout.addLayout(mid_row)

        # Objective of the Day
        objective_card = DashboardCard("Objective of the Day")
        self.objective_label = QLabel(self._generate_objective())
        self.objective_label.setFont(QFont("Segoe UI", 11))
        self.objective_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        self.objective_label.setWordWrap(True)
        objective_card.add_widget(self.objective_label)
        layout.addWidget(objective_card)

        layout.addStretch()

    def _setup_spotlight(self):
        """Show a random Pokemon spotlight."""
        if not self.db:
            return

        # Pick a random Pokemon
        pid = random.randint(1, 649)
        pokemon = self.db.get_pokemon_by_id(pid)
        if not pokemon:
            return

        # Sprite
        sprite_label = QLabel()
        sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = get_sprite(pid, 96)
        if pixmap:
            sprite_label.setPixmap(pixmap)
        self.spotlight_card.add_widget(sprite_label)

        # Name + types
        name_label = QLabel(f"#{pid} {pokemon['name']}")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.spotlight_card.add_widget(name_label)

        types_row = QHBoxLayout()
        types_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        types_row.addWidget(TypeBadge(pokemon["type1"]))
        if pokemon.get("type2"):
            types_row.addWidget(TypeBadge(pokemon["type2"]))
        self.spotlight_card.add_layout(types_row)

        # BST
        bst = sum([pokemon["hp"], pokemon["attack"], pokemon["defense"],
                   pokemon["sp_attack"], pokemon["sp_defense"], pokemon["speed"]])
        bst_label = QLabel(f"BST: {bst}")
        bst_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bst_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.spotlight_card.add_widget(bst_label)

        # Find location
        if self.db:
            locs = self.db.get_pokemon_locations(pokemon["name"])
            if locs:
                loc = locs[0]
                loc_label = QLabel(f"Find: {loc['route_name']} ({loc['region']})")
                loc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                loc_label.setStyleSheet(f"color: {COLORS['accent_green']};")
                loc_label.setFont(QFont("Segoe UI", 9))
                self.spotlight_card.add_widget(loc_label)

    def _generate_objective(self) -> str:
        """Generate a daily objective based on available data."""
        import random
        objectives = [
            "Explore a new route you haven't visited yet!",
            "Try catching 10 Pokemon you don't have in your collection",
            "Challenge a gym leader in a region you're progressing through",
            "Do 100 encounters toward your shiny hunt target",
            "Build a balanced team with good type coverage",
            "Farm some EVs for your competitive Pokemon",
            "Try Sweet Scent horde encounters for efficient shiny hunting",
            "Check the Pokedex for Pokemon you're missing in Kanto",
            "Visit the Breeding Center and plan your next 5IV breed",
            "Explore Johto if you haven't started that region yet",
            "Complete your collection for one route — catch everything!",
            "Train your team to level 50+ for the Elite Four challenge",
        ]

        if self.db:
            # Add context-aware objectives
            from ..pages.collection import CollectionData
            collection = CollectionData()
            caught = collection.count
            if caught < 50:
                return f"You've caught {caught}/649 Pokemon. Try to reach 50 today!"
            elif caught < 150:
                return f"Collection: {caught}/649. Complete the Kanto Pokedex (151)!"
            elif caught < 300:
                return f"Collection: {caught}/649. You're making great progress. Explore Hoenn for new catches!"

        return random.choice(objectives)

    def update_route(self, route_name: str, region: str) -> None:
        self.route_label.setText(route_name)
        self.region_label.setText(region)

    def update_spawns(self, spawns: list[dict]) -> None:
        if not spawns:
            self.spawns_label.setText("No spawn data")
            return

        lines = []
        for s in spawns[:10]:
            name = s.get("pokemon_name", "???")
            rate = s.get("rate", 0)
            lmin = s.get("level_min", "?")
            lmax = s.get("level_max", "?")
            lines.append(f"{name:15} {rate:5.1f}%  Lv.{lmin}-{lmax}")
        self.spawns_label.setText("\n".join(lines))

    def update_encounters(self, count: int, shiny_prob: float) -> None:
        self.encounter_label.setText(f"{count:,} encounters")
        self.shiny_prob_label.setText(f"Shiny chance: {shiny_prob * 100:.2f}%")
