"""Team analyzer widget — shows type coverage and weaknesses for a team."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...utils.constants import TYPES
from ...data.type_chart import get_dual_effectiveness, get_effectiveness
from .battle_panel import TypeBadge, TYPE_COLORS


class TeamAnalyzerWidget(QWidget):
    """Analyzes a team's type coverage and common weaknesses."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._team: list[dict] = []  # List of pokemon dicts
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255, 235, 59, 80);")
        layout.addWidget(sep)

        # Header
        header = QLabel("Analyse d'Equipe")
        header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFF176;")
        layout.addWidget(header)

        # Team members
        self.team_label = QLabel("Aucune donnee d'equipe")
        self.team_label.setFont(QFont("Consolas", 8))
        self.team_label.setStyleSheet("color: #E0E0E0;")
        self.team_label.setWordWrap(True)
        layout.addWidget(self.team_label)

        # Coverage summary
        self.coverage_label = QLabel("")
        self.coverage_label.setFont(QFont("Segoe UI", 8))
        self.coverage_label.setStyleSheet("color: #A5D6A7;")
        self.coverage_label.setWordWrap(True)
        layout.addWidget(self.coverage_label)

        # Weaknesses summary
        self.weakness_label = QLabel("")
        self.weakness_label.setFont(QFont("Segoe UI", 8))
        self.weakness_label.setStyleSheet("color: #EF9A9A;")
        self.weakness_label.setWordWrap(True)
        layout.addWidget(self.weakness_label)

    def set_team(self, pokemon_list: list[dict]) -> None:
        """Set the team for analysis.

        Each dict should have at minimum: name, type1, type2 (optional)
        """
        self._team = pokemon_list[:6]
        self._analyze()

    def add_pokemon(self, pokemon: dict) -> None:
        """Add a Pokemon to the team (max 6)."""
        if len(self._team) < 6:
            self._team.append(pokemon)
            self._analyze()

    def clear_team(self) -> None:
        """Clear the team."""
        self._team = []
        self.team_label.setText("Aucune donnee d'equipe")
        self.coverage_label.setText("")
        self.weakness_label.setText("")

    def _analyze(self) -> None:
        """Run type analysis on the current team."""
        if not self._team:
            return

        # Display team members
        team_lines = []
        for p in self._team:
            t2 = f"/{p.get('type2', '')}" if p.get('type2') else ""
            team_lines.append(f"{p['name']} ({p['type1']}{t2})")
        self.team_label.setText(" | ".join(team_lines))

        # Calculate offensive coverage (what types can the team hit super-effectively)
        covered_types = set()
        for p in self._team:
            p_types = [p["type1"]]
            if p.get("type2"):
                p_types.append(p["type2"])
            for atk_type in p_types:
                for def_type in TYPES:
                    if get_effectiveness(atk_type, def_type) > 1.0:
                        covered_types.add(def_type)

        uncovered = set(TYPES) - covered_types
        coverage_pct = len(covered_types) / len(TYPES) * 100

        coverage_text = f"Coverage: {coverage_pct:.0f}% ({len(covered_types)}/{len(TYPES)} types)"
        if uncovered:
            coverage_text += f"\nNon couverts : {', '.join(sorted(uncovered))}"
        self.coverage_label.setText(coverage_text)

        # Calculate defensive weaknesses (what types hit the whole team hard)
        type_weakness_count: dict[str, int] = {t: 0 for t in TYPES}
        for p in self._team:
            p_types = [p["type1"]]
            if p.get("type2"):
                p_types.append(p["type2"])
            for atk_type in TYPES:
                mult = get_dual_effectiveness(atk_type, p_types)
                if mult > 1.0:
                    type_weakness_count[atk_type] += 1

        # Find common weaknesses (types that hit 3+ team members)
        common_weak = {t: c for t, c in type_weakness_count.items() if c >= 3}
        shared_weak = {t: c for t, c in type_weakness_count.items() if c >= 2}

        if common_weak:
            weak_parts = [f"{t} ({c}/6)" for t, c in sorted(common_weak.items(), key=lambda x: -x[1])]
            self.weakness_label.setText(f"DANGER : {', '.join(weak_parts)}")
            self.weakness_label.setStyleSheet("color: #EF5350;")
        elif shared_weak:
            weak_parts = [f"{t} ({c}/6)" for t, c in sorted(shared_weak.items(), key=lambda x: -x[1])[:4]]
            self.weakness_label.setText(f"Attention : {', '.join(weak_parts)}")
            self.weakness_label.setStyleSheet("color: #FFB74D;")
        else:
            self.weakness_label.setText("Bon equilibre !")
            self.weakness_label.setStyleSheet("color: #A5D6A7;")
