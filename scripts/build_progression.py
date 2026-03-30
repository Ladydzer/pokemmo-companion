"""Build progression data for all 5 regions.

Populates the progression table with walkthrough steps and
updates routes with min_badges for coach GPS inference.

Usage:
    python scripts/build_progression.py
"""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "pokemon.db"


# Progression data: each region has ordered steps with gym badges, locations, and tips
PROGRESSION = {
    "Kanto": [
        (1, "Start in Pallet Town", "Get your starter from Prof. Oak", "Pallet Town", 5, 0),
        (2, "Route 1 to Viridian", "Head north, catch Pidgey/Rattata", "Route 1", 5, 0),
        (3, "Viridian City", "Get Pokedex from Oak, buy Poke Balls", "Viridian City", 5, 0),
        (4, "Viridian Forest", "Catch Pikachu (rare!), train to Lv.10", "Viridian Forest", 8, 0),
        (5, "Pewter City Gym - Brock", "Rock type. Use Water/Grass/Fighting", "Pewter City", 12, 0),
        (6, "Mt. Moon", "Navigate cave, fight Team Rocket", "Mt. Moon", 15, 1),
        (7, "Cerulean City Gym - Misty", "Water type. Use Grass/Electric", "Cerulean City", 21, 1),
        (8, "Route 24-25 - Nugget Bridge", "5 trainers + Team Rocket", "Route 24", 22, 2),
        (9, "Vermilion City Gym - Lt. Surge", "Electric type. Use Ground", "Vermilion City", 24, 2),
        (10, "S.S. Anne", "Get HM01 Cut from the Captain", "Vermilion City", 24, 2),
        (11, "Rock Tunnel", "Need Flash, grind to Lv.25+", "Rock Tunnel", 26, 3),
        (12, "Celadon City Gym - Erika", "Grass type. Use Fire/Ice/Flying", "Celadon City", 29, 3),
        (13, "Team Rocket Hideout", "Get Silph Scope, Celadon Game Corner", "Celadon City", 30, 4),
        (14, "Pokemon Tower", "Ghost types, use Silph Scope", "Lavender Town", 30, 4),
        (15, "Saffron City Gym - Sabrina", "Psychic type. Use Bug/Ghost/Dark", "Saffron City", 37, 4),
        (16, "Fuchsia City Gym - Koga", "Poison type. Use Ground/Psychic", "Fuchsia City", 40, 5),
        (17, "Safari Zone", "Get HM03 Surf, HM04 Strength", "Fuchsia City", 40, 5),
        (18, "Cinnabar Island Gym - Blaine", "Fire type. Use Water/Ground/Rock", "Cinnabar Island", 42, 6),
        (19, "Viridian City Gym - Giovanni", "Ground type. Use Water/Grass/Ice", "Viridian City", 45, 7),
        (20, "Victory Road", "Need all 8 badges, train to Lv.50+", "Victory Road", 48, 8),
        (21, "Elite Four + Champion", "Lv.50-65 recommended", "Indigo Plateau", 55, 8),
    ],
    "Johto": [
        (1, "Start in New Bark Town", "Get starter from Prof. Elm", "New Bark Town", 5, 0),
        (2, "Route 29-30 to Cherrygrove", "Catch early Pokemon, deliver Egg", "Route 29", 5, 0),
        (3, "Violet City Gym - Falkner", "Flying type. Use Rock/Electric/Ice", "Violet City", 13, 0),
        (4, "Sprout Tower", "Train here, get Flash", "Violet City", 10, 0),
        (5, "Route 32-33 to Azalea", "Head south through Union Cave", "Route 32", 14, 1),
        (6, "Azalea Town Gym - Bugsy", "Bug type. Use Fire/Rock/Flying", "Azalea Town", 17, 1),
        (7, "Ilex Forest", "Get HM01 Cut, catch Headbutt Pokemon", "Ilex Forest", 18, 2),
        (8, "Goldenrod City Gym - Whitney", "Normal type. Use Fighting. Miltank is hard!", "Goldenrod City", 20, 2),
        (9, "National Park", "Bug Catching Contest (Tues/Thurs/Sat)", "National Park", 20, 3),
        (10, "Ecruteak City Gym - Morty", "Ghost type. Use Dark/Ghost", "Ecruteak City", 25, 3),
        (11, "Route 38-39 to Olivine", "Head west", "Route 38", 25, 4),
        (12, "Olivine City", "Get medicine for Jasmine's Ampharos", "Olivine City", 28, 4),
        (13, "Cianwood City Gym - Chuck", "Fighting type. Use Flying/Psychic", "Cianwood City", 30, 4),
        (14, "Olivine City Gym - Jasmine", "Steel type. Use Fire/Fighting/Ground", "Olivine City", 33, 5),
        (15, "Mahogany Town Gym - Pryce", "Ice type. Use Fire/Fighting/Rock/Steel", "Mahogany Town", 34, 6),
        (16, "Team Rocket Radio Tower", "Clear Team Rocket from Goldenrod", "Goldenrod City", 35, 7),
        (17, "Blackthorn City Gym - Clair", "Dragon type. Use Ice/Dragon", "Blackthorn City", 40, 7),
        (18, "Dragon's Den", "Pass elder's test for Rising Badge", "Blackthorn City", 40, 7),
        (19, "Victory Road Johto", "Train to Lv.45+", "Victory Road", 45, 8),
        (20, "Elite Four + Champion", "Lv.45-55 recommended", "Indigo Plateau", 50, 8),
    ],
    "Hoenn": [
        (1, "Start in Littleroot Town", "Get starter, help Prof. Birch", "Littleroot Town", 5, 0),
        (2, "Route 101-103", "Catch early Pokemon, rival battle", "Route 101", 5, 0),
        (3, "Rustboro City Gym - Roxanne", "Rock type. Use Water/Grass/Fighting", "Rustboro City", 14, 0),
        (4, "Rusturf Tunnel", "Save Peeko, get HM01 Cut", "Rusturf Tunnel", 15, 1),
        (5, "Dewford Town Gym - Brawly", "Fighting type. Use Flying/Psychic", "Dewford Town", 18, 1),
        (6, "Granite Cave", "Deliver letter to Steven", "Granite Cave", 16, 1),
        (7, "Slateport City", "Beat Team Aqua/Magma at museum", "Slateport City", 18, 2),
        (8, "Mauville City Gym - Wattson", "Electric type. Use Ground", "Mauville City", 24, 2),
        (9, "Route 110 - Cycling Road", "Get the Acro Bike or Mach Bike", "Route 110", 24, 3),
        (10, "Lavaridge Town Gym - Flannery", "Fire type. Use Water/Ground/Rock", "Lavaridge Town", 29, 3),
        (11, "Petalburg City Gym - Norman", "Normal type. Use Fighting. Lv.28+ recommended", "Petalburg City", 31, 4),
        (12, "Get HM03 Surf", "From Wally's dad after Norman", "Petalburg City", 31, 5),
        (13, "Fortree City Gym - Winona", "Flying type. Use Rock/Electric/Ice", "Fortree City", 33, 5),
        (14, "Mt. Pyre + Team Aqua/Magma", "Get the orb", "Mt. Pyre", 35, 6),
        (15, "Mossdeep City Gym - Tate & Liza", "Psychic type. Use Bug/Ghost/Dark", "Mossdeep City", 42, 6),
        (16, "Seafloor Cavern", "Stop the legendary awakening", "Route 128", 40, 7),
        (17, "Sootopolis City Gym - Juan", "Water type. Use Grass/Electric", "Sootopolis City", 46, 7),
        (18, "Victory Road Hoenn", "Train to Lv.50+", "Victory Road", 48, 8),
        (19, "Elite Four + Champion", "Lv.50-60 recommended", "Ever Grande City", 55, 8),
    ],
    "Sinnoh": [
        (1, "Start in Twinleaf Town", "Get starter from Prof. Rowan", "Twinleaf Town", 5, 0),
        (2, "Route 201-202", "Catch early Pokemon", "Route 201", 5, 0),
        (3, "Oreburgh City Gym - Roark", "Rock type. Use Water/Grass/Fighting", "Oreburgh City", 14, 0),
        (4, "Oreburgh Mine", "Get HM06 Rock Smash", "Oreburgh Mine", 12, 0),
        (5, "Eterna City Gym - Gardenia", "Grass type. Use Fire/Ice/Flying", "Eterna City", 22, 1),
        (6, "Team Galactic Eterna Building", "Rescue the bicycle shop owner", "Eterna City", 22, 2),
        (7, "Veilstone City Gym - Maylene", "Fighting type. Use Flying/Psychic", "Veilstone City", 28, 2),
        (8, "Pastoria City Gym - Crasher Wake", "Water type. Use Grass/Electric", "Pastoria City", 30, 3),
        (9, "Hearthome City Gym - Fantina", "Ghost type. Use Dark/Ghost", "Hearthome City", 33, 4),
        (10, "Canalave City Gym - Byron", "Steel type. Use Fire/Fighting/Ground", "Canalave City", 37, 5),
        (11, "Lake Valor + Team Galactic", "Stop Saturn at the lake", "Lake Valor", 38, 5),
        (12, "Snowpoint City Gym - Candice", "Ice type. Use Fire/Fighting/Rock/Steel", "Snowpoint City", 40, 6),
        (13, "Team Galactic HQ", "Free the lake trio, get Galactic Key", "Veilstone City", 42, 7),
        (14, "Sunyshore City Gym - Volkner", "Electric type. Use Ground", "Sunyshore City", 46, 7),
        (15, "Victory Road Sinnoh", "Train to Lv.50+", "Victory Road", 48, 8),
        (16, "Elite Four + Champion", "Lv.55-65 recommended", "Pokemon League", 58, 8),
    ],
    "Unova": [
        (1, "Start in Nuvema Town", "Get starter from Prof. Juniper", "Nuvema Town", 5, 0),
        (2, "Route 1-2", "Catch early Pokemon, learn mechanics", "Route 1", 5, 0),
        (3, "Striaton City Gym - Cilan/Chili/Cress", "Type depends on starter. Counter it!", "Striaton City", 14, 0),
        (4, "Dreamyard", "Get the monkey that counters your weakness", "Striaton City", 12, 0),
        (5, "Nacrene City Gym - Lenora", "Normal type. Use Fighting", "Nacrene City", 20, 1),
        (6, "Pinwheel Forest", "Chase Team Plasma, recover the skull", "Pinwheel Forest", 18, 2),
        (7, "Castelia City Gym - Burgh", "Bug type. Use Fire/Rock/Flying", "Castelia City", 24, 2),
        (8, "Nimbasa City Gym - Elesa", "Electric type. Use Ground", "Nimbasa City", 27, 3),
        (9, "Driftveil City Gym - Clay", "Ground type. Use Water/Grass/Ice", "Driftveil City", 31, 4),
        (10, "Cold Storage", "Beat Team Plasma", "Driftveil City", 30, 4),
        (11, "Mistralton City Gym - Skyla", "Flying type. Use Rock/Electric/Ice", "Mistralton City", 35, 5),
        (12, "Chargestone Cave", "Navigate with Team Plasma encounters", "Chargestone Cave", 33, 5),
        (13, "Icirrus City Gym - Brycen", "Ice type. Use Fire/Fighting/Rock/Steel", "Icirrus City", 39, 6),
        (14, "Dragonspiral Tower", "Stop N from catching the legendary", "Dragonspiral Tower", 38, 7),
        (15, "Opelucid City Gym - Drayden", "Dragon type. Use Ice/Dragon", "Opelucid City", 43, 7),
        (16, "Route 10 + Victory Road", "Train to Lv.48+", "Victory Road", 48, 8),
        (17, "Elite Four + N + Ghetsis", "Lv.48-55 recommended, two boss fights!", "Pokemon League", 52, 8),
    ],
}

