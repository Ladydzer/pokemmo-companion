"""SQLite database manager for PokeMMO Companion."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from ..utils.config import DB_PATH
from ..utils.logger import log


class Database:
    """SQLite database for Pokemon data."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            log.info(f"Database ready at {self.db_path}")

    @contextmanager
    def connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_pokemon_by_name(self, name: str) -> dict | None:
        """Look up a Pokemon by name (case-insensitive)."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM pokemon WHERE LOWER(name) = LOWER(?)", (name,)
            ).fetchone()
            return dict(row) if row else None

    def get_pokemon_by_id(self, pokemon_id: int) -> dict | None:
        """Look up a Pokemon by national dex ID."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM pokemon WHERE id = ?", (pokemon_id,)
            ).fetchone()
            return dict(row) if row else None

    def search_pokemon(self, query: str, limit: int = 20) -> list[dict]:
        """Search Pokemon by partial name match."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pokemon WHERE LOWER(name) LIKE LOWER(?) ORDER BY id LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_spawns_for_route(self, route_name: str, region: str | None = None) -> list[dict]:
        """Get Pokemon spawns for a given route."""
        with self.connect() as conn:
            if region:
                rows = conn.execute(
                    """SELECT s.*, p.name as pokemon_name, p.type1, p.type2
                       FROM spawns s
                       JOIN pokemon p ON s.pokemon_id = p.id
                       JOIN routes r ON s.route_id = r.id
                       WHERE LOWER(r.name) LIKE LOWER(?) AND LOWER(r.region) = LOWER(?)
                       ORDER BY s.rate DESC""",
                    (f"%{route_name}%", region)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT s.*, p.name as pokemon_name, p.type1, p.type2, r.region
                       FROM spawns s
                       JOIN pokemon p ON s.pokemon_id = p.id
                       JOIN routes r ON s.route_id = r.id
                       WHERE LOWER(r.name) LIKE LOWER(?)
                       ORDER BY s.rate DESC""",
                    (f"%{route_name}%",)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_routes_for_region(self, region: str) -> list[dict]:
        """Get all routes in a region."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM routes WHERE LOWER(region) = LOWER(?) ORDER BY name",
                (region,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_type_effectiveness(self, atk_type: str, def_type: str) -> float:
        """Get type effectiveness from database."""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT multiplier FROM type_effectiveness
                   WHERE LOWER(attacking_type) = LOWER(?)
                   AND LOWER(defending_type) = LOWER(?)""",
                (atk_type, def_type)
            ).fetchone()
            return row["multiplier"] if row else 1.0

    def get_pokemon_count(self) -> int:
        """Get total Pokemon count in database."""
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM pokemon").fetchone()
            return row["cnt"]

    def get_route_count(self) -> int:
        """Get total route count in database."""
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM routes").fetchone()
            return row["cnt"]

    def get_spawn_count(self) -> int:
        """Get total spawn entry count."""
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM spawns").fetchone()
            return row["cnt"]

    def get_progression(self, region: str) -> list[dict]:
        """Get progression steps for a region, ordered by step number."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM progression WHERE LOWER(region) = LOWER(?) ORDER BY step",
                (region,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_current_step(self, region: str, location: str) -> dict | None:
        """Get the progression step for a given location in a region."""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT * FROM progression
                   WHERE LOWER(region) = LOWER(?) AND LOWER(location) LIKE LOWER(?)
                   ORDER BY step LIMIT 1""",
                (region, f"%{location}%")
            ).fetchone()
            return dict(row) if row else None

    def get_next_step(self, region: str, current_step: int) -> dict | None:
        """Get the next progression step after the current one."""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT * FROM progression
                   WHERE LOWER(region) = LOWER(?) AND step > ?
                   ORDER BY step LIMIT 1""",
                (region, current_step)
            ).fetchone()
            return dict(row) if row else None

    def get_route_min_badges(self, route_name: str, region: str) -> int:
        """Get minimum badges required to reach a route."""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT min_badges FROM routes
                   WHERE LOWER(name) LIKE LOWER(?) AND LOWER(region) = LOWER(?)""",
                (f"%{route_name}%", region)
            ).fetchone()
            return row["min_badges"] if row and row["min_badges"] else 0

    def get_evolution_chain(self, pokemon_id: int) -> list[dict]:
        """Get the full evolution chain for a Pokemon.

        Returns list of {id, name, type1, type2, condition} in chain order.
        """
        with self.connect() as conn:
            # Find the base form by walking backwards
            base_id = pokemon_id
            while True:
                row = conn.execute(
                    "SELECT from_pokemon_id FROM evolutions WHERE to_pokemon_id = ?",
                    (base_id,)
                ).fetchone()
                if row:
                    base_id = row[0]
                else:
                    break

            # Walk forward from base to build chain
            chain = []
            current_id = base_id

            pokemon = conn.execute(
                "SELECT id, name, type1, type2 FROM pokemon WHERE id = ?",
                (current_id,)
            ).fetchone()
            if pokemon:
                chain.append({**dict(pokemon), "condition": ""})

            while True:
                row = conn.execute(
                    """SELECT e.to_pokemon_id, e.condition, p.name, p.type1, p.type2
                       FROM evolutions e
                       JOIN pokemon p ON e.to_pokemon_id = p.id
                       WHERE e.from_pokemon_id = ?""",
                    (current_id,)
                ).fetchone()
                if row:
                    r = dict(row)
                    chain.append({
                        "id": r["to_pokemon_id"],
                        "name": r["name"],
                        "type1": r["type1"],
                        "type2": r["type2"],
                        "condition": r["condition"],
                    })
                    current_id = r["to_pokemon_id"]
                else:
                    break

            return chain

    def get_location_items(self, route_name: str, region: str | None = None) -> list[dict]:
        """Get items/NPCs/POI for a location."""
        with self.connect() as conn:
            if region:
                rows = conn.execute(
                    """SELECT li.* FROM location_items li
                       JOIN routes r ON li.route_id = r.id
                       WHERE LOWER(r.name) LIKE LOWER(?) AND LOWER(r.region) = LOWER(?)
                       ORDER BY li.item_type""",
                    (f"%{route_name}%", region)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT li.* FROM location_items li
                       JOIN routes r ON li.route_id = r.id
                       WHERE LOWER(r.name) LIKE LOWER(?)
                       ORDER BY li.item_type""",
                    (f"%{route_name}%",)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_pokemon_locations(self, pokemon_name: str) -> list[dict]:
        """Get all locations where a Pokemon can be found."""
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT r.name as route_name, r.region, s.method, s.rate, s.level_min, s.level_max
                   FROM spawns s
                   JOIN routes r ON s.route_id = r.id
                   JOIN pokemon p ON s.pokemon_id = p.id
                   WHERE LOWER(p.name) = LOWER(?)
                   ORDER BY s.rate DESC""",
                (pokemon_name,)
            ).fetchall()
            return [dict(r) for r in rows]


