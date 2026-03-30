"""Progression guide panel — contextual coaching based on player location.

Shows the current step, next objective, and recommendations based on
where the player is in the game.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class GuidePanelWidget(QWidget):
    """Mode Coach GPS — contextual progression guide."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_region: str = ""
        self._current_step: int = 0
        self._badges: int = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(100, 181, 246, 80);")
        layout.addWidget(sep)

        # Header
        header = QLabel("Guide")
        header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header.setStyleSheet("color: #64B5F6;")
        layout.addWidget(header)

        # Badge count
        self.badge_label = QLabel("")
        self.badge_label.setFont(QFont("Segoe UI", 9))
        self.badge_label.setStyleSheet("color: #90CAF9;")
        layout.addWidget(self.badge_label)

        # Current objective
        self.objective_label = QLabel("Detecting location...")
        self.objective_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.objective_label.setStyleSheet("color: #E3F2FD;")
        self.objective_label.setWordWrap(True)
        layout.addWidget(self.objective_label)

        # Description/tip
        self.tip_label = QLabel("")
        self.tip_label.setFont(QFont("Segoe UI", 8))
        self.tip_label.setStyleSheet("color: #B0BEC5;")
        self.tip_label.setWordWrap(True)
        layout.addWidget(self.tip_label)

        # Recommended level
        self.level_label = QLabel("")
        self.level_label.setFont(QFont("Segoe UI", 8))
        self.level_label.setStyleSheet("color: #A5D6A7;")
        layout.addWidget(self.level_label)

        # Next step preview
        self.next_label = QLabel("")
        self.next_label.setFont(QFont("Segoe UI", 8))
        self.next_label.setStyleSheet("color: #78909C;")
        self.next_label.setWordWrap(True)
        layout.addWidget(self.next_label)

    def update_location(self, route_name: str, region: str) -> None:
        """Update guide based on current location.

        Uses route min_badges to infer progression and shows the
        relevant walkthrough step.
        """
        if not self.db or not region:
            return

        self._current_region = region

        # Infer badges from route
        min_badges = self.db.get_route_min_badges(route_name, region)
        if min_badges > self._badges:
            self._badges = min_badges

        # Update badge display
        badge_icons = "O" * self._badges + "." * (8 - self._badges)
        self.badge_label.setText(f"Badges: [{badge_icons}] {self._badges}/8")

        # Find current progression step
        current = self.db.get_current_step(region, route_name)
        if current:
            self._current_step = current["step"]
            self.objective_label.setText(current["title"])
            self.tip_label.setText(current.get("description", ""))
            rec_level = current.get("recommended_level", 0)
            if rec_level:
                self.level_label.setText(f"Rec. Level: {rec_level}")
            else:
                self.level_label.setText("")
        else:
            # No exact match — show step based on badge count
            progression = self.db.get_progression(region)
            # Find the step matching current badge count
            for step in progression:
                if step.get("badge_number", 0) >= self._badges:
                    self._current_step = step["step"]
                    self.objective_label.setText(f"Next: {step['title']}")
                    self.tip_label.setText(step.get("description", ""))
                    rec_level = step.get("recommended_level", 0)
                    if rec_level:
                        self.level_label.setText(f"Rec. Level: {rec_level}")
                    break

        # Show next step
        next_step = self.db.get_next_step(region, self._current_step)
        if next_step:
            self.next_label.setText(f"Then: {next_step['title']}")
        else:
            self.next_label.setText("Final step reached!")

    def set_badges(self, count: int) -> None:
        """Manually set badge count (from setup or detection)."""
        self._badges = max(0, min(8, count))
        badge_icons = "O" * self._badges + "." * (8 - self._badges)
        self.badge_label.setText(f"Badges: [{badge_icons}] {self._badges}/8")

    def get_compact_text(self) -> str:
        """Get one-line summary for compact mode."""
        return f"{self._badges}/8 badges | {self.objective_label.text()}"
