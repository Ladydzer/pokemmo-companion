"""Breeding Assistant — IV inheritance, egg moves, and breeding chains.

PokeMMO breeding mechanics (Gen 5 based):
- 2 parents required (same egg group or Ditto)
- Random 3 IVs inherited from parents (or more with Destiny Knot: 5 IVs)
- Everstone: 100% nature inheritance from holder
- Egg moves: father passes egg moves to offspring
- Gender ratio follows species defaults
- No Masuda Method in PokeMMO
"""

# Egg groups for common Pokemon (subset — full data in database)
EGG_GROUPS = {
    "Monster": ["Bulbasaur", "Charmander", "Squirtle", "Totodile", "Treecko",
                "Mudkip", "Turtwig", "Chimchar", "Snivy", "Tepig", "Oshawott"],
    "Water 1": ["Squirtle", "Psyduck", "Slowpoke", "Seel", "Horsea",
                "Lapras", "Totodile", "Marill", "Mudkip", "Piplup", "Oshawott"],
    "Field": ["Rattata", "Pikachu", "Vulpix", "Growlithe", "Ponyta",
              "Eevee", "Cyndaquil", "Torchic", "Shinx", "Tepig", "Lillipup"],
    "Human-Like": ["Abra", "Machop", "Mr. Mime", "Jynx", "Electabuzz",
                   "Magmar", "Ralts", "Makuhita", "Lucario", "Throh", "Sawk"],
    "Bug": ["Caterpie", "Weedle", "Paras", "Venonat", "Scyther",
            "Pinsir", "Heracross", "Volbeat", "Illumise", "Sewaddle", "Joltik"],
    "Flying": ["Pidgey", "Spearow", "Zubat", "Farfetch'd", "Doduo",
               "Hoothoot", "Murkrow", "Taillow", "Wingull", "Starly", "Pidove"],
    "Ditto": ["Ditto"],
}


def get_breeding_cost_estimate(target_ivs: int) -> dict:
    """Estimate the breeding cost for a Pokemon with N perfect IVs.

    In PokeMMO, breeding costs increase exponentially:
    - Each breeding attempt costs a fee
    - More perfect IVs = more parent Pokemon needed = more expensive
    - Destiny Knot is essential for 5IV+ breeds

    Args:
        target_ivs: Number of perfect (31) IVs desired (1-6)

    Returns:
        Dict with estimated cost, parents needed, and breeding steps.
    """
    costs = {
        1: {"parents": 2, "steps": 1, "cost_min": 5000, "cost_max": 15000,
            "tip": "Just catch 2 Pokemon with the right IV and breed"},
        2: {"parents": 4, "steps": 3, "cost_min": 30000, "cost_max": 80000,
            "tip": "Need parents covering 2 stats. Destiny Knot recommended"},
        3: {"parents": 8, "steps": 7, "cost_min": 100000, "cost_max": 250000,
            "tip": "Use Destiny Knot + Everstone. Plan your breeding tree"},
        4: {"parents": 16, "steps": 15, "cost_min": 300000, "cost_max": 600000,
            "tip": "Buy breeders from GTL. Destiny Knot is mandatory"},
        5: {"parents": 32, "steps": 31, "cost_min": 800000, "cost_max": 1500000,
            "tip": "Very expensive! Consider buying a 5IV from GTL instead"},
        6: {"parents": 64, "steps": 63, "cost_min": 3000000, "cost_max": 8000000,
            "tip": "Extremely rare and expensive. 6IV is usually overkill"},
    }

    return costs.get(target_ivs, costs[1])


def check_egg_compatibility(pokemon1_groups: list[str],
                            pokemon2_groups: list[str]) -> bool:
    """Check if two Pokemon can breed based on egg groups.

    Returns True if they share at least one egg group, or if one is Ditto.
    """
    if "Ditto" in pokemon1_groups or "Ditto" in pokemon2_groups:
        return True
    return bool(set(pokemon1_groups) & set(pokemon2_groups))


def format_breeding_plan(target_pokemon: str, target_ivs: int,
                         target_nature: str = "") -> str:
    """Format a breeding plan for display."""
    cost = get_breeding_cost_estimate(target_ivs)

    lines = [
        f"Breeding Plan: {target_pokemon}",
        f"Target: {target_ivs}x31 IVs" + (f" {target_nature} nature" if target_nature else ""),
        f"",
        f"Parents needed: ~{cost['parents']}",
        f"Breeding steps: ~{cost['steps']}",
        f"Est. cost: {cost['cost_min']//1000}k - {cost['cost_max']//1000}k PY",
        f"",
        f"Items needed:",
        f"  - Destiny Knot (inherits 5 IVs)",
    ]

    if target_nature:
        lines.append(f"  - Everstone (100% nature inheritance)")

    lines.append(f"")
    lines.append(f"Tip: {cost['tip']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== Breeding Cost Estimates ===\n")
    for ivs in range(1, 7):
        cost = get_breeding_cost_estimate(ivs)
        print(f"{ivs}x31 IVs: ~{cost['parents']} parents, "
              f"{cost['cost_min']//1000}k-{cost['cost_max']//1000}k PY, "
              f"~{cost['steps']} steps")

    print()
    print(format_breeding_plan("Garchomp", 5, "Jolly"))
