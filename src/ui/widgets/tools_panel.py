"""Tools panel — IV calculator, EV guide, breeding assistant in one widget."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTabWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...tools.iv_calculator import (
    estimate_ivs, format_iv_results, NATURES, STAT_NAMES,
    calc_hp, calc_stat, get_nature_modifier,
)
from ...tools.ev_training import get_ev_spots, format_ev_plan, POWER_ITEMS
from ...tools.breeding import get_breeding_cost_estimate, format_breeding_plan


class IVCalculatorTab(QWidget):
    """IV Calculator tab."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Pokemon name input
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Pokemon:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ex: Dracaufeu")
        self.name_input.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555; border-radius: 3px; padding: 2px 4px;")
        name_row.addWidget(self.name_input)
        layout.addLayout(name_row)

        # Level + Nature
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Lv:"))
        self.level_input = QLineEdit("50")
        self.level_input.setFixedWidth(40)
        self.level_input.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555; border-radius: 3px; padding: 2px;")
        row2.addWidget(self.level_input)

        row2.addWidget(QLabel("Nature:"))
        self.nature_combo = QComboBox()
        self.nature_combo.addItems(sorted(NATURES.keys()))
        self.nature_combo.setCurrentText("Hardy")
        self.nature_combo.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555;")
        row2.addWidget(self.nature_combo)
        layout.addLayout(row2)

        # Stat inputs
        self.stat_inputs = {}
        stat_labels = {"hp": "HP", "attack": "Atk", "defense": "Def",
                       "sp_attack": "SpA", "sp_defense": "SpD", "speed": "Spe"}
        for stat in STAT_NAMES:
            row = QHBoxLayout()
            lbl = QLabel(f"{stat_labels[stat]}:")
            lbl.setFixedWidth(30)
            row.addWidget(lbl)
            inp = QLineEdit()
            inp.setPlaceholderText("0")
            inp.setFixedWidth(50)
            inp.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555; border-radius: 3px; padding: 2px;")
            self.stat_inputs[stat] = inp
            row.addWidget(inp)
            row.addStretch()
            layout.addLayout(row)

        # Calculate button
        calc_btn = QPushButton("Calculer IVs")
        calc_btn.setStyleSheet("color: white; background: #1565C0; border-radius: 3px; padding: 4px;")
        calc_btn.clicked.connect(self._calculate)
        layout.addWidget(calc_btn)

        # Results
        self.result_label = QLabel("")
        self.result_label.setFont(QFont("Consolas", 9))
        self.result_label.setStyleSheet("color: #A5D6A7;")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        # Style all labels
        for child in self.findChildren(QLabel):
            if not child.styleSheet():
                child.setFont(QFont("Segoe UI", 8))
                child.setStyleSheet("color: #B0BEC5;")

    def _calculate(self):
        pokemon_name = self.name_input.text().strip()
        if not pokemon_name or not self.db:
            self.result_label.setText("Entre un nom de Pokemon")
            return

        pokemon = self.db.get_pokemon_by_name(pokemon_name)
        if not pokemon:
            self.result_label.setText(f"Pokemon '{pokemon_name}' introuvable")
            return

        try:
            level = int(self.level_input.text())
        except ValueError:
            level = 50

        nature = self.nature_combo.currentText()

        base_stats = {
            "hp": pokemon["hp"], "attack": pokemon["attack"],
            "defense": pokemon["defense"], "sp_attack": pokemon["sp_attack"],
            "sp_defense": pokemon["sp_defense"], "speed": pokemon["speed"],
        }

        visible_stats = {}
        for stat, inp in self.stat_inputs.items():
            try:
                visible_stats[stat] = int(inp.text())
            except ValueError:
                visible_stats[stat] = 0

        if all(v == 0 for v in visible_stats.values()):
            self.result_label.setText("Entre les stats visibles du jeu")
            return

        results = estimate_ivs(base_stats, visible_stats, level, nature)
        self.result_label.setText(format_iv_results(results))


