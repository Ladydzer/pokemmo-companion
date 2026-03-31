"""Add French names to moves table from cached PokeAPI data."""
import json
import os
import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

MOVE_CACHE = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'moves')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pokemon.db')


def main():
    conn = sqlite3.connect(DB_PATH)

    # Add name_fr column if not exists
    cols = [r[1] for r in conn.execute('PRAGMA table_info(moves)').fetchall()]
    if 'name_fr' not in cols:
        conn.execute('ALTER TABLE moves ADD COLUMN name_fr TEXT')
        print('Added name_fr column to moves table')

    # Update FR names from cached move files
    updated = 0
    for fn in os.listdir(MOVE_CACHE):
        if not fn.endswith('.json'):
            continue
        mid = int(fn.replace('.json', ''))
        with open(os.path.join(MOVE_CACHE, fn), encoding='utf-8') as f:
            data = json.load(f)
        fr_name = next((n['name'] for n in data.get('names', []) if n['language']['name'] == 'fr'), None)
        if fr_name:
            conn.execute('UPDATE moves SET name_fr = ? WHERE id = ?', (fr_name, mid))
            updated += 1

    conn.commit()
    print(f'Updated {updated} moves with FR names')

    # Verify
    sample = conn.execute('SELECT name, name_fr FROM moves WHERE name_fr IS NOT NULL ORDER BY id LIMIT 10').fetchall()
    for r in sample:
        print(f'  {r[0]} -> {r[1]}')

    # Count
    total = conn.execute('SELECT COUNT(*) FROM moves').fetchone()[0]
    fr_count = conn.execute('SELECT COUNT(*) FROM moves WHERE name_fr IS NOT NULL').fetchone()[0]
    print(f'\nFR names: {fr_count}/{total}')

    conn.close()


if __name__ == '__main__':
    main()
