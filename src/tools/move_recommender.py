"""Move Recommender — suggests optimal 4-move sets for PvE.

Recommends moves based on:
1. STAB coverage (Same Type Attack Bonus)
2. Type coverage (hit as many types super-effectively as possible)
3. Move power + accuracy
4. Utility moves (status, recovery)
"""
from ..utils.constants import TYPES, TYPE_CHART


# Common strong moves by type (Gen 5 movepools, available in PokeMMO)
# Format: {type: [(move_name, power, accuracy, category, priority_score)]}
STRONG_MOVES = {
    "Normal": [("Return", 102, 100, "physical", 8), ("Hyper Voice", 90, 100, "special", 7),
               ("Body Slam", 85, 100, "physical", 7), ("Facade", 70, 100, "physical", 6)],
    "Fire": [("Flamethrower", 90, 100, "special", 9), ("Fire Blast", 110, 85, "special", 8),
             ("Flare Blitz", 120, 100, "physical", 9), ("Fire Punch", 75, 100, "physical", 7)],
    "Water": [("Surf", 90, 100, "special", 9), ("Hydro Pump", 110, 80, "special", 8),
              ("Waterfall", 80, 100, "physical", 8), ("Scald", 80, 100, "special", 9)],
    "Electric": [("Thunderbolt", 90, 100, "special", 9), ("Thunder", 110, 70, "special", 7),
                 ("Wild Charge", 90, 100, "physical", 8), ("Volt Switch", 70, 100, "special", 8)],
    "Grass": [("Energy Ball", 90, 100, "special", 8), ("Giga Drain", 75, 100, "special", 9),
              ("Leaf Blade", 90, 100, "physical", 9), ("Seed Bomb", 80, 100, "physical", 7)],
    "Ice": [("Ice Beam", 90, 100, "special", 9), ("Blizzard", 110, 70, "special", 7),
            ("Ice Punch", 75, 100, "physical", 7), ("Icicle Crash", 85, 90, "physical", 7)],
    "Fighting": [("Close Combat", 120, 100, "physical", 9), ("Aura Sphere", 80, 0, "special", 8),
                 ("Brick Break", 75, 100, "physical", 7), ("Drain Punch", 75, 100, "physical", 8)],
    "Poison": [("Sludge Bomb", 90, 100, "special", 8), ("Poison Jab", 80, 100, "physical", 7),
               ("Sludge Wave", 95, 100, "special", 7)],
    "Ground": [("Earthquake", 100, 100, "physical", 10), ("Earth Power", 90, 100, "special", 8),
               ("Dig", 80, 100, "physical", 5)],
    "Flying": [("Brave Bird", 120, 100, "physical", 8), ("Air Slash", 75, 95, "special", 7),
               ("Hurricane", 110, 70, "special", 7), ("Acrobatics", 55, 100, "physical", 6)],
    "Psychic": [("Psychic", 90, 100, "special", 9), ("Psyshock", 80, 100, "special", 8),
                ("Zen Headbutt", 80, 90, "physical", 7)],
    "Bug": [("X-Scissor", 80, 100, "physical", 7), ("Bug Buzz", 90, 100, "special", 8),
            ("U-turn", 70, 100, "physical", 8)],
    "Rock": [("Stone Edge", 100, 80, "physical", 8), ("Rock Slide", 75, 90, "physical", 8),
             ("Power Gem", 80, 100, "special", 7)],
    "Ghost": [("Shadow Ball", 80, 100, "special", 9), ("Shadow Claw", 70, 100, "physical", 7),
              ("Phantom Force", 90, 100, "physical", 6)],
    "Dragon": [("Dragon Claw", 80, 100, "physical", 8), ("Dragon Pulse", 85, 100, "special", 8),
               ("Draco Meteor", 130, 90, "special", 8), ("Outrage", 120, 100, "physical", 8)],
    "Dark": [("Dark Pulse", 80, 100, "special", 8), ("Crunch", 80, 100, "physical", 8),
             ("Knock Off", 65, 100, "physical", 9), ("Sucker Punch", 80, 100, "physical", 7)],
    "Steel": [("Iron Head", 80, 100, "physical", 8), ("Flash Cannon", 80, 100, "special", 8),
              ("Meteor Mash", 90, 90, "physical", 7)],
}

# Utility moves that are generally useful in PvE
UTILITY_MOVES = [
    ("Toxic", "Poison", "status", 8, "Poisons target, useful for tanky enemies"),
    ("Protect", "Normal", "status", 6, "Scouting + stalling"),
    ("Substitute", "Normal", "status", 7, "Protection from status moves"),
    ("Swords Dance", "Normal", "status", 8, "Doubles Attack for sweeping"),
    ("Calm Mind", "Psychic", "status", 8, "Boosts SpA + SpD"),
    ("Dragon Dance", "Dragon", "status", 9, "Boosts Atk + Spe — amazing for sweepers"),
    ("Stealth Rock", "Rock", "status", 8, "Entry hazard, great for PvP"),
    ("Roost", "Flying", "status", 8, "Reliable recovery"),
    ("Recover", "Normal", "status", 8, "Reliable recovery"),
    ("Wish", "Normal", "status", 7, "Delayed healing, good for support"),
]


