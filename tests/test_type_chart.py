"""Tests for the type effectiveness calculator."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.type_chart import (
    get_effectiveness, get_dual_effectiveness,
    get_weaknesses, get_resistances, get_immunities,
    get_battle_summary, format_battle_summary,
)


def test_basic_effectiveness():
    """Test single-type effectiveness."""
    assert get_effectiveness("Fire", "Grass") == 2.0
    assert get_effectiveness("Water", "Fire") == 2.0
    assert get_effectiveness("Electric", "Ground") == 0.0
    assert get_effectiveness("Normal", "Ghost") == 0.0
    assert get_effectiveness("Fire", "Fire") == 0.5
    assert get_effectiveness("Normal", "Normal") == 1.0  # neutral


def test_dual_type_effectiveness():
    """Test dual-type effectiveness calculations."""
    # Fire vs Rock/Ground = 0.5 * 1.0 = 0.5 (Fire is not very effective vs Rock, neutral vs Ground)
    assert get_dual_effectiveness("Fire", ["Rock", "Ground"]) == 0.5

    # Water vs Rock/Ground = 2.0 * 2.0 = 4.0
    assert get_dual_effectiveness("Water", ["Rock", "Ground"]) == 4.0

    # Grass vs Rock/Ground = 2.0 * 2.0 = 4.0
    assert get_dual_effectiveness("Grass", ["Rock", "Ground"]) == 4.0

    # Electric vs Water/Flying = 2.0 * 2.0 = 4.0
    assert get_dual_effectiveness("Electric", ["Water", "Flying"]) == 4.0

    # Ground vs Fire/Flying = 2.0 * 0.0 = 0.0
    assert get_dual_effectiveness("Ground", ["Fire", "Flying"]) == 0.0


def test_weaknesses():
    """Test weakness detection."""
    # Pure Fire type
    weaknesses = get_weaknesses(["Fire"])
    assert "Water" in weaknesses
    assert "Ground" in weaknesses
    assert "Rock" in weaknesses
    assert weaknesses["Water"] == 2.0

    # Rock/Ground (Geodude) — 4x weak to Water and Grass
    weaknesses = get_weaknesses(["Rock", "Ground"])
    assert weaknesses.get("Water") == 4.0
    assert weaknesses.get("Grass") == 4.0


def test_immunities():
    """Test immunity detection."""
    # Ghost type immune to Normal and Fighting
    immunities = get_immunities(["Ghost"])
    assert "Normal" in immunities
    assert "Fighting" in immunities

    # Ground immune to Electric
    immunities = get_immunities(["Ground"])
    assert "Electric" in immunities


def test_resistances():
    """Test resistance detection."""
    # Steel type resists many things
    resistances = get_resistances(["Steel"])
    assert "Normal" in resistances
    assert "Grass" in resistances
    assert "Ice" in resistances


def test_battle_summary():
    """Test complete battle summary."""
    summary = get_battle_summary(["Fire", "Flying"])
    assert summary["types"] == ["Fire", "Flying"]
    assert "Rock" in summary["weak_to"]
    assert summary["weak_to"]["Rock"] == 4.0  # 4x weak
    assert "Water" in summary["weak_to"]
    assert "Electric" in summary["weak_to"]
    assert "Ground" in summary["immune_to"]
    assert "Grass" in summary["resists"]
    assert "Bug" in summary["resists"]


def test_format_battle_summary():
    """Test formatted output."""
    summary = get_battle_summary(["Ghost", "Poison"])
    text = format_battle_summary(summary)
    assert "Ghost/Poison" in text
    assert "WEAK" in text
    assert "IMMUNE" in text or "RESIST" in text


def test_all_gen5_types_exist():
    """Verify all 17 Gen 5 types are in the chart."""
    from src.utils.constants import TYPES
    assert len(TYPES) == 17
    assert "Fairy" not in TYPES  # No Fairy in Gen 5


if __name__ == "__main__":
    test_basic_effectiveness()
    test_dual_type_effectiveness()
    test_weaknesses()
    test_immunities()
    test_resistances()
    test_battle_summary()
    test_format_battle_summary()
    test_all_gen5_types_exist()
    print("All type chart tests passed!")
