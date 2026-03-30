"""EV Training Guide — best spots per stat per region.

Each Pokemon gives specific EVs when defeated. This module provides
the best training spots for each stat in each region.
"""

# Best EV training spots by stat and region
# Format: {stat: {region: [(pokemon, ev_yield, location, method, notes)]}}
EV_SPOTS = {
    "hp": {
        "Kanto": [
            ("Dunsparce", 1, "Dark Cave (Johto side)", "walking", "100% encounter rate"),
            ("Caterpie", 1, "Viridian Forest", "walking", "Common, low level"),
        ],
        "Johto": [
            ("Dunsparce", 1, "Dark Cave", "walking", "Common"),
            ("Wooper", 1, "Route 32", "surfing", "Easy encounters"),
        ],
        "Hoenn": [
            ("Whismur", 1, "Rusturf Tunnel", "walking", "100% encounter"),
            ("Marill", 2, "Route 117", "walking", "Uncommon but 2 EVs"),
        ],
        "Sinnoh": [
            ("Bidoof", 1, "Route 201", "walking", "Very common"),
            ("Gastrodon", 2, "Route 218", "surfing", "2 EVs each"),
        ],
        "Unova": [
            ("Stunfisk", 2, "Icirrus City", "surfing", "2 EVs each"),
            ("Audino", 2, "Any shaking grass", "walking", "Also gives great EXP"),
        ],
    },
    "attack": {
        "Kanto": [
            ("Geodude", 1, "Mt. Moon", "walking", "Common"),
            ("Mankey", 1, "Route 22", "walking", "Common"),
        ],
        "Johto": [
            ("Goldeen", 1, "Route 35", "fishing_old", "Common"),
            ("Bellsprout", 1, "Route 31", "walking", "Common"),
        ],
        "Hoenn": [
            ("Poochyena", 1, "Route 101", "walking", "Very common"),
            ("Sharpedo", 2, "Route 132", "surfing", "2 EVs each"),
        ],
        "Sinnoh": [
            ("Shinx", 1, "Route 202", "walking", "Very common"),
            ("Bibarel", 2, "Route 208", "surfing", "2 Atk EVs"),
        ],
        "Unova": [
            ("Patrat", 1, "Route 1", "walking", "Very common"),
            ("Lillipup", 1, "Route 1", "walking", "Common"),
        ],
    },
    "defense": {
        "Kanto": [
            ("Geodude", 1, "Rock Tunnel", "walking", "Common"),
            ("Shellder", 1, "Route 6", "fishing_good", "Common"),
        ],
        "Johto": [
            ("Geodude", 1, "Route 46", "walking", "Common"),
            ("Pineco", 1, "Ilex Forest", "headbutt", "Headbutt trees"),
        ],
        "Hoenn": [
            ("Geodude", 1, "Granite Cave", "walking", "Common"),
            ("Sandshrew", 1, "Route 111 (desert)", "walking", "Common"),
        ],
        "Sinnoh": [
            ("Geodude", 1, "Oreburgh Mine", "walking", "Common"),
            ("Onix", 1, "Oreburgh Mine", "walking", "Uncommon"),
        ],
        "Unova": [
            ("Roggenrola", 1, "Wellspring Cave", "walking", "Common"),
            ("Sewaddle", 1, "Pinwheel Forest", "walking", "Common"),
        ],
    },
    "sp_attack": {
        "Kanto": [
            ("Gastly", 1, "Pokemon Tower", "walking", "Very common"),
            ("Oddish", 1, "Route 24", "walking", "Night only"),
        ],
        "Johto": [
            ("Gastly", 1, "Sprout Tower", "walking", "Night"),
            ("Psyduck", 1, "Route 35", "surfing", "Common"),
        ],
        "Hoenn": [
            ("Oddish", 1, "Route 117", "walking", "Night"),
            ("Tentacool", 1, "Any water route", "surfing", "Very common"),
        ],
        "Sinnoh": [
            ("Gastly", 1, "Old Chateau", "walking", "Night"),
            ("Psyduck", 1, "Route 203", "surfing", "Common"),
        ],
        "Unova": [
            ("Litwick", 1, "Celestial Tower", "walking", "Common"),
            ("Elgyem", 1, "Celestial Tower", "walking", "Common"),
        ],
    },
    "sp_defense": {
        "Kanto": [
            ("Tentacool", 1, "Route 19", "surfing", "Very common"),
            ("Tentacruel", 2, "Route 20", "surfing", "2 EVs each"),
        ],
        "Johto": [
            ("Tentacool", 1, "Route 40", "surfing", "Very common"),
            ("Lanturn", 2, "Route 41", "surfing", "2 EVs each"),
        ],
        "Hoenn": [
            ("Tentacool", 1, "Route 107", "surfing", "Very common"),
            ("Lombre", 2, "Route 114", "surfing", "2 EVs each"),
        ],
        "Sinnoh": [
            ("Tentacool", 1, "Route 218", "surfing", "Common"),
            ("Mantyke", 1, "Route 223", "surfing", "Common"),
        ],
        "Unova": [
            ("Frillish", 1, "Route 4", "surfing", "Common"),
            ("Claydol", 2, "Relic Castle", "walking", "2 EVs each"),
        ],
    },
    "speed": {
        "Kanto": [
            ("Diglett", 1, "Diglett's Cave", "walking", "100% encounter"),
            ("Rattata", 1, "Route 1", "walking", "Very common"),
        ],
        "Johto": [
            ("Rattata", 1, "Route 29", "walking", "Very common"),
            ("Zubat", 1, "Any cave", "walking", "Very common"),
        ],
        "Hoenn": [
            ("Zigzagoon", 1, "Route 101", "walking", "Very common"),
            ("Wingull", 1, "Route 103", "walking", "Common"),
        ],
        "Sinnoh": [
            ("Starly", 1, "Route 201", "walking", "Very common"),
            ("Zubat", 1, "Oreburgh Gate", "walking", "Common"),
        ],
        "Unova": [
            ("Basculin", 2, "Route 1", "surfing", "2 Speed EVs!"),
            ("Joltik", 1, "Chargestone Cave", "walking", "Common"),
        ],
    },
}

