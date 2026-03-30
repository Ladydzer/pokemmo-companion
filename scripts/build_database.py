"""Build the Pokemon SQLite database from PokeAPI data.

Downloads data from PokeAPI and builds a local SQLite database
with all Pokemon, moves, types, and spawn data needed by the companion app.

Usage:
    python scripts/build_database.py
    python scripts/build_database.py --pokemon-only
    python scripts/build_database.py --types-only
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "pokemon.db"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
POKEAPI_BASE = "https://pokeapi.co/api/v2"
MAX_POKEMON_ID = 649  # Gen 5 = first 649 Pokemon


def fetch_json(url: str, cache_file: Path | None = None) -> dict:
    """Fetch JSON from URL with file caching."""
    if cache_file and cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    print(f"  Fetching {url}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(data, f)

    return data


def build_type_effectiveness(conn: sqlite3.Connection) -> None:
    """Build the type effectiveness table from PokeAPI type data."""
    print("\n=== Building type effectiveness table ===")
    types_to_fetch = [
        "normal", "fire", "water", "electric", "grass", "ice",
        "fighting", "poison", "ground", "flying", "psychic",
        "bug", "rock", "ghost", "dragon", "dark", "steel",
    ]

    conn.execute("DELETE FROM type_effectiveness")

    for type_name in types_to_fetch:
        cache = RAW_DIR / "types" / f"{type_name}.json"
        data = fetch_json(f"{POKEAPI_BASE}/type/{type_name}", cache)

        relations = data["damage_relations"]

        for target in relations["double_damage_to"]:
            target_name = target["name"].capitalize()
            conn.execute(
                "INSERT OR REPLACE INTO type_effectiveness VALUES (?, ?, ?)",
                (type_name.capitalize(), target_name, 2.0)
            )

        for target in relations["half_damage_to"]:
            target_name = target["name"].capitalize()
            conn.execute(
                "INSERT OR REPLACE INTO type_effectiveness VALUES (?, ?, ?)",
                (type_name.capitalize(), target_name, 0.5)
            )

        for target in relations["no_damage_to"]:
            target_name = target["name"].capitalize()
            conn.execute(
                "INSERT OR REPLACE INTO type_effectiveness VALUES (?, ?, ?)",
                (type_name.capitalize(), target_name, 0.0)
            )

        print(f"  {type_name.capitalize()} OK")

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM type_effectiveness").fetchone()[0]
    print(f"  Total entries: {count}")


def build_pokemon_table(conn: sqlite3.Connection) -> None:
    """Build the pokemon table from PokeAPI data."""
    print(f"\n=== Building pokemon table (1-{MAX_POKEMON_ID}) ===")

    conn.execute("DELETE FROM pokemon")
    batch_size = 50

    for pokemon_id in range(1, MAX_POKEMON_ID + 1):
        cache = RAW_DIR / "pokemon" / f"{pokemon_id}.json"
        try:
            data = fetch_json(f"{POKEAPI_BASE}/pokemon/{pokemon_id}", cache)
        except Exception as e:
            print(f"  ERROR fetching #{pokemon_id}: {e}")
            continue

        name = data["name"].capitalize()
        # Fix multi-word names
        name = name.replace("-", " ").title().replace(" ", "-") if "-" in data["name"] else name

        types = [t["type"]["name"].capitalize() for t in data["types"]]
        type1 = types[0]
        type2 = types[1] if len(types) > 1 else None

        stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}

        abilities = []
        hidden_ability = None
        for a in data["abilities"]:
            if a["is_hidden"]:
                hidden_ability = a["ability"]["name"].replace("-", " ").title()
            else:
                abilities.append(a["ability"]["name"].replace("-", " ").title())

        # Determine generation
        if pokemon_id <= 151:
            gen = 1
        elif pokemon_id <= 251:
            gen = 2
        elif pokemon_id <= 386:
            gen = 3
        elif pokemon_id <= 493:
            gen = 4
        else:
            gen = 5

        conn.execute(
            """INSERT OR REPLACE INTO pokemon
               (id, name, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed,
                ability1, ability2, hidden_ability, generation,
                ev_hp, ev_attack, ev_defense, ev_sp_attack, ev_sp_defense, ev_speed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pokemon_id, name, type1, type2,
                stats.get("hp", 0), stats.get("attack", 0), stats.get("defense", 0),
                stats.get("special-attack", 0), stats.get("special-defense", 0),
                stats.get("speed", 0),
                abilities[0] if abilities else None,
                abilities[1] if len(abilities) > 1 else None,
                hidden_ability, gen,
                # EV yields from stats
                next((s["effort"] for s in data["stats"] if s["stat"]["name"] == "hp"), 0),
                next((s["effort"] for s in data["stats"] if s["stat"]["name"] == "attack"), 0),
                next((s["effort"] for s in data["stats"] if s["stat"]["name"] == "defense"), 0),
                next((s["effort"] for s in data["stats"] if s["stat"]["name"] == "special-attack"), 0),
                next((s["effort"] for s in data["stats"] if s["stat"]["name"] == "special-defense"), 0),
                next((s["effort"] for s in data["stats"] if s["stat"]["name"] == "speed"), 0),
            )
        )

        if pokemon_id % batch_size == 0:
            conn.commit()
            print(f"  {pokemon_id}/{MAX_POKEMON_ID} Pokemon loaded...")

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
    print(f"  Total Pokemon: {count}")


