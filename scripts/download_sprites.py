"""Download Pokemon sprites from PokeAPI sprite CDN.

Downloads front_default sprites for all 649 Gen 1-5 Pokemon.
Sprites are 96x96 PNG images from the official PokeAPI CDN.

Usage:
    python scripts/download_sprites.py
"""
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

PROJECT_ROOT = Path(__file__).parent.parent
SPRITES_DIR = PROJECT_ROOT / "data" / "sprites"
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png"
MAX_POKEMON = 649


def download_sprite(pokemon_id: int) -> bool:
    """Download a single sprite."""
    dest = SPRITES_DIR / f"{pokemon_id}.png"
    if dest.exists() and dest.stat().st_size > 100:
        return True  # Already downloaded

    url = SPRITE_URL.format(id=pokemon_id)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            dest.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def main():
    print("=" * 60)
    print("PokeMMO Companion -- Sprite Downloader")
    print(f"Downloading {MAX_POKEMON} Pokemon sprites...")
    print("=" * 60)

    SPRITES_DIR.mkdir(parents=True, exist_ok=True)

    # Check already downloaded
    existing = len([f for f in SPRITES_DIR.glob("*.png") if f.stat().st_size > 100])
    if existing >= MAX_POKEMON:
        print(f"All {MAX_POKEMON} sprites already downloaded!")
        return

    print(f"Already have: {existing}/{MAX_POKEMON}")
    to_download = [i for i in range(1, MAX_POKEMON + 1)
                   if not (SPRITES_DIR / f"{i}.png").exists()]

    success = 0
    failed = 0

    # Download in parallel (8 threads)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_sprite, pid): pid for pid in to_download}
        for i, future in enumerate(as_completed(futures), 1):
            pid = futures[future]
            if future.result():
                success += 1
            else:
                failed += 1

            if i % 50 == 0:
                print(f"  Progress: {i}/{len(to_download)} ({success} OK, {failed} failed)")

    total = existing + success
    print(f"\nDone! {total}/{MAX_POKEMON} sprites available ({failed} failed)")
    size_mb = sum(f.stat().st_size for f in SPRITES_DIR.glob("*.png")) / (1024 * 1024)
    print(f"Total size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
