"""Dark gaming theme for PokeMMO Companion desktop app."""

# Color palette — dark gaming theme with Pokemon accent colors
COLORS = {
    "bg_primary": "#1a1a2e",       # Main background (very dark blue)
    "bg_secondary": "#16213e",     # Sidebar / cards background
    "bg_card": "#1f2940",          # Card backgrounds
    "bg_hover": "#263252",         # Hover state
    "bg_active": "#2a3f6e",        # Active/selected state
    "border": "#2d3a5c",           # Subtle borders
    "text_primary": "#e8eaf6",     # Primary text (near-white)
    "text_secondary": "#90a4ae",   # Secondary text (muted)
    "text_muted": "#546e7a",       # Muted text
    "accent_blue": "#4fc3f7",      # Primary accent (Pokemon blue)
    "accent_red": "#ef5350",       # Danger / weaknesses
    "accent_green": "#66bb6a",     # Success / resistances
    "accent_yellow": "#ffd54f",    # Warning / shiny
    "accent_purple": "#ce93d8",    # Special / breeding
    "accent_orange": "#ffb74d",    # Encounters
}

# Type colors (official Pokemon colors)
TYPE_COLORS = {
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0",
    "Electric": "#F7D02C", "Grass": "#7AC74C", "Ice": "#96D9D6",
    "Fighting": "#C22E28", "Poison": "#A33EA1", "Ground": "#E2BF65",
    "Flying": "#A98FF3", "Psychic": "#F95587", "Bug": "#A6B91A",
    "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC",
    "Dark": "#705746", "Steel": "#B7B7CE",
}

# Global stylesheet for the app
APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg_primary']};
}}

QWidget {{
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}

/* Sidebar */
#sidebar {{
    background-color: {COLORS['bg_secondary']};
    border-right: 1px solid {COLORS['border']};
    min-width: 200px;
    max-width: 200px;
}}

#sidebar QPushButton {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    border: none;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
}}

#sidebar QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    color: {COLORS['text_primary']};
}}

#sidebar QPushButton:checked {{
    background-color: {COLORS['bg_active']};
    color: {COLORS['accent_blue']};
    border-left: 3px solid {COLORS['accent_blue']};
}}

/* Cards */
.card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 16px;
}}

/* Search bar */
QLineEdit {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border-color: {COLORS['accent_blue']};
}}

QLineEdit::placeholder {{
    color: {COLORS['text_muted']};
}}

/* Scroll area */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {COLORS['bg_secondary']};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_muted']};
}}

/* Labels */
QLabel {{
    color: {COLORS['text_primary']};
}}

/* Tab widget */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg_card']};
    border-radius: 4px;
}}

QTabBar::tab {{
    color: {COLORS['text_secondary']};
    background-color: {COLORS['bg_secondary']};
    padding: 8px 16px;
    border: 1px solid {COLORS['border']};
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    color: {COLORS['accent_blue']};
    background-color: {COLORS['bg_card']};
}}

/* Combo box */
QComboBox {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
}}

QComboBox::drop-down {{
    border: none;
}}

/* Progress bar */
QProgressBar {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text_primary']};
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_blue']};
    border-radius: 3px;
}}
"""
