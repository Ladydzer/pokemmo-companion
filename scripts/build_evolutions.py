"""Build evolution chain data from PokeAPI.

Fetches evolution chains and populates the evolutions table.

Usage:
    python scripts/build_evolutions.py
"""
import json
import sqlite3
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "pokemon.db"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "evolutions"
POKEAPI = "https://pokeapi.co/api/v2"


def fetch_json(url: str, cache_file: Path | None = None) -> dict:
    if cache_file and cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(data, f)
    return data


def get_pokemon_id(name: str, conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM pokemon WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
    return row[0] if row else None


def parse_chain(chain: dict, conn: sqlite3.Connection) -> list[tuple]:
    """Recursively parse an evolution chain into (from_id, to_id, method, condition) tuples."""
    results = []
    species_name = chain["species"]["name"].capitalize()
    from_id = get_pokemon_id(species_name, conn)

    for evo in chain.get("evolves_to", []):
        to_name = evo["species"]["name"].capitalize()
        to_id = get_pokemon_id(to_name, conn)

        if from_id and to_id:
            # Parse evolution details
            details = evo.get("evolution_details", [{}])
            detail = details[0] if details else {}

            trigger = detail.get("trigger", {}).get("name", "unknown")
            condition = ""

            if trigger == "level-up":
                level = detail.get("min_level")
                if level:
                    condition = f"Level {level}"
                elif detail.get("min_happiness"):
                    condition = "Happiness"
                elif detail.get("known_move"):
                    condition = f"Knows {detail['known_move']['name']}"
                elif detail.get("time_of_day"):
                    condition = f"Level up ({detail['time_of_day']})"
                else:
                    condition = "Level up"
            elif trigger == "use-item":
                item = detail.get("item", {}).get("name", "item")
                condition = item.replace("-", " ").title()
            elif trigger == "trade":
                held = detail.get("held_item")
                if held:
                    condition = f"Trade holding {held['name'].replace('-', ' ').title()}"
                else:
                    condition = "Trade"
            else:
                condition = trigger.replace("-", " ").title()

            results.append((from_id, to_id, trigger, condition))

        # Recurse into further evolutions
        results.extend(parse_chain(evo, conn))

    return results


def main():
    print("=" * 60)
    print("PokeMMO Companion -- Evolution Chain Builder")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("DELETE FROM evolutions")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch evolution chains (there are ~270 chains for Gen 1-5)
    total_evos = 0
    errors = 0

    # PokeAPI lists evolution chains by ID, up to ~300 for Gen 1-5
    for chain_id in range(1, 350):
        cache = RAW_DIR / f"chain_{chain_id}.json"
        try:
            data = fetch_json(f"{POKEAPI}/evolution-chain/{chain_id}", cache)
        except Exception:
            errors += 1
            continue

        evos = parse_chain(data["chain"], conn)
        for from_id, to_id, method, condition in evos:
            # Only include Gen 1-5 Pokemon (ID <= 649)
            if from_id <= 649 and to_id <= 649:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO evolutions (from_pokemon_id, to_pokemon_id, method, condition) VALUES (?, ?, ?, ?)",
                        (from_id, to_id, method, condition)
                    )
                    total_evos += 1
                except sqlite3.IntegrityError:
                    pass

        if chain_id % 50 == 0:
            conn.commit()
            print(f"  Processed {chain_id} chains ({total_evos} evolutions)...")

    conn.commit()
    conn.close()

    print(f"\nDone! {total_evos} evolution entries added ({errors} chain fetch errors)")


if __name__ == "__main__":
    main()
