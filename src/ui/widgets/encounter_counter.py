"""Encounter counter + shiny tracker widget."""
import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...utils.constants import SHINY_RATE_BASE, SHINY_RATE_DONATOR, SHINY_RATE_CHARM, SHINY_RATE_BOTH
from ...utils.config import CONFIG_DIR


COUNTER_FILE = CONFIG_DIR / "encounter_data.json"


@dataclass
class EncounterSession:
    """Data for a single hunting session."""
    target_pokemon: str = ""
    encounters: int = 0
    hordes: int = 0
    started_at: float = field(default_factory=time.time)
    location: str = ""
    region: str = ""


@dataclass
class EncounterData:
    """Persistent encounter tracking data."""
    total_encounters: int = 0
    total_hordes: int = 0
    shinies_found: int = 0
    current_session: EncounterSession = field(default_factory=EncounterSession)
    shiny_rate: float = SHINY_RATE_BASE
    use_donator: bool = False
    use_charm: bool = False

    def save(self) -> None:
        COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        with open(COUNTER_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "EncounterData":
        if COUNTER_FILE.exists():
            try:
                with open(COUNTER_FILE) as f:
                    data = json.load(f)
                ed = cls()
                ed.total_encounters = data.get("total_encounters", 0)
                ed.total_hordes = data.get("total_hordes", 0)
                ed.shinies_found = data.get("shinies_found", 0)
                ed.use_donator = data.get("use_donator", False)
                ed.use_charm = data.get("use_charm", False)
                ed.shiny_rate = _calc_rate(ed.use_donator, ed.use_charm)
                sess = data.get("current_session", {})
                ed.current_session = EncounterSession(
                    target_pokemon=sess.get("target_pokemon", ""),
                    encounters=sess.get("encounters", 0),
                    hordes=sess.get("hordes", 0),
                    started_at=sess.get("started_at", time.time()),
                    location=sess.get("location", ""),
                    region=sess.get("region", ""),
                )
                return ed
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()


def _calc_rate(donator: bool, charm: bool) -> float:
    if donator and charm:
        return SHINY_RATE_BOTH
    elif donator:
        return SHINY_RATE_DONATOR
    elif charm:
        return SHINY_RATE_CHARM
    return SHINY_RATE_BASE


def cumulative_shiny_probability(encounters: int, rate: float) -> float:
    """Calculate probability of having found at least 1 shiny in N encounters.

    P = 1 - (1 - rate)^encounters
    """
    if encounters <= 0 or rate <= 0:
        return 0.0
    return 1.0 - (1.0 - rate) ** encounters


class EncounterCounterWidget(QWidget):
    """Encounter counter + shiny probability display."""

    shiny_alert = pyqtSignal()  # Emitted when user marks a shiny found

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = EncounterData.load()
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        header = QLabel("Compteur Rencontres")
        header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFB74D;")
        layout.addWidget(header)

        # Session encounters
        self.session_label = QLabel("Session: 0")
        self.session_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.session_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(self.session_label)

        # Total encounters
        self.total_label = QLabel("Total: 0")
        self.total_label.setFont(QFont("Consolas", 9))
        self.total_label.setStyleSheet("color: #B0BEC5;")
        layout.addWidget(self.total_label)

        # Shiny probability
        self.prob_label = QLabel("Shiny chance: 0.00%")
        self.prob_label.setFont(QFont("Consolas", 9))
        self.prob_label.setStyleSheet("color: #FFD54F;")
        layout.addWidget(self.prob_label)

        # Shiny rate display
        self.rate_label = QLabel("")
        self.rate_label.setFont(QFont("Segoe UI", 8))
        self.rate_label.setStyleSheet("color: #78909C;")
        layout.addWidget(self.rate_label)

        # Session timer
        self.timer_label = QLabel("")
        self.timer_label.setFont(QFont("Segoe UI", 8))
        self.timer_label.setStyleSheet("color: #78909C;")
        layout.addWidget(self.timer_label)

    def increment(self, is_horde: bool = False) -> None:
        """Add an encounter. Call this when a wild battle starts."""
        count = 5 if is_horde else 1
        self.data.current_session.encounters += count
        self.data.total_encounters += count
        if is_horde:
            self.data.current_session.hordes += 1
            self.data.total_hordes += 1
        self._update_display()

        # Auto-save every 10 encounters
        if self.data.total_encounters % 10 == 0:
            self.data.save()

    def mark_shiny_found(self) -> None:
        """Mark that a shiny was found."""
        self.data.shinies_found += 1
        self.data.save()
        self.shiny_alert.emit()

    def reset_session(self) -> None:
        """Reset the current session counter."""
        self.data.current_session = EncounterSession()
        self._update_display()
        self.data.save()

    def set_location(self, location: str, region: str) -> None:
        """Update the current hunting location."""
        self.data.current_session.location = location
        self.data.current_session.region = region

    def set_target(self, pokemon_name: str) -> None:
        """Set the target Pokemon for this hunting session."""
        self.data.current_session.target_pokemon = pokemon_name

    def _update_display(self) -> None:
        """Refresh all display labels."""
        sess = self.data.current_session

        # Session encounters
        session_text = f"Session: {sess.encounters:,}"
        if sess.hordes > 0:
            session_text += f" ({sess.hordes} hordes)"
        if sess.target_pokemon:
            session_text = f"[{sess.target_pokemon}] {session_text}"
        self.session_label.setText(session_text)

        # Total
        self.total_label.setText(
            f"Total: {self.data.total_encounters:,} | Shinies: {self.data.shinies_found}"
        )

        # Shiny probability for session
        prob = cumulative_shiny_probability(sess.encounters, self.data.shiny_rate)
        self.prob_label.setText(f"Shiny chance: {prob * 100:.2f}%")

        # Color the probability based on value
        if prob > 0.5:
            self.prob_label.setStyleSheet("color: #EF5350;")  # Red = unlucky
        elif prob > 0.25:
            self.prob_label.setStyleSheet("color: #FFD54F;")  # Yellow
        else:
            self.prob_label.setStyleSheet("color: #81C784;")  # Green = normal

        # Rate display
        rate_inv = int(1 / self.data.shiny_rate) if self.data.shiny_rate > 0 else 0
        modifiers = []
        if self.data.use_donator:
            modifiers.append("Donator")
        if self.data.use_charm:
            modifiers.append("Charm")
        mod_str = f" ({'+'.join(modifiers)})" if modifiers else ""
        self.rate_label.setText(f"Rate: 1/{rate_inv:,}{mod_str}")

        # Session timer
        elapsed = time.time() - sess.started_at
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        self.timer_label.setText(f"Time: {hours}h{minutes:02d}m")

    def get_compact_text(self) -> str:
        """Get a compact one-line summary for the overlay compact mode."""
        sess = self.data.current_session
        prob = cumulative_shiny_probability(sess.encounters, self.data.shiny_rate)
        return f"#{sess.encounters:,} | {prob * 100:.1f}% shiny"

    def save(self) -> None:
        """Save encounter data to disk."""
        self.data.save()
