"""Onboarding dialog — shown on first launch to collect player info."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .theme import COLORS
from .sprite_cache import get_sprite
from ..utils.constants import REGIONS


class OnboardingDialog(QDialog):
    """First-launch dialog to set up player profile."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bienvenue sur PokeMMO Companion !")
        self.setFixedSize(500, 520)
        self.setStyleSheet(f"background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']};")

        self.result_data = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Title
        title = QLabel("Bienvenue !")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Configurons ton PokeMMO Companion")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Starter sprite display
        self.sprite_label = QLabel()
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setFixedHeight(96)
        pixmap = get_sprite(25, 96)  # Pikachu default
        if pixmap:
            self.sprite_label.setPixmap(pixmap)
        layout.addWidget(self.sprite_label)

        # Region selection
        region_frame = QFrame()
        region_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        rf_layout = QVBoxLayout(region_frame)
        rf_layout.setContentsMargins(16, 12, 16, 12)

        rl = QLabel("Dans quelle region joues-tu ?")
        rl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        rf_layout.addWidget(rl)

        self.region_combo = QComboBox()
        self.region_combo.addItems(REGIONS)
        self.region_combo.setStyleSheet(f"""
            QComboBox {{
                color: {COLORS['text_primary']};
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
        """)
        self.region_combo.currentTextChanged.connect(self._on_region_change)
        rf_layout.addWidget(self.region_combo)
        layout.addWidget(region_frame)

        # Badges
        badge_frame = QFrame()
        badge_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        bf_layout = QVBoxLayout(badge_frame)
        bf_layout.setContentsMargins(16, 12, 16, 12)

        bl = QLabel("Combien de badges as-tu dans cette region ?")
        bl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        bf_layout.addWidget(bl)

        badge_row = QHBoxLayout()
        self.badge_spin = QSpinBox()
        self.badge_spin.setRange(0, 8)
        self.badge_spin.setValue(0)
        self.badge_spin.setFixedWidth(80)
        self.badge_spin.setStyleSheet(f"""
            QSpinBox {{
                color: {COLORS['text_primary']};
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }}
        """)
        badge_row.addWidget(self.badge_spin)

        self.badge_display = QLabel("........")
        self.badge_display.setFont(QFont("Segoe UI", 16))
        self.badge_display.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        badge_row.addWidget(self.badge_display)
        badge_row.addStretch()
        bf_layout.addLayout(badge_row)

        self.badge_spin.valueChanged.connect(self._on_badges_change)
        layout.addWidget(badge_frame)

        # Starter selection
        starter_frame = QFrame()
        starter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        sf_layout = QVBoxLayout(starter_frame)
        sf_layout.setContentsMargins(16, 12, 16, 12)

        sl = QLabel("Quel est ton starter prefere ?")
        sl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sf_layout.addWidget(sl)

        self.starter_combo = QComboBox()
        self.starter_combo.setStyleSheet(f"""
            QComboBox {{
                color: {COLORS['text_primary']};
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
        """)
        self.starter_combo.currentTextChanged.connect(self._on_starter_change)
        sf_layout.addWidget(self.starter_combo)
        layout.addWidget(starter_frame)

        self._on_region_change(self.region_combo.currentText())

        # Start button
        layout.addSpacing(10)
        start_btn = QPushButton("C'est parti !")
        start_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        start_btn.setFixedHeight(44)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background: {COLORS['accent_blue']};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{ background: #2196F3; }}
        """)
        start_btn.clicked.connect(self._finish)
        layout.addWidget(start_btn)

    def _on_region_change(self, region: str):
        starters = {
            "Kanto": [("Bulbasaur", 1), ("Charmander", 4), ("Squirtle", 7)],
            "Johto": [("Chikorita", 152), ("Cyndaquil", 155), ("Totodile", 158)],
            "Hoenn": [("Treecko", 252), ("Torchic", 255), ("Mudkip", 258)],
            "Sinnoh": [("Turtwig", 387), ("Chimchar", 390), ("Piplup", 393)],
            "Unova": [("Snivy", 495), ("Tepig", 498), ("Oshawott", 501)],
        }
        self.starter_combo.clear()
        for name, pid in starters.get(region, []):
            self.starter_combo.addItem(name, pid)
        self._on_starter_change(self.starter_combo.currentText())

    def _on_starter_change(self, name: str):
        pid = self.starter_combo.currentData()
        if pid:
            pixmap = get_sprite(pid, 96)
            if pixmap:
                self.sprite_label.setPixmap(pixmap)

    def _on_badges_change(self, value: int):
        display = "O" * value + "." * (8 - value)
        self.badge_display.setText(display)

    def _finish(self):
        self.result_data = {
            "region": self.region_combo.currentText(),
            "badges": self.badge_spin.value(),
            "starter": self.starter_combo.currentText(),
            "starter_id": self.starter_combo.currentData(),
        }
        self.accept()