# Min badges mapping for common routes
# Format: {region: {route_name_pattern: min_badges}}
MIN_BADGES = {
    "Kanto": {
        "pallet": 0, "route 1": 0, "route 2": 0, "viridian city": 0, "viridian forest": 0,
        "pewter": 0, "route 3": 1, "route 4": 1, "mt. moon": 1,
        "cerulean": 1, "route 24": 2, "route 25": 2, "route 5": 2, "route 6": 2,
        "vermilion": 2, "route 9": 3, "route 10": 3, "rock tunnel": 3,
        "lavender": 3, "celadon": 3, "route 7": 3, "route 8": 3,
        "saffron": 4, "route 12": 4, "route 13": 4, "route 14": 4, "route 15": 4,
        "fuchsia": 5, "safari zone": 5, "route 16": 5, "route 17": 5, "route 18": 5,
        "route 19": 6, "route 20": 6, "cinnabar": 6, "seafoam": 6,
        "route 21": 7, "route 22": 7, "route 23": 8, "victory road": 8, "indigo": 8,
    },
    "Johto": {
        "new bark": 0, "route 29": 0, "route 30": 0, "cherrygrove": 0,
        "route 31": 0, "violet": 0, "sprout tower": 0,
        "route 32": 1, "union cave": 1, "route 33": 1, "azalea": 1,
        "ilex": 2, "route 34": 2, "goldenrod": 2,
        "route 35": 3, "national park": 3, "route 36": 3, "route 37": 3,
        "ecruteak": 3, "route 38": 4, "route 39": 4, "olivine": 4,
        "route 40": 4, "route 41": 4, "cianwood": 4,
        "mahogany": 6, "route 42": 6, "route 43": 6, "lake of rage": 6,
        "route 44": 7, "blackthorn": 7, "dragon": 7,
        "route 26": 8, "route 27": 8, "victory road": 8,
    },
    "Hoenn": {
        "littleroot": 0, "route 101": 0, "oldale": 0, "route 102": 0,
        "petalburg": 0, "route 104": 0, "petalburg woods": 0, "rustboro": 0,
        "route 116": 1, "rusturf": 1, "route 106": 1, "dewford": 1,
        "granite": 1, "route 107": 2, "route 108": 2, "route 109": 2, "slateport": 2,
        "route 110": 2, "mauville": 2, "route 103": 3,
        "route 111": 3, "route 112": 3, "lavaridge": 3, "route 117": 4,
        "route 118": 5, "route 119": 5, "fortree": 5,
        "route 120": 6, "route 121": 6, "lilycove": 6, "mt. pyre": 6,
        "route 122": 6, "route 123": 6, "mossdeep": 6,
        "route 124": 7, "route 125": 7, "route 126": 7, "route 127": 7,
        "route 128": 7, "sootopolis": 7,
        "route 129": 8, "route 130": 8, "route 131": 8, "victory road": 8,
    },
    "Sinnoh": {
        "twinleaf": 0, "route 201": 0, "sandgem": 0, "route 202": 0, "jubilife": 0,
        "route 203": 0, "oreburgh": 0,
        "route 204": 1, "route 205": 1, "eterna": 1,
        "route 206": 2, "route 207": 2, "route 208": 2, "hearthome": 2,
        "route 209": 3, "route 210": 3, "solaceon": 3, "route 215": 3, "veilstone": 3,
        "route 212": 3, "pastoria": 3,
        "route 213": 4, "route 214": 4,
        "route 218": 5, "canalave": 5, "route 216": 6, "route 217": 6, "snowpoint": 6,
        "route 222": 7, "sunyshore": 7,
        "route 223": 8, "victory road": 8,
    },
    "Unova": {
        "nuvema": 0, "route 1": 0, "accumula": 0, "route 2": 0, "striaton": 0,
        "dreamyard": 0, "route 3": 1, "nacrene": 1, "pinwheel": 2,
        "route 4": 2, "castelia": 2, "route 5": 3, "nimbasa": 3,
        "route 6": 4, "driftveil": 4, "cold storage": 4,
        "route 7": 5, "chargestone": 5, "mistralton": 5,
        "route 8": 6, "icirrus": 6, "dragonspiral": 7,
        "route 9": 7, "opelucid": 7,
        "route 10": 8, "victory road": 8,
    },
}


