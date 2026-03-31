"""Tests for the damage calculator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.damage_calc import calc_damage, get_type_effectiveness


def test_basic_damage():
    r = calc_damage(50, 80, "Normal", 100, 100, 200, ["Normal"])
    assert r["min_damage"] > 0
    assert r["max_damage"] >= r["min_damage"]
    assert r["type_mult"] == 1.0


def test_super_effective():
    r = calc_damage(50, 80, "Water", 100, 100, 200, ["Fire"])
    assert r["type_mult"] == 2.0
    assert r["max_damage"] > calc_damage(50, 80, "Normal", 100, 100, 200, ["Fire"])["max_damage"]


def test_quad_effective():
    r = calc_damage(50, 90, "Fire", 129, 116, 181, ["Grass", "Steel"])
    assert r["type_mult"] == 4.0
    assert r["ohko"]  # Should OHKO


def test_immune():
    r = calc_damage(50, 80, "Normal", 100, 100, 200, ["Ghost"])
    assert r["type_mult"] == 0.0
    assert r["min_damage"] == 0
    assert r["max_damage"] == 0


def test_stab():
    # With STAB
    r_stab = calc_damage(50, 80, "Fire", 100, 100, 200, ["Normal"], ["Fire"])
    # Without STAB
    r_no = calc_damage(50, 80, "Fire", 100, 100, 200, ["Normal"], ["Water"])
    assert r_stab["is_stab"]
    assert not r_no["is_stab"]
    assert r_stab["max_damage"] > r_no["max_damage"]


def test_type_effectiveness():
    assert get_type_effectiveness("Fire", ["Grass"]) == 2.0
    assert get_type_effectiveness("Fire", ["Water"]) == 0.5
    assert get_type_effectiveness("Electric", ["Ground"]) == 0.0
    assert get_type_effectiveness("Water", ["Rock", "Ground"]) == 4.0


def test_zero_power():
    r = calc_damage(50, 0, "Normal", 100, 100, 200, ["Normal"])
    assert r["min_damage"] == 0


if __name__ == "__main__":
    test_basic_damage()
    test_super_effective()
    test_quad_effective()
    test_immune()
    test_stab()
    test_type_effectiveness()
    test_zero_power()
    print("All damage calc tests passed!")
