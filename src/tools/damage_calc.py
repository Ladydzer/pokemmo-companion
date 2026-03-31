"""Damage calculator — Gen 5 damage formula.

Formula:
  Damage = ((2*Level/5 + 2) * Power * A/D) / 50 + 2) * Modifier

Modifier = STAB * Type * Critical * Random * Other

This gives a damage RANGE (min-max) as percentage of defender's HP.
"""
from ..utils.constants import TYPE_CHART


def get_type_effectiveness(atk_type: str, def_types: list[str]) -> float:
    """Calculate type effectiveness multiplier."""
    mult = 1.0
    for dt in def_types:
        mult *= TYPE_CHART.get((atk_type, dt), 1.0)
    return mult


def calc_damage(
    attacker_level: int,
    move_power: int,
    move_type: str,
    attack_stat: int,
    defense_stat: int,
    defender_hp: int,
    defender_types: list[str],
    attacker_types: list[str] | None = None,
    is_critical: bool = False,
    is_stab: bool | None = None,
) -> dict:
    """Calculate damage range as HP values and percentages.

    Args:
        attacker_level: Attacker's level
        move_power: Move's base power
        move_type: Move's type (e.g., "Fire")
        attack_stat: Relevant attack stat (Atk for physical, SpA for special)
        defense_stat: Relevant defense stat (Def for physical, SpD for special)
        defender_hp: Defender's max HP
        defender_types: Defender's types
        attacker_types: Attacker's types (for STAB calculation)
        is_critical: Whether it's a critical hit (1.5x in Gen 5)
        is_stab: Override STAB detection (auto-detected from types if None)

    Returns:
        {"min_damage": int, "max_damage": int,
         "min_pct": float, "max_pct": float,
         "type_mult": float, "is_stab": bool, "ohko": bool}
    """
    if move_power <= 0 or attack_stat <= 0 or defense_stat <= 0:
        return {"min_damage": 0, "max_damage": 0, "min_pct": 0, "max_pct": 0,
                "type_mult": 1.0, "is_stab": False, "ohko": False}

    # Base damage
    base = ((2 * attacker_level / 5 + 2) * move_power * attack_stat / defense_stat) / 50 + 2

    # Type effectiveness
    type_mult = get_type_effectiveness(move_type, defender_types)

    # STAB (Same Type Attack Bonus)
    if is_stab is None:
        is_stab = attacker_types is not None and move_type in attacker_types
    stab = 1.5 if is_stab else 1.0

    # Critical hit
    crit = 1.5 if is_critical else 1.0

    # Random factor (0.85 to 1.00 in Gen 5)
    modifier_base = type_mult * stab * crit

    min_damage = int(base * modifier_base * 0.85)
    max_damage = int(base * modifier_base * 1.00)

    # Ensure minimum 1 damage (unless immune)
    if type_mult == 0:
        min_damage = 0
        max_damage = 0
    else:
        min_damage = max(1, min_damage)
        max_damage = max(1, max_damage)

    min_pct = (min_damage / defender_hp * 100) if defender_hp > 0 else 0
    max_pct = (max_damage / defender_hp * 100) if defender_hp > 0 else 0

    return {
        "min_damage": min_damage,
        "max_damage": max_damage,
        "min_pct": round(min_pct, 1),
        "max_pct": round(max_pct, 1),
        "type_mult": type_mult,
        "is_stab": is_stab,
        "ohko": max_pct >= 100,
    }


def format_damage_result(result: dict) -> str:
    """Format damage result for display."""
    if result["type_mult"] == 0:
        return "IMMUNE (0 damage)"

    lines = []

    # Damage range
    lines.append(f"{result['min_damage']}-{result['max_damage']} HP "
                 f"({result['min_pct']:.1f}%-{result['max_pct']:.1f}%)")

    # Effectiveness
    mult = result["type_mult"]
    if mult >= 4:
        lines.append("SUPER EFFECTIVE (x4)")
    elif mult >= 2:
        lines.append("Super effective (x2)")
    elif mult <= 0.25:
        lines.append("Not very effective (x0.25)")
    elif mult <= 0.5:
        lines.append("Not very effective (x0.5)")

    if result["is_stab"]:
        lines.append("STAB (x1.5)")

    if result["ohko"]:
        lines.append("*** OHKO POSSIBLE ***")
    elif result["max_pct"] >= 50:
        lines.append("2HKO likely")
    elif result["max_pct"] >= 33:
        lines.append("3HKO likely")

    return "\n".join(lines)


if __name__ == "__main__":
    # Charizard (Lv50, SpA 129) using Flamethrower (90 power, Fire)
    # vs Ferrothorn (Grass/Steel, SpD 116, HP 181)
    result = calc_damage(
        attacker_level=50,
        move_power=90,
        move_type="Fire",
        attack_stat=129,
        defense_stat=116,
        defender_hp=181,
        defender_types=["Grass", "Steel"],
        attacker_types=["Fire", "Flying"],
    )
    print("Charizard Flamethrower vs Ferrothorn:")
    print(format_damage_result(result))
    print()

    # Geodude Earthquake vs Pikachu
    result = calc_damage(
        attacker_level=25,
        move_power=100,
        move_type="Ground",
        attack_stat=80,
        defense_stat=30,
        defender_hp=55,
        defender_types=["Electric"],
        attacker_types=["Rock", "Ground"],
    )
    print("Geodude Earthquake vs Pikachu:")
    print(format_damage_result(result))