def main():
    print("=" * 60)
    print("PokeMMO Companion -- Progression Data Builder")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    # Add min_badges column if missing
    try:
        conn.execute("ALTER TABLE routes ADD COLUMN min_badges INTEGER DEFAULT 0")
        print("Added min_badges column to routes")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Build progression table
    print("\n=== Building progression data ===")
    conn.execute("DELETE FROM progression")

    total_steps = 0
    for region, steps in PROGRESSION.items():
        for step, title, desc, location, rec_level, badge_num in steps:
            conn.execute(
                """INSERT OR REPLACE INTO progression
                   (region, step, title, description, location, recommended_level, badge_number)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (region, step, title, desc, location, rec_level, badge_num)
            )
            total_steps += 1
        print(f"  {region}: {len(steps)} steps")

    conn.commit()
    print(f"  Total: {total_steps} progression steps")

    # Update routes with min_badges
    print("\n=== Updating route min_badges ===")
    updated = 0
    for region, routes_map in MIN_BADGES.items():
        for route_pattern, min_badges in routes_map.items():
            cursor = conn.execute(
                """UPDATE routes SET min_badges = ?
                   WHERE LOWER(name) LIKE ? AND LOWER(region) = LOWER(?)""",
                (min_badges, f"%{route_pattern}%", region)
            )
            updated += cursor.rowcount

    conn.commit()
    print(f"  Updated {updated} routes with min_badges")

    conn.close()
    print(f"\nProgression data built successfully!")


if __name__ == "__main__":
    main()
