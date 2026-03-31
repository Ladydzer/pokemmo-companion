"""Dashboard page — hub central with overview of current game state."""
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame,
    QProgressBar, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient

from ..theme import COLORS, TYPE_COLORS
from ..sprite_cache import get_sprite, sprite_count
from ..widgets import TypeBadge


class AccentCard(QFrame):
    """Card with colored left border accent — the key visual element."""

    def __init__(self, title: str, accent: str, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.setStyleSheet(f"""
            AccentCard {{
                background-color: {COLORS['bg_card']};
                border-left: 4px solid {accent};
                border-top: 1px solid {COLORS['border']};
                border-right: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(6)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {accent};")
        self._layout.addWidget(header)

    def add_widget(self, widget):
        self._layout.addWidget(widget)

    def add_layout(self, layout):
        self._layout.addLayout(layout)


class SpawnRow(QWidget):
    """A single spawn entry with sprite + name + type badge + rate bar."""

    def __init__(self, pokemon_name: str, pokemon_id: int, type1: str,
                 type2: str | None, rate: float, level_min: int, level_max: int,
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        # Sprite
        sprite_label = QLabel()
        sprite_label.setFixedSize(32, 32)
        sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = get_sprite(pokemon_id, 32)
        if pixmap:
            sprite_label.setPixmap(pixmap)
        layout.addWidget(sprite_label)

        # Name
        name_label = QLabel(pokemon_name)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white;")
        name_label.setFixedWidth(110)
        layout.addWidget(name_label)

        # Type badge
        t1 = QLabel(type1[:3])
        t1.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setFixedSize(36, 18)
        t1.setStyleSheet(f"color: white; background: {TYPE_COLORS.get(type1, '#888')}; border-radius: 3px;")
        layout.addWidget(t1)

        if type2:
            t2 = QLabel(type2[:3])
            t2.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t2.setFixedSize(36, 18)
            t2.setStyleSheet(f"color: white; background: {TYPE_COLORS.get(type2, '#888')}; border-radius: 3px;")
            layout.addWidget(t2)

        # Rate bar
        rate_bar = QProgressBar()
        rate_bar.setRange(0, 100)
        rate_bar.setValue(int(min(rate, 100)))
        rate_bar.setFixedHeight(14)
        rate_bar.setFixedWidth(80)
        rate_bar.setFormat(f"{rate:.0f}%")
        rate_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_secondary']};
                border-radius: 4px;
                font-size: 9px;
                color: white;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_green']};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(rate_bar)

        # Level
        lvl = QLabel(f"Lv.{level_min}-{level_max}")
        lvl.setFont(QFont("Segoe UI", 9))
        lvl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(lvl)

        layout.addStretch()


class DashboardPage(QWidget):
    """Main dashboard page — redesigned with visual hierarchy."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Tableau de Bord")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        # === Hero row: Pokemon du Jour (big) + Stats ===
        hero_row = QHBoxLayout()
        hero_row.setSpacing(16)

        # Pokemon du Jour — Hero card
        self.hero_card = self._build_hero_card()
        hero_row.addWidget(self.hero_card, 2)

        # Stats column
        stats_col = QVBoxLayout()
        stats_col.setSpacing(12)

        # Position card
        pos_card = AccentCard("Position Actuelle", COLORS['accent_blue'])
        self.route_label = QLabel("Non connecte au jeu")
        self.route_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.route_label.setStyleSheet("color: white;")
        pos_card.add_widget(self.route_label)
        self.region_label = QLabel("")
        self.region_label.setFont(QFont("Segoe UI", 10))
        self.region_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        pos_card.add_widget(self.region_label)
        stats_col.addWidget(pos_card)

        # Encounters card
        enc_card = AccentCard("Rencontres", COLORS['accent_orange'])
        self.encounter_label = QLabel("0")
        self.encounter_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.encounter_label.setStyleSheet(f"color: {COLORS['accent_orange']};")
        enc_card.add_widget(self.encounter_label)
        self.shiny_prob_label = QLabel("Shiny: 0.00%")
        self.shiny_prob_label.setFont(QFont("Segoe UI", 10))
        self.shiny_prob_label.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        enc_card.add_widget(self.shiny_prob_label)
        stats_col.addWidget(enc_card)

        # Collection progress card
        col_card = AccentCard("Collection", COLORS['accent_green'])
        self.collection_bar = QProgressBar()
        self.collection_bar.setRange(0, 649)
        self.collection_bar.setValue(0)
        self.collection_bar.setFixedHeight(20)
        self.collection_bar.setFormat("0 / 649 (0%)")
        self.collection_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_secondary']};
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_green']};
                border-radius: 5px;
            }}
        """)
        col_card.add_widget(self.collection_bar)
        stats_col.addWidget(col_card)

        # Update collection count
        try:
            from .collection import CollectionData
            coll = CollectionData()
            self.collection_bar.setValue(coll.count)
            self.collection_bar.setFormat(f"{coll.count} / 649 ({coll.count*100//649}%)")
        except Exception:
            pass

        hero_row.addLayout(stats_col, 1)
        layout.addLayout(hero_row)

        # === Spawns section ===
        spawns_card = AccentCard("Pokemon de la Zone", COLORS['accent_green'])
        self.spawns_container = QVBoxLayout()
        self.spawns_placeholder = QLabel("En attente de detection de route...")
        self.spawns_placeholder.setFont(QFont("Segoe UI", 11))
        self.spawns_placeholder.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.spawns_container.addWidget(self.spawns_placeholder)
        spawns_card.add_layout(self.spawns_container)
        layout.addWidget(spawns_card)

        # === Objective ===
        obj_card = AccentCard("Objectif du Jour", COLORS['accent_purple'])
        self.objective_label = QLabel(self._generate_objective())
        self.objective_label.setFont(QFont("Segoe UI", 12))
        self.objective_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        self.objective_label.setWordWrap(True)
        obj_card.add_widget(self.objective_label)
        layout.addWidget(obj_card)

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_hero_card(self) -> QFrame:
        """Build the Pokemon du Jour hero card with big sprite."""
        card = QFrame()

        if not self.db:
            card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border-radius: 12px;")
            layout = QVBoxLayout(card)
            layout.addWidget(QLabel("Base de donnees non chargee"))
            return card

        pid = random.randint(1, 649)
        pokemon = self.db.get_pokemon_by_id(pid)
        if not pokemon:
            pid, pokemon = 25, self.db.get_pokemon_by_id(25)

        # Card with type-colored gradient border
        type_color = TYPE_COLORS.get(pokemon["type1"], "#4FC3F7")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {type_color};
                border-radius: 12px;
            }}
        """)
        card.setMinimumHeight(220)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Title
        title = QLabel("Pokemon du Jour")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        layout.addWidget(title)

        # Content row: sprite + info
        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        # Big sprite
        sprite_label = QLabel()
        sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sprite_label.setFixedSize(128, 128)
        pixmap = get_sprite(pid, 128)
        if pixmap:
            sprite_label.setPixmap(pixmap)
        content_row.addWidget(sprite_label)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(4)

        name_lbl = QLabel(f"#{pid:03d} {pokemon['name']}")
        name_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: white;")
        info.addWidget(name_lbl)

        types_row = QHBoxLayout()
        types_row.setSpacing(6)
        types_row.addWidget(TypeBadge(pokemon["type1"]))
        if pokemon.get("type2"):
            types_row.addWidget(TypeBadge(pokemon["type2"]))
        types_row.addStretch()
        info.addLayout(types_row)

        # BST
        bst = sum([pokemon["hp"], pokemon["attack"], pokemon["defense"],
                   pokemon["sp_attack"], pokemon["sp_defense"], pokemon["speed"]])
        bst_lbl = QLabel(f"BST: {bst}")
        bst_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        bst_lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.addWidget(bst_lbl)

        # Location hint
        locs = self.db.get_pokemon_locations(pokemon["name"])
        if locs:
            loc = locs[0]
            loc_lbl = QLabel(f"Trouve: {loc['route_name']} ({loc['region']})")
            loc_lbl.setFont(QFont("Segoe UI", 10))
            loc_lbl.setStyleSheet(f"color: {COLORS['accent_green']};")
            info.addWidget(loc_lbl)

        info.addStretch()
        content_row.addLayout(info, 1)
        layout.addLayout(content_row)

        return card

    def _generate_objective(self) -> str:
        import random
        objectives = [
            "Explore une nouvelle route que tu n'as pas encore visitee !",
            "Essaie d'attraper 10 Pokemon qui manquent a ta collection",
            "Defie un champion d'arene dans ta region en cours",
            "Fais 100 rencontres pour ton shiny hunt",
            "Construis une equipe equilibree avec une bonne couverture de types",
            "Entraine les EVs de ton Pokemon competitif",
            "Essaie les hordes avec Sweet Scent pour chasser les shinies",
            "Verifie le Pokedex pour les Pokemon qui te manquent a Kanto",
            "Planifie ton prochain breed 5IV au Centre d'Elevage",
            "Explore Johto si tu n'as pas encore commence cette region",
            "Complete ta collection sur une route — attrape tout !",
            "Entraine ton equipe au niveau 50+ pour le Conseil des 4",
        ]
        if self.db:
            try:
                from .collection import CollectionData
                collection = CollectionData()
                caught = collection.count
                if caught < 50:
                    return f"Tu as attrape {caught}/649 Pokemon. Essaie d'atteindre 50 aujourd'hui !"
                elif caught < 150:
                    return f"Collection : {caught}/649. Complete le Pokedex Kanto (151) !"
                elif caught < 300:
                    return f"Collection : {caught}/649. Explore Hoenn pour de nouvelles captures !"
            except Exception:
                pass
        return random.choice(objectives)

    def update_route(self, route_name: str, region: str) -> None:
        self.route_label.setText(route_name)
        self.region_label.setText(region)

    def update_spawns(self, spawns: list[dict]) -> None:
        # Clear existing
        while self.spawns_container.count():
            item = self.spawns_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not spawns:
            placeholder = QLabel("Aucune donnee de spawn pour cette zone")
            placeholder.setFont(QFont("Segoe UI", 10))
            placeholder.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.spawns_container.addWidget(placeholder)
            return

        for s in spawns[:8]:
            row = SpawnRow(
                s.get("pokemon_name", "???"),
                s.get("pokemon_id", 0),
                s.get("type1", "Normal"),
                s.get("type2"),
                s.get("rate", 0),
                s.get("level_min", 0),
                s.get("level_max", 0),
            )
            self.spawns_container.addWidget(row)

    def update_encounters(self, count: int, shiny_prob: float) -> None:
        self.encounter_label.setText(f"{count:,}")
        self.shiny_prob_label.setText(f"Shiny: {shiny_prob * 100:.2f}%")
