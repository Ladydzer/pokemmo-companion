"""Tests for the desktop companion app — widget creation, data display, navigation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication

# Need a QApplication for widget tests
_app = QApplication.instance() or QApplication(sys.argv)

from src.data.database import Database
from src.data.type_chart import get_battle_summary
from src.app.main_window import MainWindow
from src.app.widgets import StatBar, RadarChart, PokemonCard, TypeBadge
from src.app.sprite_cache import get_sprite, sprite_count, has_sprites
from src.app.splash import SplashScreen
from src.tools.iv_calculator import calc_hp, calc_stat, get_nature_modifier
from src.tools.ev_training import get_ev_spots, calc_battles_needed
from src.tools.breeding import get_breeding_cost_estimate


def test_database_loaded():
    db = Database()
    assert db.get_pokemon_count() == 649
    assert db.get_route_count() > 0
    assert db.get_spawn_count() > 0


def test_pokemon_lookup():
    db = Database()
    p = db.get_pokemon_by_name("Charizard")
    assert p is not None
    assert p["type1"] == "Fire"
    assert p["type2"] == "Flying"
    assert p["hp"] == 78


def test_pokemon_search():
    db = Database()
    results = db.search_pokemon("pika")
    assert len(results) >= 1
    assert results[0]["name"] == "Pikachu"


def test_spawns_for_route():
    db = Database()
    spawns = db.get_spawns_for_route("Viridian Forest", "Kanto")
    assert len(spawns) > 0
    names = [s["pokemon_name"] for s in spawns]
    assert "Caterpie" in names or "Weedle" in names


def test_pokemon_locations():
    db = Database()
    locs = db.get_pokemon_locations("Pikachu")
    assert len(locs) > 0
    regions = [l["region"] for l in locs]
    assert "Kanto" in regions


def test_progression():
    db = Database()
    prog = db.get_progression("Kanto")
    assert len(prog) > 10
    assert prog[0]["title"] == "Start in Pallet Town"


def test_route_min_badges():
    db = Database()
    assert db.get_route_min_badges("Pallet Town", "Kanto") == 0
    assert db.get_route_min_badges("Cerulean City", "Kanto") >= 1
    assert db.get_route_min_badges("Victory Road", "Kanto") == 8


def test_type_chart_battle_summary():
    # Charizard Fire/Flying
    summary = get_battle_summary(["Fire", "Flying"])
    assert "Rock" in summary["weak_to"]
    assert summary["weak_to"]["Rock"] == 4.0
    assert "Ground" in summary["immune_to"]


def test_sprites_exist():
    assert has_sprites()
    assert sprite_count() == 649


def test_sprite_load():
    pixmap = get_sprite(25)  # Pikachu
    assert pixmap is not None
    assert not pixmap.isNull()


def test_main_window_creation():
    db = Database()
    window = MainWindow(db)
    assert window.pages.count() == 6
    assert len(window._nav_buttons) == 6


def test_navigation():
    db = Database()
    window = MainWindow(db)
    for page_name, expected_idx in [("Dashboard", 0), ("Pokedex", 1),
                                      ("Battle", 2), ("Team", 3),
                                      ("Shiny Lab", 4), ("Settings", 5)]:
        window._navigate(page_name)
        assert window.pages.currentIndex() == expected_idx


def test_splash_screen():
    splash = SplashScreen()
    splash.set_progress(50, "Testing...")
    splash.set_progress(100, "Done!")
    assert splash.progress.value() == 100


def test_stat_bar_widget():
    bar = StatBar("HP", 78)
    assert bar.value == 78
    assert bar.label == "HP"


def test_radar_chart():
    chart = RadarChart([78, 84, 78, 109, 85, 100])
    assert chart.stats == [78, 84, 78, 109, 85, 100]


def test_pokemon_card():
    card = PokemonCard(6, "Charizard", "Fire", "Flying")
    assert card.pokemon_id == 6


def test_ev_training_spots():
    spots = get_ev_spots("speed", "Kanto")
    assert len(spots) > 0
    assert spots[0]["pokemon"] == "Diglett"


def test_ev_battles_needed():
    # 252 EVs, 1 per battle, no items
    assert calc_battles_needed(252, 1) == 252
    # With power item (+4 = 5 per battle)
    assert calc_battles_needed(252, 1, has_power_item=True) == 51
    # With power item + pokerus (5*2 = 10 per battle)
    assert calc_battles_needed(252, 1, has_pokerus=True, has_power_item=True) == 26


def test_breeding_cost():
    cost = get_breeding_cost_estimate(5)
    assert cost["parents"] == 32
    assert cost["cost_min"] == 800000


def test_nature_modifiers():
    assert get_nature_modifier("Adamant", "attack") == 1.1
    assert get_nature_modifier("Adamant", "sp_attack") == 0.9
    assert get_nature_modifier("Jolly", "speed") == 1.1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS: {test_fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test_fn.__name__} -- {e}")

    print(f"\n{passed} passed, {failed} failed out of {passed + failed} tests")
    if failed > 0:
        sys.exit(1)
