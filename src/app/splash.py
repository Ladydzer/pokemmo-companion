"""Splash screen — shown at startup while loading data."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient

from .theme import COLORS


class SplashScreen(QWidget):
    """Animated splash screen with progress bar."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(450, 280)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Center on screen
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.move(
                (geom.width() - self.width()) // 2,
                (geom.height() - self.height()) // 2,
            )

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(8)

        layout.addStretch()

        # Title
        title = QLabel("PokeMMO")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Companion")
        subtitle.setFont(QFont("Segoe UI", 16))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Status text
        self.status_label = QLabel("Loading...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_secondary']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_blue']};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress)

        # Version
        version = QLabel("v0.5.0")
        version.setFont(QFont("Segoe UI", 8))
        version.setStyleSheet(f"color: {COLORS['text_muted']};")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addStretch()

    def paintEvent(self, event):
        """Draw rounded dark background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(26, 26, 46, 240))
        gradient.setColorAt(1, QColor(22, 33, 62, 240))

        painter.setBrush(gradient)
        painter.setPen(QColor(COLORS["border"]))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.end()

    def set_progress(self, value: int, status: str = "") -> None:
        """Update progress bar and status text."""
        self.progress.setValue(value)
        if status:
            self.status_label.setText(status)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
