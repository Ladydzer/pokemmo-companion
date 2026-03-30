"""Import PokeMMO-specific spawn data into the SQLite database.

Reads the PokeMMOZone location-regions.json and imports spawn data
for all 5 regions into the routes and spawns tables.

Usage:
    python scripts/import_spawns.py
"""
import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "pokemon.db"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "pokemmo" / "pokemmozone"

# Map PokeMMOZone rarity strings to approximate percentage rates
RARITY_TO_RATE = {
    "Common": 30.0,
    "Uncommon": 15.0,
    "Rare": 5.0,
    "Very Rare": 2.0,
    "Lure": 10.0,        # Special fishing/lure encounters
    "Horde": 20.0,        # Horde encounters
    "Special": 3.0,       # Special conditions
}

# Map encounter method from rarity/type context
def classify_method(rarity: str, location: str) -> str:
    """Classify encounter method from rarity and location hints."""
    rarity_lower = rarity.lower()
    location_lower = location.lower()

    if "horde" in rarity_lower:
        return "horde"
    if "surf" in rarity_lower or "surfing" in rarity_lower:
        return "surfing"
    if "fish" in rarity_lower or "rod" in rarity_lower:
        if "super" in rarity_lower:
            return "fishing_super"
        elif "good" in rarity_lower:
            return "fishing_good"
        return "fishing_old"
    if "lure" in rarity_lower:
        return "fishing_old"

    # Check location name for hints
    if any(w in location_lower for w in ["sea", "ocean", "lake", "pond", "water"]):
        return "surfing"

    return "walking"


def main():
    print("=" * 60)
    print("PokeMMO Companion -- Spawn Data Importer")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run scripts/build_database.py first.")
        sys.exit(1)

    regions_file = RAW_DIR / "location-regions.json"
    if not regions_file.exists():
        print(f"ERROR: Spawn data not found at {regions_file}")
        print("Run scripts/download_pokemmo_data.py first.")
        sys.exit(1)

    with open(regions_file, encoding="utf-8") as f:
        regions_data = json.load(f)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    # Clear existing spawn data (keep pokemon and types)
    conn.execute("DELETE FROM spawns")
    conn.execute("DELETE FROM routes")

    total_routes = 0
    total_spawns = 0

    for region_name, entries in regions_data.items():
        print(f"\n--- {region_name} ({len(entries)} raw entries) ---")

        # Group entries by location
        locations = defaultdict(list)
        for entry in entries:
            loc = entry.get("location", "Unknown")
            locations[loc].append(entry)

        region_routes = 0
        region_spawns = 0

        for location_name, spawns in locations.items():
            # Determine area type from location name
            loc_lower = location_name.lower()
            if "route" in loc_lower:
                area_type = "route"
            elif any(w in loc_lower for w in ["city", "town", "village"]):
                area_type = "city"
            elif any(w in loc_lower for w in ["cave", "tunnel", "mt.", "mount", "rock"]):
                area_type = "cave"
            elif any(w in loc_lower for w in ["sea", "ocean", "lake", "pond"]):
                area_type = "water"
            elif any(w in loc_lower for w in ["forest", "woods", "garden", "park"]):
                area_type = "forest"
            else:
                area_type = "other"

            # Insert route (title case the name)
            display_name = location_name.title()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO routes (name, region, area_type) VALUES (?, ?, ?)",
                    (display_name, region_name, area_type)
                )
            except sqlite3.IntegrityError:
                pass

            route_row = conn.execute(
                "SELECT id FROM routes WHERE name = ? AND region = ?",
                (display_name, region_name)
            ).fetchone()

            if not route_row:
                continue
            route_id = route_row[0]
            region_routes += 1

            # Insert spawns for this location
            for spawn in spawns:
                pokemon_id = spawn.get("pokemon_id")
                if not pokemon_id:
                    continue

                rarity = spawn.get("rarity", "Common")
                rate = RARITY_TO_RATE.get(rarity, 10.0)
                method = classify_method(rarity, location_name)
                min_level = spawn.get("min_level", 0)
                max_level = spawn.get("max_level", 0)

                try:
                    conn.execute(
                        """INSERT INTO spawns (route_id, pokemon_id, method, rate, level_min, level_max)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (route_id, pokemon_id, method, rate, min_level, max_level)
                    )
                    region_spawns += 1
                except sqlite3.IntegrityError:
                    pass

        conn.commit()
        total_routes += region_routes
        total_spawns += region_spawns
        print(f"  Routes: {region_routes}, Spawns: {region_spawns}")

    conn.close()

    print(f"\n{'='*60}")
    print(f"Import complete!")
    print(f"  Total routes: {total_routes}")
    print(f"  Total spawn entries: {total_spawns}")
    print(f"  Regions: {list(regions_data.keys())}")
    print(f"  Database: {DB_PATH}")


if __name__ == "__main__":
    main()