def recommend_moves(pokemon_types: list[str], attack: int, sp_attack: int,
                    speed: int) -> list[dict]:
    """Recommend a 4-move PvE set for a Pokemon.

    Strategy:
    1. Two STAB moves (one for each type, if dual-typed)
    2. One coverage move (hits types that STAB doesn't cover)
    3. One utility or additional coverage move

    Returns list of recommended moves with reasoning.
    """
    is_physical = attack >= sp_attack
    preferred_cat = "physical" if is_physical else "special"

    recommendations = []

    # Step 1: STAB moves (one per type)
    for ptype in pokemon_types:
        moves = STRONG_MOVES.get(ptype, [])
        # Prefer moves matching the Pokemon's best attacking stat
        best = None
        for name, power, acc, cat, score in moves:
            if cat == preferred_cat or cat == "special" and not is_physical:
                if best is None or score > best[4]:
                    best = (name, power, acc, cat, score)
        if not best and moves:
            best = max(moves, key=lambda m: m[4])
        if best:
            recommendations.append({
                "move": best[0],
                "type": ptype,
                "power": best[1],
                "accuracy": best[2],
                "category": best[3],
                "reason": f"STAB {ptype} — {best[1]} power",
            })

    # Step 2: Coverage move — find types not covered by STAB
    stab_coverage = set()
    for ptype in pokemon_types:
        for def_type in TYPES:
            if TYPE_CHART.get((ptype, def_type), 1.0) > 1.0:
                stab_coverage.add(def_type)

    uncovered = set(TYPES) - stab_coverage
    # Find the best coverage type
    best_coverage = None
    best_coverage_count = 0
    for cov_type in TYPES:
        if cov_type in pokemon_types:
            continue
        hits = sum(1 for t in uncovered if TYPE_CHART.get((cov_type, t), 1.0) > 1.0)
        if hits > best_coverage_count:
            best_coverage_count = hits
            best_coverage = cov_type

    if best_coverage:
        moves = STRONG_MOVES.get(best_coverage, [])
        best = None
        for name, power, acc, cat, score in moves:
            if cat == preferred_cat:
                if best is None or score > best[4]:
                    best = (name, power, acc, cat, score)
        if not best and moves:
            best = max(moves, key=lambda m: m[4])
        if best:
            recommendations.append({
                "move": best[0],
                "type": best_coverage,
                "power": best[1],
                "accuracy": best[2],
                "category": best[3],
                "reason": f"Coverage — hits {best_coverage_count} uncovered types",
            })

    # Step 3: Second coverage or utility
    if len(recommendations) < 4:
        # Try another coverage type
        remaining = set(TYPES) - stab_coverage - {best_coverage}
        second_cov = None
        second_count = 0
        for cov_type in TYPES:
            if cov_type in pokemon_types or cov_type == best_coverage:
                continue
            hits = sum(1 for t in remaining if TYPE_CHART.get((cov_type, t), 1.0) > 1.0)
            if hits > second_count:
                second_count = hits
                second_cov = cov_type

        if second_cov and second_count > 0:
            moves = STRONG_MOVES.get(second_cov, [])
            best = None
            for name, power, acc, cat, score in moves:
                if cat == preferred_cat:
                    if best is None or score > best[4]:
                        best = (name, power, acc, cat, score)
            if not best and moves:
                best = max(moves, key=lambda m: m[4])
            if best:
                recommendations.append({
                    "move": best[0],
                    "type": second_cov,
                    "power": best[1],
                    "accuracy": best[2],
                    "category": best[3],
                    "reason": f"Coverage — hits {second_count} more types",
                })

    # Fill remaining slots with utility
    while len(recommendations) < 4:
        for name, mtype, cat, score, desc in UTILITY_MOVES:
            already = {r["move"] for r in recommendations}
            if name not in already:
                recommendations.append({
                    "move": name,
                    "type": mtype,
                    "power": 0,
                    "accuracy": 0,
                    "category": cat,
                    "reason": desc,
                })
                break
        else:
            break

    return recommendations[:4]


def format_recommendations(recs: list[dict]) -> str:
    """Format move recommendations for display."""
    lines = []
    for i, r in enumerate(recs, 1):
        power_str = f"{r['power']} pwr" if r['power'] > 0 else "status"
        lines.append(f"{i}. {r['move']} ({r['type']}, {power_str})")
        lines.append(f"   {r['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Charizard (Fire/Flying, SpA 109 > Atk 84)
    print("=== Charizard (Fire/Flying, Special) ===")
    recs = recommend_moves(["Fire", "Flying"], 84, 109, 100)
    print(format_recommendations(recs))
    print()

    # Garchomp (Dragon/Ground, Atk 130 > SpA 80)
    print("=== Garchomp (Dragon/Ground, Physical) ===")
    recs = recommend_moves(["Dragon", "Ground"], 130, 80, 102)
    print(format_recommendations(recs))
