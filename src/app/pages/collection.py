"""Collection Tracker — track which Pokemon you've caught out of 649."""
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QFrame, QGridLayout, QScrollArea, QPushButton, QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..theme import COLORS
from ..sprite_cache import get_sprite
from ...utils.config import CONFIG_DIR

COLLECTION_FILE = CONFIG_DIR / "collection.json"


class CollectionData:
    """Persistent collection tracking data."""

    def __init__(self):
        self.caught: set[int] = set()
        self._load()

    def _load(self) -> None:
        if COLLECTION_FILE.exists():
            try:
                with open(COLLECTION_FILE) as f:
                    data = json.load(f)
                self.caught = set(data.get("caught", []))
            except (json.JSONDecodeError, TypeError):
                pass

    def save(self) -> None:
        COLLECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COLLECTION_FILE, "w") as f:
            json.dump({"caught": sorted(self.caught)}, f)

    def toggle(self, pokemon_id: int) -> bool:
        """Toggle caught status. Returns new status."""
        if pokemon_id in self.caught:
            self.caught.discard(pokemon_id)
            return False
        else:
            self.caught.add(pokemon_id)
            return True

    def is_caught(self, pokemon_id: int) -> bool:
        return pokemon_id in self.caught

    @property
    def count(self) -> int:
        return len(self.caught)


class MiniSpriteCard(QWidget):
    """Small sprite card for collection grid — colored if caught, grey if not."""

    def __init__(self, pokemon_id: int, name: str, is_caught: bool, parent=None):
        super().__init__(parent)
        self.pokemon_id = pokemon_id
        self._caught = is_caught
        self.setFixedSize(56, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sprite
        self.sprite_label = QLabel()
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = get_sprite(pokemon_id, 40)
        if pixmap:
            self.sprite_label.setPixmap(pixmap)
            if not is_caught:
                # Make grayscale effect via stylesheet
                self.sprite_label.setStyleSheet("opacity: 0.3;")
        else:
            self.sprite_label.setText(f"{pokemon_id}")
            self.sprite_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px;")
        layout.addWidget(self.sprite_label)

        # Number
        num = QLabel(f"#{pokemon_id}")
        num.setFont(QFont("Consolas", 7))
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
        layout.addWidget(num)

    def _update_style(self):
        if self._caught:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_card']};
                    border: 2px solid {COLORS['accent_green']};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                }}
                QWidget:hover {{
                    border-color: {COLORS['accent_blue']};
                }}
            """)

    def set_caught(self, caught: bool):
        self._caught = caught
        self._update_style()


class CollectionPage(QWidget):
    """Collection tracker page — progress bars and sprite grid."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.collection = CollectionData()
        self._all_pokemon: list[dict] = []
        self._cards: dict[int, MiniSpriteCard] = {}
        self._setup_ui()
        self._load_pokemon()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title_row = QHBoxLayout()
        title = QLabel("Suivi de Collection")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_row.addWidget(title)

        self.count_label = QLabel("0 / 649")
        self.count_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.count_label.setStyleSheet(f"color: {COLORS['accent_green']};")
        title_row.addStretch()
        title_row.addWidget(self.count_label)
        layout.addLayout(title_row)

        # Overall progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 649)
        self.progress.setValue(0)
        self.progress.setFixedHeight(24)
        self.progress.setFormat("%v / 649 (%p%)")
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                text-align: center;
                color: {COLORS['text_primary']};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_green']};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.progress)

        # Region progress
        region_row = QHBoxLayout()
        region_row.setSpacing(8)
        self.region_bars: dict[str, tuple[QProgressBar, QLabel]] = {}

        gen_ranges = [
            ("Kanto", 1, 151), ("Johto", 152, 251),
            ("Hoenn", 252, 386), ("Sinnoh", 387, 493), ("Unova", 494, 649),
        ]
        for region, start, end in gen_ranges:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(10, 8, 10, 8)

            rl = QLabel(region)
            rl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            rl.setStyleSheet(f"color: {COLORS['accent_blue']};")
            rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fl.addWidget(rl)

            count = end - start + 1
            bar = QProgressBar()
            bar.setRange(0, count)
            bar.setValue(0)
            bar.setFixedHeight(16)
            bar.setFormat(f"0/{count}")
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {COLORS['bg_secondary']};
                    border-radius: 4px;
                    font-size: 9px;
                    color: {COLORS['text_secondary']};
                }}
                QProgressBar::chunk {{
                    background-color: {COLORS['accent_green']};
                    border-radius: 3px;
                }}
            """)
            fl.addWidget(bar)

            count_lbl = QLabel(f"0/{count}")
            count_lbl.setFont(QFont("Segoe UI", 8))
            count_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fl.addWidget(count_lbl)

            self.region_bars[region] = (bar, count_lbl)
            region_row.addWidget(frame)

        layout.addLayout(region_row)

        # Hint
        hint = QLabel("Clique sur un Pokemon pour le marquer capture/non capture")
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(hint)

        # Grid scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(4)
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

    def _load_pokemon(self):
        if not self.db:
            return

        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, name, type1, type2 FROM pokemon ORDER BY id"
            ).fetchall()
            self._all_pokemon = [dict(r) for r in rows]

        cols = 12
        for i, p in enumerate(self._all_pokemon):
            caught = self.collection.is_caught(p["id"])
            card = MiniSpriteCard(p["id"], p["name"], caught)
            card.mousePressEvent = lambda e, pid=p["id"]: self._toggle_pokemon(pid)
            self._cards[p["id"]] = card
            self.grid.addWidget(card, i // cols, i % cols)

        self._update_counts()

    def _toggle_pokemon(self, pokemon_id: int) -> None:
        caught = self.collection.toggle(pokemon_id)
        if pokemon_id in self._cards:
            self._cards[pokemon_id].set_caught(caught)
        self.collection.save()
        self._update_counts()

    def _update_counts(self) -> None:
        total = self.collection.count
        self.count_label.setText(f"{total} / 649")
        self.progress.setValue(total)

        gen_ranges = [
            ("Kanto", 1, 151), ("Johto", 152, 251),
            ("Hoenn", 252, 386), ("Sinnoh", 387, 493), ("Unova", 494, 649),
        ]
        for region, start, end in gen_ranges:
            if region in self.region_bars:
                count = sum(1 for i in range(start, end + 1) if self.collection.is_caught(i))
                total_region = end - start + 1
                bar, lbl = self.region_bars[region]
                bar.setValue(count)
                bar.setFormat(f"{count}/{total_region}")
                lbl.setText(f"{count}/{total_region}")