SCHEMA = """
CREATE TABLE IF NOT EXISTS pokemon (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type1 TEXT NOT NULL,
    type2 TEXT,
    hp INTEGER NOT NULL DEFAULT 0,
    attack INTEGER NOT NULL DEFAULT 0,
    defense INTEGER NOT NULL DEFAULT 0,
    sp_attack INTEGER NOT NULL DEFAULT 0,
    sp_defense INTEGER NOT NULL DEFAULT 0,
    speed INTEGER NOT NULL DEFAULT 0,
    ability1 TEXT,
    ability2 TEXT,
    hidden_ability TEXT,
    generation INTEGER NOT NULL,
    ev_hp INTEGER NOT NULL DEFAULT 0,
    ev_attack INTEGER NOT NULL DEFAULT 0,
    ev_defense INTEGER NOT NULL DEFAULT 0,
    ev_sp_attack INTEGER NOT NULL DEFAULT 0,
    ev_sp_defense INTEGER NOT NULL DEFAULT 0,
    ev_speed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    power INTEGER,
    accuracy INTEGER,
    pp INTEGER,
    category TEXT NOT NULL,  -- physical, special, status
    effect TEXT
);

CREATE TABLE IF NOT EXISTS pokemon_moves (
    pokemon_id INTEGER NOT NULL,
    move_id INTEGER NOT NULL,
    method TEXT NOT NULL,  -- level-up, tm, egg, tutor
    level INTEGER,
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (move_id) REFERENCES moves(id)
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    area_type TEXT,  -- route, city, cave, water, building
    min_badges INTEGER DEFAULT 0,  -- minimum badges to reach this route
    UNIQUE(name, region)
);

CREATE TABLE IF NOT EXISTS spawns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    method TEXT NOT NULL DEFAULT 'walking',  -- walking, surfing, fishing_old, fishing_good, fishing_super, horde
    rate REAL NOT NULL DEFAULT 0,  -- percentage 0-100
    level_min INTEGER,
    level_max INTEGER,
    FOREIGN KEY (route_id) REFERENCES routes(id),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id)
);

CREATE TABLE IF NOT EXISTS type_effectiveness (
    attacking_type TEXT NOT NULL,
    defending_type TEXT NOT NULL,
    multiplier REAL NOT NULL,
    PRIMARY KEY (attacking_type, defending_type)
);

CREATE TABLE IF NOT EXISTS evolutions (
    from_pokemon_id INTEGER NOT NULL,
    to_pokemon_id INTEGER NOT NULL,
    method TEXT NOT NULL,  -- level, stone, trade, friendship, etc.
    condition TEXT,  -- level number, item name, etc.
    FOREIGN KEY (from_pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (to_pokemon_id) REFERENCES pokemon(id)
);

CREATE TABLE IF NOT EXISTS progression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    step INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    recommended_level INTEGER,
    badge_number INTEGER,
    UNIQUE(region, step)
);

CREATE INDEX IF NOT EXISTS idx_pokemon_name ON pokemon(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_pokemon_type ON pokemon(type1, type2);
CREATE INDEX IF NOT EXISTS idx_routes_region ON routes(region);
CREATE INDEX IF NOT EXISTS idx_spawns_route ON spawns(route_id);
CREATE INDEX IF NOT EXISTS idx_spawns_pokemon ON spawns(pokemon_id);
CREATE INDEX IF NOT EXISTS idx_progression_region ON progression(region, step);
"""


if __name__ == "__main__":
    db = Database()
    print(f"Database initialized at {db.db_path}")
    print(f"Pokemon: {db.get_pokemon_count()}")
    print(f"Routes: {db.get_route_count()}")
    print(f"Spawns: {db.get_spawn_count()}")
