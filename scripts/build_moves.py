"""Build moves database from raw Pokemon data + PokeAPI."""
import json
import sqlite3
import os
import time
import urllib.request

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'pokemon')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pokemon.db')
MOVE_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'moves')

# Gen 5 version groups
GEN5_VERSIONS = {'black-white', 'black-2-white-2'}


def fetch_move(move_id: int) -> dict | None:
    """Fetch move data from PokeAPI, with local cache."""
    cache_file = os.path.join(MOVE_CACHE_DIR, f'{move_id}.json')
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    url = f'https://pokeapi.co/api/v2/move/{move_id}/'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'PokeMMO-Companion/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            return data
    except Exception as e:
        print(f'  Failed to fetch move {move_id}: {e}')
        return None


def extract_gen5_moves(pokemon_data: dict) -> list[dict]:
    """Extract level-up and TM moves for Gen 5."""
    moves = []
    for m in pokemon_data.get('moves', []):
        move_name = m['move']['name']
        move_id = int(m['move']['url'].rstrip('/').split('/')[-1])
        for vgd in m['version_group_details']:
            vg = vgd.get('version_group', {}).get('name', '')
            if vg in GEN5_VERSIONS:
                method = vgd['move_learn_method']['name']
                level = vgd.get('level_learned_at', 0)
                if method in ('level-up', 'machine', 'tutor', 'egg'):
                    moves.append({
                        'move_name': move_name,
                        'move_id': move_id,
                        'method': method,
                        'level': level,
                    })
                break  # Only need one Gen5 entry per move
    return moves


def main():
    os.makedirs(MOVE_CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # Collect all unique move IDs first
    print('Scanning Pokemon for moves...')
    all_moves = {}  # move_id -> move_name
    pokemon_moves = []  # (pokemon_id, move_id, method, level)

    for pid in range(1, 650):
        filepath = os.path.join(RAW_DIR, f'{pid}.json')
        if not os.path.exists(filepath):
            continue
        with open(filepath) as f:
            data = json.load(f)
        moves = extract_gen5_moves(data)
        for m in moves:
            all_moves[m['move_id']] = m['move_name']
            pokemon_moves.append((pid, m['move_id'], m['method'], m['level']))

    print(f'Found {len(all_moves)} unique moves, {len(pokemon_moves)} pokemon-move links')

    # Fetch move details
    print(f'Fetching move details (cached: {len(os.listdir(MOVE_CACHE_DIR))} files)...')
    move_data = {}
    fetched = 0
    for i, (mid, mname) in enumerate(sorted(all_moves.items())):
        data = fetch_move(mid)
        if data:
            move_data[mid] = {
                'id': mid,
                'name': data['name'],
                'type': data['type']['name'].capitalize(),
                'power': data.get('power') or 0,
                'accuracy': data.get('accuracy') or 0,
                'pp': data.get('pp') or 0,
                'category': data.get('damage_class', {}).get('name', 'status'),
                'effect': (data.get('effect_entries') or [{}])[0].get('short_effect', '') if data.get('effect_entries') else '',
            }
            if not os.path.exists(os.path.join(MOVE_CACHE_DIR, f'{mid}.json')):
                fetched += 1
                if fetched % 50 == 0:
                    print(f'  Fetched {fetched} moves...')
                    time.sleep(0.5)  # Be nice to API
        if (i + 1) % 100 == 0:
            print(f'  Processed {i+1}/{len(all_moves)} moves')

    print(f'Got data for {len(move_data)} moves')

    # Clear and rebuild tables
    conn.execute('DELETE FROM moves')
    conn.execute('DELETE FROM pokemon_moves')

    # Insert moves
    for m in move_data.values():
        conn.execute(
            'INSERT OR REPLACE INTO moves (id, name, type, power, accuracy, pp, category, effect) VALUES (?,?,?,?,?,?,?,?)',
            (m['id'], m['name'], m['type'], m['power'], m['accuracy'], m['pp'], m['category'], m['effect'])
        )

    # Insert pokemon_moves
    for pm in pokemon_moves:
        pid, mid, method, level = pm
        if mid in move_data:
            conn.execute(
                'INSERT INTO pokemon_moves (pokemon_id, move_id, method, level) VALUES (?,?,?,?)',
                (pid, mid, method, level)
            )

    conn.commit()

    # Verify
    mc = conn.execute('SELECT COUNT(*) FROM moves').fetchone()[0]
    pmc = conn.execute('SELECT COUNT(*) FROM pokemon_moves').fetchone()[0]
    print(f'\nDone! Moves: {mc}, Pokemon-Move links: {pmc}')

    # Sample verification
    print('\nPikachu level-up moves:')
    rows = conn.execute('''
        SELECT m.name, m.type, m.power, m.category, pm.level, pm.method
        FROM pokemon_moves pm JOIN moves m ON pm.move_id = m.id
        WHERE pm.pokemon_id = 25 AND pm.method = 'level-up'
        ORDER BY pm.level
    ''').fetchall()
    for r in rows:
        print(f'  Lv.{r[4]:2d} - {r[0]} ({r[1]}, {r[2]} pwr, {r[3]})')

    conn.close()


if __name__ == '__main__':
    main()
