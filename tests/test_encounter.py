"""Tests for encounter counter and shiny probability."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.widgets.encounter_counter import cumulative_shiny_probability, EncounterData


def test_shiny_probability_zero():
    assert cumulative_shiny_probability(0, 1/30000) == 0.0
    assert cumulative_shiny_probability(-1, 1/30000) == 0.0
    assert cumulative_shiny_probability(100, 0) == 0.0


def test_shiny_probability_base_rate():
    rate = 1/30000
    # At 30,000 encounters: ~63.2% (1 - 1/e)
    prob = cumulative_shiny_probability(30000, rate)
    assert 0.63 < prob < 0.64

    # At 100 encounters: very low
    prob = cumulative_shiny_probability(100, rate)
    assert prob < 0.01

    # At 100,000 encounters: very high
    prob = cumulative_shiny_probability(100000, rate)
    assert prob > 0.95


def test_shiny_probability_donator():
    rate = 1/27000
    prob = cumulative_shiny_probability(27000, rate)
    assert 0.63 < prob < 0.64


def test_horde_multiplier():
    rate = 1/30000
    # 1000 hordes = 5000 encounters
    prob_horde = cumulative_shiny_probability(5000, rate)
    prob_single = cumulative_shiny_probability(1000, rate)
    # Horde should give much better odds
    assert prob_horde > prob_single * 3


def test_encounter_data_defaults():
    data = EncounterData()
    assert data.total_encounters == 0
    assert data.shinies_found == 0
    assert data.shiny_rate == 1/30000
    assert data.current_session.encounters == 0


def test_encounter_session_tracking():
    data = EncounterData()
    data.current_session.encounters = 500
    data.current_session.hordes = 100
    data.total_encounters = 5000
    data.shinies_found = 0

    assert data.current_session.encounters == 500
    assert data.total_encounters == 5000


if __name__ == "__main__":
    test_shiny_probability_zero()
    test_shiny_probability_base_rate()
    test_shiny_probability_donator()
    test_horde_multiplier()
    test_encounter_data_defaults()
    test_encounter_session_tracking()
    print("All encounter tests passed!")
