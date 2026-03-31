"""Shiny Lab page — shiny hunting dashboard with stats and session tracking."""
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QPushButton, QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from ..theme import COLORS
from ..sprite_cache import get_sprite
from ..widgets import TypeBadge
from ...utils.constants import SHINY_RATE_BASE, SHINY_RATE_DONATOR, SHINY_RATE_CHARM, SHINY_RATE_BOTH
from ...ui.widgets.encounter_counter import (
    EncounterData, cumulative_shiny_probability,
)


class StatCard(QFrame):
    """Small stat display card."""

    def __init__(self, title: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        self.setFixedHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 9))
        self.title_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class ShinyLabPage(QWidget):
    """Shiny hunting dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = EncounterData.load()
        self._setup_ui()
        self._update_display()

        # Timer for live updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_display)
        self._timer.start(5000)  # Update every 5s

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Shiny Lab")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        layout.addWidget(title)

        subtitle = QLabel("Track your shiny hunting progress")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(subtitle)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.encounters_card = StatCard("Session Encounters", "0", COLORS["accent_orange"])
        stats_row.addWidget(self.encounters_card)

        self.total_card = StatCard("Total Encounters", "0", COLORS["accent_blue"])
        stats_row.addWidget(self.total_card)

        self.shinies_card = StatCard("Shinies Found", "0", COLORS["accent_yellow"])
        stats_row.addWidget(self.shinies_card)

        self.hordes_card = StatCard("Hordes", "0", COLORS["accent_purple"])
        stats_row.addWidget(self.hordes_card)

        layout.addLayout(stats_row)

        # Probability section
        prob_frame = QFrame()
        prob_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        prob_layout = QVBoxLayout(prob_frame)
        prob_layout.setContentsMargins(20, 16, 20, 16)

        prob_title = QLabel("Shiny Probability (Session)")
        prob_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        prob_title.setStyleSheet(f"color: {COLORS['accent_yellow']};")
        prob_layout.addWidget(prob_title)

        # Progress bar
        self.prob_bar = QProgressBar()
        self.prob_bar.setRange(0, 1000)
        self.prob_bar.setValue(0)
        self.prob_bar.setTextVisible(True)
        self.prob_bar.setFormat("%v/1000")
        self.prob_bar.setFixedHeight(30)
        prob_layout.addWidget(self.prob_bar)

        self.prob_label = QLabel("0.00% chance of having found a shiny")
        self.prob_label.setFont(QFont("Segoe UI", 11))
        self.prob_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        prob_layout.addWidget(self.prob_label)

        self.rate_label = QLabel("")
        self.rate_label.setFont(QFont("Segoe UI", 9))
        self.rate_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        prob_layout.addWidget(self.rate_label)

        layout.addWidget(prob_frame)

        # Session info
        session_frame = QFrame()
        session_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        session_layout = QVBoxLayout(session_frame)
        session_layout.setContentsMargins(20, 16, 20, 16)

        session_title = QLabel("Current Session")
        session_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        session_title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        session_layout.addWidget(session_title)

        # Target + Location
        info_row = QHBoxLayout()

        self.target_label = QLabel("Target: None")
        self.target_label.setFont(QFont("Segoe UI", 10))
        self.target_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_row.addWidget(self.target_label)

        self.location_label = QLabel("Location: ---")
        self.location_label.setFont(QFont("Segoe UI", 10))
        self.location_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_row.addWidget(self.location_label)

        self.timer_label = QLabel("Time: 0h00m")
        self.timer_label.setFont(QFont("Segoe UI", 10))
        self.timer_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_row.addWidget(self.timer_label)

        session_layout.addLayout(info_row)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        reset_btn = QPushButton("Reset Session")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['accent_red']};
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['accent_red']};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        reset_btn.clicked.connect(self._reset_session)
        btn_row.addWidget(reset_btn)

        shiny_btn = QPushButton("SHINY FOUND!")
        shiny_btn.setStyleSheet(f"""
            QPushButton {{
                color: #000;
                background: {COLORS['accent_yellow']};
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #ffeb3b; }}
        """)
        shiny_btn.clicked.connect(self._mark_shiny)
        btn_row.addWidget(shiny_btn)

        btn_row.addStretch()
        session_layout.addLayout(btn_row)

        layout.addWidget(session_frame)

        # Shiny rate info
        rate_frame = QFrame()
        rate_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        rate_layout = QVBoxLayout(rate_frame)
        rate_layout.setContentsMargins(20, 16, 20, 16)

        rate_title = QLabel("PokeMMO Shiny Rates")
        rate_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        rate_title.setStyleSheet(f"color: {COLORS['text_secondary']};")
        rate_layout.addWidget(rate_title)

        rates_text = (
            f"Base rate: 1/30,000\n"
            f"Donator Status: 1/27,000\n"
            f"Shiny Charm: 1/27,000\n"
            f"Donator + Charm: 1/24,000\n"
            f"\n"
            f"Sweet Scent hordes: 5x encounters per use (best method)\n"
            f"Secret Shinies: 1/16 chance on a shiny (single encounters only)"
        )
        rates_label = QLabel(rates_text)
        rates_label.setFont(QFont("Consolas", 9))
        rates_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        rate_layout.addWidget(rates_label)

        layout.addWidget(rate_frame)
        layout.addStretch()

    def _update_display(self) -> None:
        """Refresh all stats from data."""
        self.data = EncounterData.load()
        sess = self.data.current_session

        self.encounters_card.set_value(f"{sess.encounters:,}")
        self.total_card.set_value(f"{self.data.total_encounters:,}")
        self.shinies_card.set_value(str(self.data.shinies_found))
        self.hordes_card.set_value(f"{sess.hordes:,}")

        # Probability
        prob = cumulative_shiny_probability(sess.encounters, self.data.shiny_rate)
        self.prob_bar.setValue(int(prob * 1000))
        self.prob_label.setText(f"{prob * 100:.2f}% chance of having found a shiny")

        # Color the progress bar
        if prob > 0.5:
            self.prob_bar.setStyleSheet(f"""
                QProgressBar::chunk {{ background-color: {COLORS['accent_red']}; border-radius: 3px; }}
            """)
        elif prob > 0.25:
            self.prob_bar.setStyleSheet(f"""
                QProgressBar::chunk {{ background-color: {COLORS['accent_yellow']}; border-radius: 3px; }}
            """)
        else:
            self.prob_bar.setStyleSheet(f"""
                QProgressBar::chunk {{ background-color: {COLORS['accent_green']}; border-radius: 3px; }}
            """)

        # Rate
        rate_inv = int(1 / self.data.shiny_rate) if self.data.shiny_rate > 0 else 0
        self.rate_label.setText(f"Rate: 1/{rate_inv:,}")

        # Session info
        if sess.target_pokemon:
            self.target_label.setText(f"Target: {sess.target_pokemon}")
        if sess.location:
            self.location_label.setText(f"Location: {sess.location} ({sess.region})")

        elapsed = time.time() - sess.started_at
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        self.timer_label.setText(f"Time: {hours}h{minutes:02d}m")

    def _reset_session(self) -> None:
        from ...ui.widgets.encounter_counter import EncounterSession
        self.data.current_session = EncounterSession()
        self.data.save()
        self._update_display()

    def _mark_shiny(self) -> None:
        self.data.shinies_found += 1
        self.data.save()
        self._update_display()
