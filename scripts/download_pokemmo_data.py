"""Download PokeMMO-specific data from community sources.

Downloads spawn tables, location data, and other PokeMMO-specific data
from the PokeMMOZone/PokeMMO-Data GitHub repository.

Usage:
    python scripts/download_pokemmo_data.py
"""
import json
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "pokemmo"

# PokeMMOZone data repository (raw GitHub URLs)
POKEMMOZONE_BASE = "https://raw.githubusercontent.com/PokeMMOZone/PokeMMO-Data/main/data"
POKEMMO_TOOLS_BASE = "https://raw.githubusercontent.com/PokeMMO-Tools/pokemmo-data/main"

# Files to download from PokeMMOZone
POKEMMOZONE_FILES = [
    "location-rarities.json",
    "location-regions.json",
    "location-types.json",
    "pokemon-data.json",
    "moves-data.json",
    "egg-groups-data.json",
    "egg-moves-data.json",
    "abilities-data.json",
    "obtainable-data.json",
    "gender-rates.json",
    "natures-data.json",
]

# Files from PokeMMO-Tools
POKEMMO_TOOLS_FILES = [
    "data/monsters.json",
    "data/moves.json",
    "data/pokedex.json",
    "data/items.json",
]


def download_file(url: str, dest: Path) -> bool:
    """Download a file from URL to destination."""
    try:
        print(f"  Downloading {dest.name}...")
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            size_kb = len(resp.content) / 1024
            print(f"    -> {size_kb:.0f} KB")
            return True
        else:
            print(f"    -> FAILED ({resp.status_code})")
            return False
    except Exception as e:
        print(f"    -> ERROR: {e}")
        return False


def download_pokemmozone():
    """Download data from PokeMMOZone repository."""
    print("\n=== PokeMMOZone/PokeMMO-Data ===")
    dest_dir = RAW_DIR / "pokemmozone"
    success = 0
    for filename in POKEMMOZONE_FILES:
        url = f"{POKEMMOZONE_BASE}/{filename}"
        dest = dest_dir / filename
        if download_file(url, dest):
            success += 1
    print(f"  Downloaded: {success}/{len(POKEMMOZONE_FILES)}")
    return success


def download_pokemmo_tools():
    """Download data from PokeMMO-Tools repository."""
    print("\n=== PokeMMO-Tools/pokemmo-data ===")
    dest_dir = RAW_DIR / "pokemmo-tools"
    success = 0
    for filepath in POKEMMO_TOOLS_FILES:
        url = f"{POKEMMO_TOOLS_BASE}/{filepath}"
        filename = Path(filepath).name
        dest = dest_dir / filename
        if download_file(url, dest):
            success += 1
    print(f"  Downloaded: {success}/{len(POKEMMO_TOOLS_FILES)}")
    return success


def analyze_location_data():
    """Analyze downloaded location data and show summary."""
    print("\n=== Data Analysis ===")

    # Check location-regions.json
    regions_file = RAW_DIR / "pokemmozone" / "location-regions.json"
    if regions_file.exists():
        with open(regions_file) as f:
            data = json.load(f)
        if isinstance(data, dict):
            print(f"  Regions found: {list(data.keys())}")
            for region, locations in data.items():
                if isinstance(locations, (list, dict)):
                    count = len(locations)
                    print(f"    {region}: {count} locations")
        elif isinstance(data, list):
            print(f"  Total location entries: {len(data)}")

    # Check location-rarities.json
    rarities_file = RAW_DIR / "pokemmozone" / "location-rarities.json"
    if rarities_file.exists():
        with open(rarities_file) as f:
            data = json.load(f)
        if isinstance(data, (list, dict)):
            count = len(data)
            print(f"  Location rarities entries: {count}")

    # Check pokemon-data.json
    pokemon_file = RAW_DIR / "pokemmozone" / "pokemon-data.json"
    if pokemon_file.exists():
        with open(pokemon_file) as f:
            data = json.load(f)
        if isinstance(data, (list, dict)):
            count = len(data)
            print(f"  Pokemon data entries: {count}")


def main():
    print("=" * 60)
    print("PokeMMO Companion -- Data Downloader")
    print("=" * 60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    z = download_pokemmozone()
    t = download_pokemmo_tools()

    analyze_location_data()

    total = z + t
    print(f"\nTotal files downloaded: {total}")
    if total > 0:
        print("Run 'python scripts/import_spawns.py' to import into the database.")


if __name__ == "__main__":
    main()
