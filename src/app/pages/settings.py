"""Settings page — app configuration, overlay settings, about."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QSlider, QComboBox, QPushButton, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..theme import COLORS
from ...utils.config import AppConfig


class SettingsSection(QFrame):
    """A settings section card."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            SettingsSection {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(10)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['accent_blue']};")
        self._layout.addWidget(header)

    def add_row(self, label_text: str, widget: QWidget) -> None:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 10))
        label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        label.setFixedWidth(180)
        row.addWidget(label)
        row.addWidget(widget)
        row.addStretch()
        self._layout.addLayout(row)


class SettingsPage(QWidget):
    """Settings page with overlay config and about info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AppConfig.load()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Options")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # Overlay settings
        overlay_section = SettingsSection("Overlay")

        # Opacity slider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(self.config.overlay.opacity * 100))
        self.opacity_slider.setFixedWidth(200)
        self.opacity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['bg_secondary']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['accent_blue']};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
        """)
        overlay_section.add_row("Opacite Overlay", self.opacity_slider)

        # Toggle hotkey
        self.hotkey_input = QLineEdit(self.config.overlay.toggle_hotkey)
        self.hotkey_input.setFixedWidth(100)
        self.hotkey_input.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            background: {COLORS['bg_secondary']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 4px 8px;
        """)
        overlay_section.add_row("Raccourci Affichage", self.hotkey_input)

        # Capture FPS
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["1", "2", "3", "5"])
        self.fps_combo.setCurrentText(str(self.config.capture.target_fps))
        self.fps_combo.setFixedWidth(80)
        overlay_section.add_row("FPS Detection", self.fps_combo)

        layout.addWidget(overlay_section)

        # OCR settings
        ocr_section = SettingsSection("OCR (Lecture Texte)")

        self.tesseract_input = QLineEdit(self.config.ocr.tesseract_path)
        self.tesseract_input.setFixedWidth(350)
        self.tesseract_input.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            background: {COLORS['bg_secondary']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 4px 8px;
        """)
        ocr_section.add_row("Chemin Tesseract", self.tesseract_input)

        self.game_title_input = QLineEdit(self.config.capture.game_window_title)
        self.game_title_input.setFixedWidth(200)
        self.game_title_input.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            background: {COLORS['bg_secondary']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 4px 8px;
        """)
        ocr_section.add_row("Titre Fenetre Jeu", self.game_title_input)

        layout.addWidget(ocr_section)

        # Shiny hunting settings
        shiny_section = SettingsSection("Chasse au Shiny")

        self.donator_check = QCheckBox("Donator Status (1/27,000)")
        self.donator_check.setStyleSheet(f"color: {COLORS['text_primary']};")
        shiny_section.add_row("Modificateurs de Taux", self.donator_check)

        self.charm_check = QCheckBox("Shiny Charm (1/27,000)")
        self.charm_check.setStyleSheet(f"color: {COLORS['text_primary']};")
        shiny_section.add_row("", self.charm_check)

        layout.addWidget(shiny_section)

        # Save button
        save_btn = QPushButton("Sauvegarder")
        save_btn.setFixedWidth(150)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background: {COLORS['accent_blue']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #2196F3; }}
        """)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        # About section
        about_section = SettingsSection("A Propos")
        about_text = QLabel(
            "PokeMMO Companion v0.2.0\n\n"
            "Real-time overlay and desktop companion for PokeMMO.\n"
            "Provides route detection, spawn data, battle type counters,\n"
            "shiny tracking, team building, and progression guides.\n\n"
            "Built with Python + PyQt6\n"
            "Pokemon data from PokeAPI + PokeMMOZone\n"
            "Sprites from PokeAPI\n\n"
            "github.com/Ladydzer/pokemmo-companion"
        )
        about_text.setFont(QFont("Segoe UI", 9))
        about_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        about_text.setWordWrap(True)
        about_section._layout.addWidget(about_text)
        layout.addWidget(about_section)

        layout.addStretch()

    def _save(self) -> None:
        """Save settings to config file."""
        self.config.overlay.opacity = self.opacity_slider.value() / 100.0
        self.config.overlay.toggle_hotkey = self.hotkey_input.text()
        self.config.capture.target_fps = int(self.fps_combo.currentText())
        self.config.ocr.tesseract_path = self.tesseract_input.text()
        self.config.capture.game_window_title = self.game_title_input.text()
        self.config.save()

        # Visual feedback
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Options", "Settings saved! Restart the app to apply changes.")