def build_sample_routes(conn: sqlite3.Connection) -> None:
    """Build sample route data for all 5 regions.

    This is a starter dataset — the full spawn data should come from
    PokeMMOZone/PokeMMO-Data JSON files.
    """
    print("\n=== Building sample routes ===")
    conn.execute("DELETE FROM routes")
    conn.execute("DELETE FROM spawns")

    # Sample routes with known spawns (can be expanded later)
    routes_data = [
        # Kanto
        ("Route 1", "Kanto", "route"),
        ("Route 2", "Kanto", "route"),
        ("Route 3", "Kanto", "route"),
        ("Route 4", "Kanto", "route"),
        ("Viridian Forest", "Kanto", "cave"),
        ("Mt. Moon", "Kanto", "cave"),
        ("Pallet Town", "Kanto", "city"),
        ("Viridian City", "Kanto", "city"),
        ("Pewter City", "Kanto", "city"),
        ("Cerulean City", "Kanto", "city"),
        # Johto
        ("Route 29", "Johto", "route"),
        ("Route 30", "Johto", "route"),
        ("Route 31", "Johto", "route"),
        ("New Bark Town", "Johto", "city"),
        ("Cherrygrove City", "Johto", "city"),
        ("Violet City", "Johto", "city"),
        # Hoenn
        ("Route 101", "Hoenn", "route"),
        ("Route 102", "Hoenn", "route"),
        ("Route 103", "Hoenn", "route"),
        ("Route 104", "Hoenn", "route"),
        ("Petalburg Woods", "Hoenn", "cave"),
        ("Littleroot Town", "Hoenn", "city"),
        ("Oldale Town", "Hoenn", "city"),
        ("Petalburg City", "Hoenn", "city"),
        ("Rustboro City", "Hoenn", "city"),
        # Sinnoh
        ("Route 201", "Sinnoh", "route"),
        ("Route 202", "Sinnoh", "route"),
        ("Route 203", "Sinnoh", "route"),
        ("Twinleaf Town", "Sinnoh", "city"),
        ("Sandgem Town", "Sinnoh", "city"),
        ("Jubilife City", "Sinnoh", "city"),
        # Unova
        ("Route 1", "Unova", "route"),
        ("Route 2", "Unova", "route"),
        ("Route 3", "Unova", "route"),
        ("Nuvema Town", "Unova", "city"),
        ("Accumula Town", "Unova", "city"),
        ("Striaton City", "Unova", "city"),
    ]

    for name, region, area_type in routes_data:
        conn.execute(
            "INSERT OR IGNORE INTO routes (name, region, area_type) VALUES (?, ?, ?)",
            (name, region, area_type)
        )

    # Sample spawns — Route 1 Kanto as example
    route1_kanto_id = conn.execute(
        "SELECT id FROM routes WHERE name='Route 1' AND region='Kanto'"
    ).fetchone()

    if route1_kanto_id:
        rid = route1_kanto_id[0]
        sample_spawns = [
            (rid, 19, "walking", 50.0, 2, 5),   # Rattata
            (rid, 16, "walking", 50.0, 2, 5),   # Pidgey
        ]
        for route_id, pokemon_id, method, rate, lmin, lmax in sample_spawns:
            conn.execute(
                "INSERT INTO spawns (route_id, pokemon_id, method, rate, level_min, level_max) VALUES (?, ?, ?, ?, ?, ?)",
                (route_id, pokemon_id, method, rate, lmin, lmax)
            )

    # Route 101 Hoenn
    route101_id = conn.execute(
        "SELECT id FROM routes WHERE name='Route 101' AND region='Hoenn'"
    ).fetchone()

    if route101_id:
        rid = route101_id[0]
        sample_spawns = [
            (rid, 263, "walking", 30.0, 2, 3),  # Zigzagoon
            (rid, 265, "walking", 30.0, 2, 3),  # Wurmple
            (rid, 261, "walking", 30.0, 2, 3),  # Poochyena
            (rid, 280, "walking", 10.0, 2, 3),  # Ralts
        ]
        for route_id, pokemon_id, method, rate, lmin, lmax in sample_spawns:
            conn.execute(
                "INSERT INTO spawns (route_id, pokemon_id, method, rate, level_min, level_max) VALUES (?, ?, ?, ?, ?, ?)",
                (route_id, pokemon_id, method, rate, lmin, lmax)
            )

    conn.commit()
    routes = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    spawns = conn.execute("SELECT COUNT(*) FROM spawns").fetchone()[0]
    print(f"  Routes: {routes}, Spawns: {spawns}")
    print("  NOTE: Full spawn data should be imported from PokeMMOZone/PokeMMO-Data")


def main():
    print("=" * 60)
    print("PokeMMO Companion — Database Builder")
    print("=" * 60)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Read schema from database module
    schema_path = PROJECT_ROOT / "src" / "data" / "database.py"
    schema_text = schema_path.read_text()
    # Extract SCHEMA string
    start = schema_text.index('SCHEMA = """') + len('SCHEMA = """')
    end = schema_text.index('"""', start)
    schema = schema_text[start:end]

    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(schema)

    args = sys.argv[1:]

    if "--types-only" in args:
        build_type_effectiveness(conn)
    elif "--pokemon-only" in args:
        build_pokemon_table(conn)
    else:
        build_type_effectiveness(conn)
        build_pokemon_table(conn)
        build_sample_routes(conn)

    conn.close()
    print(f"\nDatabase built: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