# Power items double EV gain from that stat
POWER_ITEMS = {
    "hp": "Power Weight",
    "attack": "Power Bracer",
    "defense": "Power Belt",
    "sp_attack": "Power Lens",
    "sp_defense": "Power Band",
    "speed": "Power Anklet",
}


def get_ev_spots(stat: str, region: str | None = None) -> list[dict]:
    """Get EV training spots for a given stat.

    Args:
        stat: One of hp, attack, defense, sp_attack, sp_defense, speed
        region: Optional region filter

    Returns:
        List of dicts with pokemon, ev_yield, location, method, notes
    """
    stat_data = EV_SPOTS.get(stat, {})
    results = []

    regions = [region] if region else stat_data.keys()
    for r in regions:
        spots = stat_data.get(r, [])
        for pokemon, ev_yield, location, method, notes in spots:
            results.append({
                "pokemon": pokemon,
                "ev_yield": ev_yield,
                "location": location,
                "region": r,
                "method": method,
                "notes": notes,
            })

    return results


def calc_evs_needed(current: int, target: int = 252) -> int:
    """Calculate EVs still needed to reach target."""
    return max(0, target - current)


def calc_battles_needed(evs_needed: int, ev_per_battle: int = 1,
                        has_pokerus: bool = False,
                        has_power_item: bool = False,
                        has_macho_brace: bool = False) -> int:
    """Calculate number of battles needed to get required EVs.

    Modifiers stack:
    - Pokerus: 2x
    - Power Item: +4 EVs per battle (before Pokerus)
    - Macho Brace: 2x (doesn't stack with Power Item)
    """
    ev_per = ev_per_battle
    if has_power_item:
        ev_per += 4
    elif has_macho_brace:
        ev_per *= 2
    if has_pokerus:
        ev_per *= 2

    if ev_per <= 0:
        return 0
    return -(-evs_needed // ev_per)  # Ceiling division


def format_ev_plan(stat: str, region: str, target: int = 252,
                   current: int = 0, has_pokerus: bool = False) -> str:
    """Format an EV training plan for display."""
    needed = calc_evs_needed(current, target)
    if needed == 0:
        return f"{stat.upper()}: Already at {target} EVs!"

    spots = get_ev_spots(stat, region)
    if not spots:
        return f"{stat.upper()}: No spots found for {region}"

    best = spots[0]
    power_item = POWER_ITEMS.get(stat, "Power Item")

    battles_base = calc_battles_needed(needed, best["ev_yield"])
    battles_power = calc_battles_needed(needed, best["ev_yield"], has_power_item=True)
    battles_full = calc_battles_needed(needed, best["ev_yield"],
                                       has_pokerus=True, has_power_item=True)

    lines = [
        f"{stat.upper()}: {current}/{target} ({needed} needed)",
        f"Best spot: {best['pokemon']} ({best['location']})",
        f"  Base: ~{battles_base} battles",
        f"  +{power_item}: ~{battles_power} battles",
        f"  +{power_item}+Pokerus: ~{battles_full} battles",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== EV Training Guide ===\n")

    for stat in ["speed", "attack", "sp_attack"]:
        print(format_ev_plan(stat, "Kanto", target=252))
        print()

    print("=== Speed spots (all regions) ===")
    for spot in get_ev_spots("speed"):
        print(f"  {spot['pokemon']:12} +{spot['ev_yield']} Spe  {spot['location']:20} ({spot['region']})")
