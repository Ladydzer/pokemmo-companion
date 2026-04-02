"""Main overlay window — transparent, click-through, always-on-top."""
import sys
import time
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPalette, QMouseEvent

from ..utils.config import AppConfig
from ..utils.logger import log

# Win32 constants for click-through
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080

user32 = ctypes.windll.user32


class GripBar(QWidget):
    """Small drag handle at the top of the overlay — NOT click-through."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._drag_pos = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class OverlayWindow(QMainWindow):
    """Main overlay window that sits on top of PokeMMO."""

    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config = config or AppConfig.load()
        self._is_compact = True
        self._is_visible = True
        self._is_mini = True  # Mini mode: route + battle only
        self._last_battle_name = ""
        self._last_activity = 0.0  # timestamp of last route/battle change
        self._auto_hidden = False  # True when auto-hidden due to inactivity

        self._setup_window()
        self._setup_ui()
        self._setup_click_through()
        self._setup_auto_hide()

    def _setup_window(self):
        """Configure window flags for overlay behavior."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("PokeMMO Companion Overlay")

        # Position
        oc = self.config.overlay
        if oc.position_x >= 0 and oc.position_y >= 0:
            self.move(oc.position_x, oc.position_y)
        else:
            # Default: top-right area
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.geometry()
                self.move(geom.width() - oc.width - 20, 100)

        self.resize(self.config.overlay.width, 200)
        self.setWindowOpacity(self.config.overlay.opacity)

    def _setup_ui(self):
        """Build the overlay UI."""
        central = QWidget()
        central.setObjectName("overlay_central")
        central.setStyleSheet("""
            #overlay_central {
                background-color: rgba(20, 20, 30, 200);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 140, 100);
            }
        """)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)

        # Grip bar for dragging
        self.grip = GripBar()
        self.grip.setStyleSheet("background-color: rgba(60, 60, 80, 150); border-radius: 3px;")
        layout.addWidget(self.grip)

        # Route info section
        self.route_label = QLabel("Route : ---")
        self.route_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.route_label.setStyleSheet("color: #4FC3F7; padding: 2px;")
        layout.addWidget(self.route_label)

        self.region_label = QLabel("")
        self.region_label.setFont(QFont("Segoe UI", 9))
        self.region_label.setStyleSheet("color: #90A4AE; padding: 0 2px;")
        layout.addWidget(self.region_label)

        # Separator
        sep1 = QWidget()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background-color: rgba(100, 100, 140, 80);")
        layout.addWidget(sep1)

        # Spawns section
        self.spawns_label = QLabel("Spawns :")
        self.spawns_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.spawns_label.setStyleSheet("color: #A5D6A7; padding: 2px;")
        layout.addWidget(self.spawns_label)

        self.spawns_list = QLabel("En attente de detection...")
        self.spawns_list.setFont(QFont("Consolas", 9))
        self.spawns_list.setStyleSheet("color: #E0E0E0; padding: 2px 4px;")
        self.spawns_list.setWordWrap(True)
        layout.addWidget(self.spawns_list)

        # Battle panel widget (hidden by default, shows in combat)
        from .widgets.battle_panel import BattlePanelWidget
        self.battle_panel = BattlePanelWidget()
        layout.addWidget(self.battle_panel)

        # Encounter counter separator
        self.counter_sep = QWidget()
        self.counter_sep.setFixedHeight(1)
        self.counter_sep.setStyleSheet("background-color: rgba(255, 183, 77, 80);")
        layout.addWidget(self.counter_sep)

        # Encounter counter + shiny tracker
        from .widgets.encounter_counter import EncounterCounterWidget
        self.encounter_counter = EncounterCounterWidget()
        layout.addWidget(self.encounter_counter)

        # Guide panel (extended mode — hidden by default)
        from .widgets.guide_panel import GuidePanelWidget
        self.guide_panel = GuidePanelWidget()
        self.guide_panel.hide()
        layout.addWidget(self.guide_panel)

        # Pokedex widget (extended mode — hidden by default)
        from .widgets.pokedex_widget import PokedexWidget
        self.pokedex_widget = PokedexWidget()
        self.pokedex_widget.hide()
        layout.addWidget(self.pokedex_widget)

        # Team analyzer (extended mode — hidden by default)
        from .widgets.team_analyzer import TeamAnalyzerWidget
        self.team_analyzer = TeamAnalyzerWidget()
        self.team_analyzer.hide()
        layout.addWidget(self.team_analyzer)

        # Tools panel (extended mode — hidden by default)
        from .widgets.tools_panel import ToolsPanelWidget
        self.tools_panel = ToolsPanelWidget()
        self.tools_panel.hide()
        layout.addWidget(self.tools_panel)

        # Debug overlay label (shows when F11 active)
        self.debug_label = QLabel("")
        self.debug_label.setFont(QFont("Consolas", 8))
        self.debug_label.setStyleSheet("color: #FF5252;")
        self.debug_label.setWordWrap(True)
        self.debug_label.hide()
        layout.addWidget(self.debug_label)

        # Status bar
        self.status_label = QLabel("PokeMMO Companion | F9: Afficher | F10: Extended | F11: Debug")
        self.status_label.setFont(QFont("Segoe UI", 7))
        self.status_label.setStyleSheet("color: rgba(150, 150, 150, 150); padding: 2px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Start in mini mode (route + battle only)
        self._apply_mini_mode()

    def _apply_mini_mode(self):
        """Apply mini mode — show only route + battle, hide details."""
        mini = self._is_mini
        # In mini mode, hide spawns and encounter counter
        for w in [self.spawns_label, self.spawns_list, self.counter_sep,
                  self.encounter_counter]:
            w.setVisible(not mini)
        self._adjust_size()

    def _setup_auto_hide(self):
        """Setup auto-hide timer — fade out after inactivity."""
        self._last_activity = time.time()
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.timeout.connect(self._check_auto_hide)
        self._auto_hide_timer.start(1000)  # check every second

    def _check_auto_hide(self):
        """Auto-hide overlay after inactivity (configurable delay)."""
        elapsed = time.time() - self._last_activity
        delay = getattr(self.config.overlay, 'auto_hide_delay', 10)
        if elapsed > delay and not self._auto_hidden and self._is_visible:
            self._auto_hidden = True
            self._fade_to(0.45)
        elif elapsed <= delay and self._auto_hidden:
            self._auto_hidden = False
            self._fade_to(self.config.overlay.opacity)

    def _fade_to(self, target_opacity: float):
        """Animate opacity transition over 500ms."""
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(500)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(target_opacity)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._opacity_anim = anim  # prevent GC during animation
        anim.start()

    def _mark_activity(self):
        """Mark user-relevant activity (route change, battle detected)."""
        self._last_activity = time.time()
        if self._auto_hidden:
            self._auto_hidden = False
            self._fade_to(self.config.overlay.opacity)

    def _setup_click_through(self):
        """Make the window click-through using Win32 API (except grip bar)."""
        try:
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            # Note: we set WS_EX_LAYERED but NOT WS_EX_TRANSPARENT globally
            # because we want the grip bar to be interactive.
            # Click-through for the content area is handled by Qt's
            # WA_TransparentForMouseEvents on individual widgets.
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TOOLWINDOW)

            # Exclude overlay from screen capture APIs (PrintWindow, WGC, etc.)
            # WDA_EXCLUDEFROMCAPTURE = 0x00000011
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            if user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
                log.info("Overlay excluded from screen capture (SetWindowDisplayAffinity)")
            else:
                log.debug("SetWindowDisplayAffinity not supported — overlay may appear in captures")
        except Exception as e:
            log.warning(f"Click-through setup failed: {e}")

        # Make content labels click-through (but not grip bar)
        for widget in [self.route_label, self.region_label, self.spawns_label,
                       self.spawns_list, self.battle_panel, self.encounter_counter,
                       self.guide_panel, self.team_analyzer, self.status_label]:
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Note: pokedex_widget is NOT click-through because it has a search input

    # === Public API for updating the overlay ===

    def update_route(self, route_name: str, region: str = "") -> None:
        """Update the displayed route information. Skip repaint if unchanged."""
        new_text = f"Route: {route_name}"
        if self.route_label.text() == new_text:
            return  # No change — skip repaint
        self._mark_activity()
        self.route_label.setText(new_text)
        if region:
            self.region_label.setText(f"Region : {region}")
            self.region_label.show()
        else:
            self.region_label.hide()

    def update_spawns(self, spawns: list[dict]) -> None:
        """Update the spawn list display.

        Each spawn dict: {"pokemon_name": str, "type1": str, "type2": str|None,
                         "rate": float, "level_min": int, "level_max": int, "method": str}
        """
        if not spawns:
            self.spawns_list.setText("Aucune donnee de spawn")
            return

        lines = []
        for s in spawns[:8]:  # Show top 8 spawns
            name = s.get("pokemon_name", "???")
            rate = s.get("rate", 0)
            lmin = s.get("level_min", "?")
            lmax = s.get("level_max", "?")
            method = s.get("method", "walking")

            method_icon = {"walking": "🌿", "surfing": "🌊", "fishing_old": "🎣",
                          "fishing_good": "🎣", "fishing_super": "🎣",
                          "horde": "👥"}.get(method, "•")

            lines.append(f"{method_icon} {name:<14} {rate:>5.1f}%  Lv.{lmin}-{lmax}")

        self.spawns_list.setText("\n".join(lines))

    def show_battle(self, battle_info: dict) -> None:
        """Show battle information overlay. Skip repaint if same opponent."""
        new_name = battle_info.get("name", "")
        if self._last_battle_name == new_name:
            return  # Same opponent — skip repaint
        self._mark_activity()
        self._last_battle_name = new_name
        self.battle_panel.show_battle(battle_info)
        self._adjust_size()

    def hide_battle(self) -> None:
        """Hide battle information."""
        self._mark_activity()
        self._last_battle_name = ""
        self.battle_panel.hide_battle()
        self._adjust_size()

    def toggle_extended(self) -> None:
        """Cycle overlay modes: mini → normal → extended → mini."""
        if self._is_mini:
            # mini → normal
            self._is_mini = False
            self._is_compact = True
            self._apply_mini_mode()
            self.battle_panel.set_extended(False)
            for panel in [self.guide_panel, self.pokedex_widget,
                          self.team_analyzer, self.tools_panel]:
                panel.hide()
            self.resize(self.config.overlay.width, 200)
            self.update_status("Mode Normal | F10: Extended")
        elif self._is_compact:
            # normal → extended
            self._is_compact = False
            self.battle_panel.set_extended(True)
            for panel in [self.guide_panel, self.pokedex_widget,
                          self.team_analyzer, self.tools_panel]:
                panel.show()
            self.resize(self.config.overlay.width, 700)
            self.update_status("Mode Extended | F10: Mini")
        else:
            # extended → mini
            self._is_compact = True
            self._is_mini = True
            self.battle_panel.set_extended(False)
            for panel in [self.guide_panel, self.pokedex_widget,
                          self.team_analyzer, self.tools_panel]:
                panel.hide()
            self._apply_mini_mode()
            self.resize(self.config.overlay.width, 120)
            self.update_status("Mode Mini | F10: Normal")
        self._adjust_size()

    def toggle_debug(self) -> None:
        """Toggle debug mode — shows OCR regions as colored rectangles info."""
        from .widgets.debug_overlay import DEFAULT_OCR_REGIONS
        if self.debug_label.isVisible():
            self.debug_label.hide()
            self.update_status("PokeMMO Companion | F9: Afficher | F10: Extended | F11: Debug")
        else:
            lines = ["MODE DEBUG — OCR Regions:"]
            for r in DEFAULT_OCR_REGIONS:
                lines.append(
                    f"  [{r['color']:6}] {r['name']:20} "
                    f"x={r['x_ratio']:.0%} y={r['y_ratio']:.0%} "
                    f"w={r['w_ratio']:.0%} h={r['h_ratio']:.0%}"
                )
            lines.append("")
            lines.append("These are the screen regions the OCR reads.")
            lines.append("If they don't match your game layout,")
            lines.append("adjust ROI in src/detection/route_detector.py")
            lines.append("and src/detection/battle_detector.py")
            self.debug_label.setText("\n".join(lines))
            self.debug_label.show()
            self.update_status("DEBUG ON | F11 pour desactiver")
        self._adjust_size()

    def save_position(self) -> None:
        """Save current overlay position to config."""
        pos = self.pos()
        self.config.overlay.position_x = pos.x()
        self.config.overlay.position_y = pos.y()
        self.config.save()

    def increment_encounter(self, is_horde: bool = False) -> None:
        """Increment the encounter counter."""
        self.encounter_counter.increment(is_horde)

    def update_counter_location(self, location: str, region: str) -> None:
        """Update encounter counter location."""
        self.encounter_counter.set_location(location, region)

    def toggle_visibility(self) -> None:
        """Toggle overlay visibility."""
        self._is_visible = not self._is_visible
        if self._is_visible:
            self.show()
        else:
            self.hide()

    def set_opacity(self, opacity: float) -> None:
        """Set overlay opacity (0.0 - 1.0)."""
        self.setWindowOpacity(max(0.1, min(1.0, opacity)))

    def _adjust_size(self):
        """Auto-adjust window height based on content."""
        self.centralWidget().adjustSize()
        self.adjustSize()

    def update_status(self, text: str) -> None:
        """Update the status bar text."""
        self.status_label.setText(text)


class ToastNotification(QWidget):
    """Temporary notification popup."""

    def __init__(self, message: str, duration_ms: int = 5000,
                 color: str = "#4FC3F7", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(message)
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        label.setStyleSheet(f"""
            color: {color};
            background-color: rgba(20, 20, 30, 220);
            border-radius: 6px;
            padding: 8px 12px;
            border: 1px solid {color};
        """)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Position top-right
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.move(geom.width() - 350, 20)
        self.resize(330, 60)

        # Auto-dismiss
        QTimer.singleShot(duration_ms, self.close)

        self.show()