class EVTrainingTab(QWidget):
    """EV Training guide tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Stat selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Stat:"))
        self.stat_combo = QComboBox()
        self.stat_combo.addItems(["HP", "Attack", "Defense", "Sp.Attack", "Sp.Defense", "Speed"])
        self.stat_combo.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555;")
        self.stat_combo.currentIndexChanged.connect(self._update)
        row.addWidget(self.stat_combo)

        row.addWidget(QLabel("Region:"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["Tous", "Kanto", "Johto", "Hoenn", "Sinnoh", "Unova"])
        self.region_combo.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555;")
        self.region_combo.currentIndexChanged.connect(self._update)
        row.addWidget(self.region_combo)
        layout.addLayout(row)

        # Results
        self.result_label = QLabel("Selectionne une stat")
        self.result_label.setFont(QFont("Consolas", 8))
        self.result_label.setStyleSheet("color: #E0E0E0;")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        # Style labels
        for child in self.findChildren(QLabel):
            if "Consolas" not in (child.font().family() or ""):
                child.setFont(QFont("Segoe UI", 8))
                if not child.styleSheet():
                    child.setStyleSheet("color: #B0BEC5;")

        self._update()

    def _update(self):
        stat_map = {"HP": "hp", "Attack": "attack", "Defense": "defense",
                    "Sp.Attack": "sp_attack", "Sp.Defense": "sp_defense", "Speed": "speed"}
        stat = stat_map.get(self.stat_combo.currentText(), "speed")
        region = self.region_combo.currentText()
        if region == "Tous":
            region = None

        spots = get_ev_spots(stat, region)
        if not spots:
            self.result_label.setText("Aucun spot trouve")
            return

        power_item = POWER_ITEMS.get(stat, "Power Item")
        lines = [f"Meilleurs {stat.upper()} spots d'entrainement :"]
        for s in spots[:8]:
            lines.append(
                f"  {s['pokemon']:12} +{s['ev_yield']} | {s['location']:18} ({s['region']})"
            )
            if s.get('notes'):
                lines.append(f"    {s['notes']}")

        lines.append(f"\nItem: {power_item} (+4 par combat)")
        lines.append("Pokerus: doubles all EV gains")
        self.result_label.setText("\n".join(lines))


class BreedingTab(QWidget):
    """Breeding assistant tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Target IVs selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Target IVs:"))
        self.iv_combo = QComboBox()
        self.iv_combo.addItems(["1x31", "2x31", "3x31", "4x31", "5x31", "6x31"])
        self.iv_combo.setCurrentIndex(4)  # Default 5x31
        self.iv_combo.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555;")
        self.iv_combo.currentIndexChanged.connect(self._update)
        row.addWidget(self.iv_combo)
        layout.addLayout(row)

        # Pokemon name
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Pokemon:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ex: Carchacroc")
        self.name_input.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555; border-radius: 3px; padding: 2px 4px;")
        row2.addWidget(self.name_input)
        layout.addLayout(row2)

        # Nature
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Nature:"))
        self.nature_input = QLineEdit()
        self.nature_input.setPlaceholderText("ex: Jovial")
        self.nature_input.setStyleSheet("color: #E0E0E0; background: rgba(40,40,60,200); border: 1px solid #555; border-radius: 3px; padding: 2px 4px;")
        row3.addWidget(self.nature_input)
        layout.addLayout(row3)

        # Results
        self.result_label = QLabel("")
        self.result_label.setFont(QFont("Consolas", 8))
        self.result_label.setStyleSheet("color: #E0E0E0;")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        for child in self.findChildren(QLabel):
            if "Consolas" not in (child.font().family() or ""):
                child.setFont(QFont("Segoe UI", 8))
                if not child.styleSheet():
                    child.setStyleSheet("color: #B0BEC5;")

        self._update()

    def _update(self):
        target_ivs = self.iv_combo.currentIndex() + 1
        name = self.name_input.text().strip() or "Pokemon"
        nature = self.nature_input.text().strip()
        self.result_label.setText(format_breeding_plan(name, target_ivs, nature))


class ToolsPanelWidget(QWidget):
    """Tabbed tools panel with IV calc, EV guide, breeding."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(0)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(100, 200, 255, 80);")
        layout.addWidget(sep)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(100,100,140,80); background: transparent; }
            QTabBar::tab { color: #B0BEC5; background: rgba(40,40,60,150); padding: 4px 8px;
                           border: 1px solid rgba(100,100,140,60); margin-right: 2px; }
            QTabBar::tab:selected { color: #4FC3F7; background: rgba(30,30,50,200); }
        """)

        self.iv_tab = IVCalculatorTab(self.db)
        tabs.addTab(self.iv_tab, "IV Calc")

        self.ev_tab = EVTrainingTab()
        tabs.addTab(self.ev_tab, "EV Train")

        self.breed_tab = BreedingTab()
        tabs.addTab(self.breed_tab, "Breeding")

        layout.addWidget(tabs)
