"""Type effectiveness calculator for Gen 5 mechanics."""
from ..utils.constants import TYPES, TYPE_CHART


def get_effectiveness(attack_type: str, defend_type: str) -> float:
    """Get effectiveness multiplier for attack_type vs defend_type."""
    return TYPE_CHART.get((attack_type, defend_type), 1.0)


def get_dual_effectiveness(attack_type: str, defend_types: list[str]) -> float:
    """Get effectiveness multiplier for attack_type vs dual-typed defender."""
    result = 1.0
    for dt in defend_types:
        result *= get_effectiveness(attack_type, dt)
    return result


def get_weaknesses(defend_types: list[str]) -> dict[str, float]:
    """Get all types that are super effective against the given type(s).

    Returns dict of {type: multiplier} for multipliers > 1.0.
    """
    result = {}
    for atk_type in TYPES:
        mult = get_dual_effectiveness(atk_type, defend_types)
        if mult > 1.0:
            result[atk_type] = mult
    return dict(sorted(result.items(), key=lambda x: -x[1]))


def get_resistances(defend_types: list[str]) -> dict[str, float]:
    """Get all types that are resisted by the given type(s).

    Returns dict of {type: multiplier} for multipliers < 1.0 and > 0.
    """
    result = {}
    for atk_type in TYPES:
        mult = get_dual_effectiveness(atk_type, defend_types)
        if 0 < mult < 1.0:
            result[atk_type] = mult
    return dict(sorted(result.items(), key=lambda x: x[1]))


def get_immunities(defend_types: list[str]) -> list[str]:
    """Get all types that the given type(s) are immune to."""
    result = []
    for atk_type in TYPES:
        mult = get_dual_effectiveness(atk_type, defend_types)
        if mult == 0.0:
            result.append(atk_type)
    return result


def get_battle_summary(defend_types: list[str]) -> dict:
    """Get complete battle info for a Pokemon's defensive types.

    Returns:
        {
            "types": ["Fire", "Steel"],
            "weak_to": {"Ground": 4.0, "Water": 2.0, "Fighting": 2.0},
            "resists": {"Bug": 0.25, "Grass": 0.25, ...},
            "immune_to": ["Poison"],
        }
    """
    return {
        "types": defend_types,
        "weak_to": get_weaknesses(defend_types),
        "resists": get_resistances(defend_types),
        "immune_to": get_immunities(defend_types),
    }


def format_battle_summary(summary: dict) -> str:
    """Format battle summary for display in overlay."""
    lines = []
    types_str = "/".join(summary["types"])
    lines.append(f"Type: {types_str}")

    if summary["weak_to"]:
        weak_parts = []
        for t, m in summary["weak_to"].items():
            weak_parts.append(f"{t} x{m:g}")
        lines.append(f"WEAK: {', '.join(weak_parts)}")

    if summary["immune_to"]:
        lines.append(f"IMMUNE: {', '.join(summary['immune_to'])}")

    if summary["resists"]:
        resist_parts = []
        for t, m in summary["resists"].items():
            resist_parts.append(f"{t} x{m:g}")
        lines.append(f"RESIST: {', '.join(resist_parts)}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test: Geodude (Rock/Ground) — should be x4 weak to Water and Grass
    print("=== Geodude (Rock/Ground) ===")
    summary = get_battle_summary(["Rock", "Ground"])
    print(format_battle_summary(summary))
    print()

    # Test: Charizard (Fire/Flying)
    print("=== Charizard (Fire/Flying) ===")
    summary = get_battle_summary(["Fire", "Flying"])
    print(format_battle_summary(summary))
    print()

    # Test: Gengar (Ghost/Poison)
    print("=== Gengar (Ghost/Poison) ===")
    summary = get_battle_summary(["Ghost", "Poison"])
    print(format_battle_summary(summary))
