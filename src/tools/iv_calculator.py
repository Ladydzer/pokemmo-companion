"""IV Calculator — estimate Pokemon IVs from visible stats.

Uses Gen 5 stat formula:
  HP  = ((2*Base + IV + EV/4) * Level / 100) + Level + 10
  Stat = (((2*Base + IV + EV/4) * Level / 100) + 5) * Nature

Where Nature multiplier is 1.1 (beneficial), 0.9 (hindering), or 1.0 (neutral).
"""

# Nature modifiers: {nature_name: (boosted_stat, hindered_stat)}
# None means neutral
NATURES = {
    "Hardy": (None, None), "Lonely": ("attack", "defense"),
    "Brave": ("attack", "speed"), "Adamant": ("attack", "sp_attack"),
    "Naughty": ("attack", "sp_defense"), "Bold": ("defense", "attack"),
    "Docile": (None, None), "Relaxed": ("defense", "speed"),
    "Impish": ("defense", "sp_attack"), "Lax": ("defense", "sp_defense"),
    "Timid": ("speed", "attack"), "Hasty": ("speed", "defense"),
    "Serious": (None, None), "Jolly": ("speed", "sp_attack"),
    "Naive": ("speed", "sp_defense"), "Modest": ("sp_attack", "attack"),
    "Mild": ("sp_attack", "defense"), "Quiet": ("sp_attack", "speed"),
    "Bashful": (None, None), "Rash": ("sp_attack", "sp_defense"),
    "Calm": ("sp_defense", "attack"), "Gentle": ("sp_defense", "defense"),
    "Sassy": ("sp_defense", "speed"), "Careful": ("sp_defense", "sp_attack"),
    "Quirky": (None, None),
}

STAT_NAMES = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]


def get_nature_modifier(nature: str, stat: str) -> float:
    """Get the nature modifier for a specific stat."""
    if nature not in NATURES:
        return 1.0
    boosted, hindered = NATURES[nature]
    if boosted == stat:
        return 1.1
    if hindered == stat:
        return 0.9
    return 1.0


def calc_hp(base: int, iv: int, ev: int, level: int) -> int:
    """Calculate HP stat value."""
    return ((2 * base + iv + ev // 4) * level // 100) + level + 10


def calc_stat(base: int, iv: int, ev: int, level: int, nature_mod: float) -> int:
    """Calculate a non-HP stat value."""
    return int(((2 * base + iv + ev // 4) * level / 100 + 5) * nature_mod)


def estimate_ivs(
    base_stats: dict[str, int],
    visible_stats: dict[str, int],
    level: int,
    nature: str = "Hardy",
    evs: dict[str, int] | None = None,
) -> dict[str, tuple[int, int]]:
    """Estimate IV ranges for each stat.

    Args:
        base_stats: Base stats from Pokedex {stat_name: base_value}
        visible_stats: Visible stats from the game {stat_name: visible_value}
        level: Pokemon level
        nature: Nature name
        evs: Known EVs (default 0 for all)

    Returns:
        Dict of {stat_name: (min_iv, max_iv)} ranges.
    """
    if evs is None:
        evs = {s: 0 for s in STAT_NAMES}

    results = {}

    for stat in STAT_NAMES:
        base = base_stats.get(stat, 0)
        visible = visible_stats.get(stat, 0)
        ev = evs.get(stat, 0)

        possible_ivs = []
        for iv in range(32):  # IVs range 0-31
            if stat == "hp":
                calculated = calc_hp(base, iv, ev, level)
            else:
                nature_mod = get_nature_modifier(nature, stat)
                calculated = calc_stat(base, iv, ev, level, nature_mod)

            if calculated == visible:
                possible_ivs.append(iv)

        if possible_ivs:
            results[stat] = (min(possible_ivs), max(possible_ivs))
        else:
            results[stat] = (0, 31)  # Can't determine

    return results


def format_iv_results(results: dict[str, tuple[int, int]]) -> str:
    """Format IV estimation results for display."""
    lines = []
    for stat in STAT_NAMES:
        min_iv, max_iv = results.get(stat, (0, 31))
        stat_display = {"hp": "HP", "attack": "Atk", "defense": "Def",
                        "sp_attack": "SpA", "sp_defense": "SpD", "speed": "Spe"}
        name = stat_display.get(stat, stat)

        if min_iv == max_iv:
            quality = _iv_quality(min_iv)
            lines.append(f"{name:3}: {min_iv:2} {quality}")
        else:
            lines.append(f"{name:3}: {min_iv}-{max_iv}")

    return "\n".join(lines)


def _iv_quality(iv: int) -> str:
    """Get a quality indicator for an IV value."""
    if iv == 31:
        return "PERFECT"
    elif iv >= 28:
        return "Great"
    elif iv >= 20:
        return "Good"
    elif iv >= 10:
        return "OK"
    else:
        return "Low"


if __name__ == "__main__":
    # Test: Level 50 Charizard with known stats
    base = {"hp": 78, "attack": 84, "defense": 78,
            "sp_attack": 109, "sp_defense": 85, "speed": 100}

    # Simulate visible stats for 31 IVs, 0 EVs, Timid nature
    visible = {
        "hp": calc_hp(78, 31, 0, 50),
        "attack": calc_stat(84, 31, 0, 50, 0.9),   # Timid: -Atk
        "defense": calc_stat(78, 31, 0, 50, 1.0),
        "sp_attack": calc_stat(109, 31, 0, 50, 1.0),
        "sp_defense": calc_stat(85, 31, 0, 50, 1.0),
        "speed": calc_stat(100, 31, 0, 50, 1.1),    # Timid: +Spe
    }

    print("=== Charizard Lv.50 Timid (all 31 IVs, 0 EVs) ===")
    print(f"Visible stats: {visible}")
    results = estimate_ivs(base, visible, 50, "Timid")
    print(format_iv_results(results))
