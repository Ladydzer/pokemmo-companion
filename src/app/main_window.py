"""Main window for PokeMMO Companion desktop app."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from .theme import COLORS, APP_STYLESHEET
from .pages.dashboard import DashboardPage
from .pages.pokedex import PokedexPage
from .pages.battle import BattlePage
from .pages.team_builder import TeamBuilderPage
from .pages.shiny_lab import ShinyLabPage
from .pages.settings import SettingsPage


class SidebarButton(QPushButton):
    """Styled sidebar navigation button."""

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(f"  {icon_text}  {label}", parent)
        self.setCheckable(True)
        self.setFont(QFont("Segoe UI", 12))
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MainWindow(QMainWindow):
    """Main companion app window with sidebar navigation."""

    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.setWindowTitle("PokeMMO Companion")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Apply theme
        self.setStyleSheet(APP_STYLESHEET)

        self._setup_ui()

    def _setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App title in sidebar
        title_container = QWidget()
        title_container.setStyleSheet(f"background-color: {COLORS['bg_primary']}; padding: 16px;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(12, 16, 12, 16)

        app_title = QLabel("PokeMMO")
        app_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        app_title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        title_layout.addWidget(app_title)

        app_subtitle = QLabel("Companion")
        app_subtitle.setFont(QFont("Segoe UI", 10))
        app_subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        title_layout.addWidget(app_subtitle)

        sidebar_layout.addWidget(title_container)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        sidebar_layout.addWidget(sep)

        # Navigation buttons
        self._nav_buttons: list[SidebarButton] = []
        nav_items = [
            ("🏠", "Dashboard"),
            ("📖", "Pokedex"),
            ("⚔", "Battle"),
            ("👥", "Team"),
            ("✨", "Shiny Lab"),
            ("⚙", "Settings"),
        ]

        for icon, label in nav_items:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, l=label: self._navigate(l))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Version info
        version = QLabel("v0.2.0")
        version.setFont(QFont("Segoe UI", 8))
        version.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 12px;")
        sidebar_layout.addWidget(version)

        main_layout.addWidget(sidebar)

        # Content area (stacked pages)
        self.pages = QStackedWidget()
        self.pages.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        # Create pages
        self.dashboard = DashboardPage(self.db)
        self.pages.addWidget(self.dashboard)

        self.pokedex = PokedexPage(self.db)
        self.pages.addWidget(self.pokedex)

        self.battle = BattlePage(self.db)
        self.pages.addWidget(self.battle)

        self.team_builder = TeamBuilderPage(self.db)
        self.pages.addWidget(self.team_builder)

        self.shiny_lab = ShinyLabPage()
        self.pages.addWidget(self.shiny_lab)

        self.settings = SettingsPage()
        self.pages.addWidget(self.settings)

        # Right side: pages + status bar
        right_side = QVBoxLayout()
        right_side.setContentsMargins(0, 0, 0, 0)
        right_side.setSpacing(0)
        right_side.addWidget(self.pages, 1)

        # Status bar
        self.status_bar = QLabel(
            f"  DB: {self.db.get_pokemon_count() if self.db else 0} Pokemon  |  "
            f"Route: ---  |  Overlay: Disconnected"
        )
        self.status_bar.setFont(QFont("Segoe UI", 9))
        self.status_bar.setFixedHeight(28)
        self.status_bar.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            background-color: {COLORS['bg_secondary']};
            border-top: 1px solid {COLORS['border']};
            padding: 0 8px;
        """)
        right_side.addWidget(self.status_bar)

        main_layout.addLayout(right_side, 1)

        # Default to dashboard
        self._navigate("Dashboard")

    def _navigate(self, page_name: str) -> None:
        """Navigate to a page."""
        page_map = {
            "Dashboard": 0,
            "Pokedex": 1,
            "Battle": 2,
            "Team": 3,
            "Shiny Lab": 4,
            "Settings": 5,
        }
        idx = page_map.get(page_name, 0)
        self.pages.setCurrentIndex(idx)

        # Update button states
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)

    # === Public API for overlay sync ===

    def on_route_changed(self, route_name: str, region: str, spawns: list) -> None:
        """Called when overlay detects a route change."""
        self.dashboard.update_route(route_name, region)
        self.dashboard.update_spawns(spawns)

    def on_battle_started(self, battle_info: dict) -> None:
        """Called when overlay detects a battle — auto-navigate to Battle page."""
        self._navigate("Battle")
        self.battle.show_opponent(battle_info)

    def on_battle_ended(self) -> None:
        """Called when battle ends — go back to dashboard."""
        self._navigate("Dashboard")

    def on_encounters_updated(self, count: int, shiny_prob: float) -> None:
        """Update encounter stats on dashboard."""
        self.dashboard.update_encounters(count, shiny_prob)
