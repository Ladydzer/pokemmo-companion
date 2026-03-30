"""Tests for IV calculator — Gen 5 stat formulas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.iv_calculator import (
    calc_hp, calc_stat, estimate_ivs, get_nature_modifier,
    NATURES, STAT_NAMES,
)


def test_hp_formula():
    # Charizard base HP 78, IV 31, EV 0, Level 50
    # HP = ((2*78 + 31 + 0) * 50 / 100) + 50 + 10 = 153
    result = calc_hp(78, 31, 0, 50)
    assert result == 153

    # Level 100, max EVs: ((2*78+31+63)*100/100) + 100 + 10 = 360
    result = calc_hp(78, 31, 252, 100)
    assert result == 360


def test_stat_formula():
    # Charizard base Speed 100, IV 31, EV 0, Level 50, neutral nature
    # Stat = ((2*100 + 31 + 0) * 50 / 100 + 5) * 1.0 = 120
    result = calc_stat(100, 31, 0, 50, 1.0)
    assert result == 120

    # With +speed nature (1.1)
    result = calc_stat(100, 31, 0, 50, 1.1)
    assert result == 132

    # With -speed nature (0.9)
    result = calc_stat(100, 31, 0, 50, 0.9)
    assert result == 108


def test_nature_modifiers():
    assert get_nature_modifier("Timid", "speed") == 1.1
    assert get_nature_modifier("Timid", "attack") == 0.9
    assert get_nature_modifier("Timid", "defense") == 1.0
    assert get_nature_modifier("Hardy", "attack") == 1.0
    assert get_nature_modifier("Adamant", "attack") == 1.1
    assert get_nature_modifier("Adamant", "sp_attack") == 0.9


def test_all_natures_defined():
    assert len(NATURES) == 25


def test_iv_estimation_perfect():
    # Charizard Lv50 Timid, all 31 IVs, 0 EVs
    base = {"hp": 78, "attack": 84, "defense": 78,
            "sp_attack": 109, "sp_defense": 85, "speed": 100}

    visible = {
        "hp": calc_hp(78, 31, 0, 50),
        "attack": calc_stat(84, 31, 0, 50, 0.9),
        "defense": calc_stat(78, 31, 0, 50, 1.0),
        "sp_attack": calc_stat(109, 31, 0, 50, 1.0),
        "sp_defense": calc_stat(85, 31, 0, 50, 1.0),
        "speed": calc_stat(100, 31, 0, 50, 1.1),
    }

    results = estimate_ivs(base, visible, 50, "Timid")

    # All IVs should include 31 in their range
    for stat in STAT_NAMES:
        min_iv, max_iv = results[stat]
        assert min_iv <= 31 <= max_iv, f"{stat}: {min_iv}-{max_iv} does not include 31"


def test_iv_estimation_zero():
    # Charizard Lv50 Hardy, all 0 IVs, 0 EVs
    base = {"hp": 78, "attack": 84, "defense": 78,
            "sp_attack": 109, "sp_defense": 85, "speed": 100}

    visible = {
        "hp": calc_hp(78, 0, 0, 50),
        "attack": calc_stat(84, 0, 0, 50, 1.0),
        "defense": calc_stat(78, 0, 0, 50, 1.0),
        "sp_attack": calc_stat(109, 0, 0, 50, 1.0),
        "sp_defense": calc_stat(85, 0, 0, 50, 1.0),
        "speed": calc_stat(100, 0, 0, 50, 1.0),
    }

    results = estimate_ivs(base, visible, 50, "Hardy")

    for stat in STAT_NAMES:
        min_iv, max_iv = results[stat]
        assert min_iv <= 0 <= max_iv, f"{stat}: {min_iv}-{max_iv} does not include 0"


if __name__ == "__main__":
    test_hp_formula()
    test_stat_formula()
    test_nature_modifiers()
    test_all_natures_defined()
    test_iv_estimation_perfect()
    test_iv_estimation_zero()
    print("All IV calculator tests passed!")
