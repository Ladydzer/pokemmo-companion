"""Route Notes — personal notes per route, persisted in SQLite."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QFrame, QComboBox, QPushButton, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..theme import COLORS
from ...utils.constants import REGIONS


class NotesPage(QWidget):
    """Route notes page — add personal notes to any route."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_route_id: int | None = None
        self._setup_ui()
        self._ensure_notes_table()
        self._load_routes()

    def _ensure_notes_table(self):
        """Create notes table if it doesn't exist."""
        if not self.db:
            return
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS route_notes (
                    route_id INTEGER PRIMARY KEY,
                    note TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (route_id) REFERENCES routes(id)
                )
            """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Left side: route list
        left = QVBoxLayout()
        left.setSpacing(8)

        title = QLabel("Route Notes")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        left.addWidget(title)

        # Region filter
        self.region_combo = QComboBox()
        self.region_combo.addItems(["All Regions"] + REGIONS)
        self.region_combo.currentTextChanged.connect(self._filter_routes)
        left.addWidget(self.region_combo)

        # Route list
        self.route_list = QListWidget()
        self.route_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_primary']};
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['bg_active']};
                color: {COLORS['accent_blue']};
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        self.route_list.currentItemChanged.connect(self._on_route_selected)
        left.addWidget(self.route_list)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(280)
        layout.addWidget(left_widget)

        # Right side: note editor
        right = QVBoxLayout()
        right.setSpacing(8)

        self.route_title = QLabel("Select a route")
        self.route_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.route_title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        right.addWidget(self.route_title)

        self.route_info = QLabel("")
        self.route_info.setFont(QFont("Segoe UI", 10))
        self.route_info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        right.addWidget(self.route_info)

        # Note text editor
        note_frame = QFrame()
        note_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(12, 8, 12, 8)

        note_header = QLabel("Your Notes")
        note_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        note_header.setStyleSheet(f"color: {COLORS['accent_orange']};")
        note_layout.addWidget(note_header)

        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText(
            "Write your notes here...\n\n"
            "Examples:\n"
            "- Good spot for Audino farming\n"
            "- Saw a shiny Ponyta here at night\n"
            "- Need Surf to access the east side"
        )
        self.note_editor.setFont(QFont("Segoe UI", 10))
        self.note_editor.setStyleSheet(f"""
            QTextEdit {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        self.note_editor.setMinimumHeight(200)
        note_layout.addWidget(self.note_editor)

        # Save button
        save_btn = QPushButton("Save Note")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background: {COLORS['accent_blue']};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #2196F3; }}
        """)
        save_btn.clicked.connect(self._save_note)
        note_layout.addWidget(save_btn)

        right.addWidget(note_frame)

        # Spawns info for selected route
        self.spawns_label = QLabel("")
        self.spawns_label.setFont(QFont("Consolas", 9))
        self.spawns_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.spawns_label.setWordWrap(True)
        right.addWidget(self.spawns_label)

        right.addStretch()
        layout.addLayout(right, 1)

    def _load_routes(self):
        """Load all routes into the list."""
        if not self.db:
            return
        self._filter_routes(self.region_combo.currentText())

    def _filter_routes(self, region: str):
        """Filter route list by region."""
        self.route_list.clear()
        if not self.db:
            return

        with self.db.connect() as conn:
            if region == "All Regions":
                rows = conn.execute(
                    "SELECT id, name, region, area_type FROM routes ORDER BY region, name"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, name, region, area_type FROM routes WHERE region = ? ORDER BY name",
                    (region,)
                ).fetchall()

            # Check which routes have notes
            noted_ids = set()
            try:
                note_rows = conn.execute("SELECT route_id FROM route_notes WHERE note != ''").fetchall()
                noted_ids = {r[0] for r in note_rows}
            except Exception:
                pass

        for row in rows:
            route = dict(row)
            prefix = "* " if route["id"] in noted_ids else "  "
            text = f"{prefix}{route['name']} ({route['region']})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, route["id"])
            self.route_list.addItem(item)

    def _on_route_selected(self, current, previous):
        """Handle route selection."""
        if not current:
            return

        route_id = current.data(Qt.ItemDataRole.UserRole)
        self._current_route_id = route_id

        if not self.db:
            return

        # Load route info
        with self.db.connect() as conn:
            route = conn.execute(
                "SELECT name, region, area_type FROM routes WHERE id = ?", (route_id,)
            ).fetchone()

            if route:
                self.route_title.setText(dict(route)["name"])
                self.route_info.setText(f"{dict(route)['region']} — {dict(route).get('area_type', '')}")

            # Load note
            try:
                note_row = conn.execute(
                    "SELECT note FROM route_notes WHERE route_id = ?", (route_id,)
                ).fetchone()
                self.note_editor.setText(dict(note_row)["note"] if note_row else "")
            except Exception:
                self.note_editor.setText("")

        # Load spawns
        spawns = self.db.get_spawns_for_route(
            dict(route)["name"] if route else "", dict(route)["region"] if route else ""
        )
        if spawns:
            lines = ["Spawns:"]
            for s in spawns[:8]:
                t2 = f"/{s.get('type2', '')}" if s.get('type2') else ""
                lines.append(f"  {s['pokemon_name']} ({s['type1']}{t2}) {s['rate']:.0f}%")
            self.spawns_label.setText("\n".join(lines))
        else:
            self.spawns_label.setText("No spawn data")

    def _save_note(self):
        """Save the current note."""
        if not self.db or self._current_route_id is None:
            return

        note = self.note_editor.toPlainText()
        with self.db.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO route_notes (route_id, note, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (self._current_route_id, note)
            )

        # Refresh list to show asterisk for noted routes
        self._filter_routes(self.region_combo.currentText())
