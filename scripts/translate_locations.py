"""Translate route names and progression text to French."""
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pokemon.db')

# Pokemon city/location name translations (EN -> FR)
LOCATION_FR = {
    # Kanto
    "Pallet Town": "Bourg Palette",
    "Viridian City": "Jadielle",
    "Viridian Forest": "Forêt de Jade",
    "Pewter City": "Argenta",
    "Mt. Moon": "Mont Sélénite",
    "Cerulean City": "Azuria",
    "Cerulean Cave": "Grotte Azurée",
    "Vermilion City": "Carmin sur Mer",
    "Lavender Town": "Lavanville",
    "Pokemon Tower": "Tour Pokémon",
    "Celadon City": "Céladopole",
    "Saffron City": "Safrania",
    "Fuchsia City": "Parmanie",
    "Cinnabar Island": "Cramois'Île",
    "Seafoam Islands": "Îles Écume",
    "Indigo Plateau": "Plateau Indigo",
    "Power Plant": "Centrale",
    "Rock Tunnel": "Grotte",
    "Safari Zone": "Parc Safari",
    "Silph Co.": "Sylphe SARL",
    "S.S. Anne": "Océane",
    "Pokemon Mansion": "Manoir Pokémon",
    "Victory Road": "Route Victoire",
    "Diglett'S Cave": "Grotte Taupiqueur",
    "Pokemon League": "Ligue Pokémon",
    # Johto
    "New Bark Town": "Bourg Geon",
    "Cherrygrove City": "Ville Griotte",
    "Violet City": "Mauville",
    "Azalea Town": "Écorcia",
    "Goldenrod City": "Doublonville",
    "Ecruteak City": "Rosalia",
    "Olivine City": "Oliville",
    "Cianwood City": "Irisia",
    "Mahogany Town": "Acajou",
    "Blackthorn City": "Ébènelle",
    "Lake of Rage": "Lac Colère",
    "Ice Path": "Chemin de Glace",
    "Dragon'S Den": "Antre du Dragon",
    "Bell Tower": "Tour Ferraille",
    "Burned Tower": "Tour Cendrée",
    "Whirl Islands": "Îles Tourb.",
    "Ilex Forest": "Bois aux Chênes",
    "Union Cave": "Grotte Lierre",
    "Slowpoke Well": "Puits Ramoloss",
    "Sprout Tower": "Tour Chétiflor",
    "National Park": "Parc Naturel",
    "Ruins of Alph": "Ruines d'Alpha",
    "Mt. Mortar": "Mont Creuset",
    "Mt. Silver": "Mont Argenté",
    # Hoenn
    "Littleroot Town": "Bourg-en-Vol",
    "Oldale Town": "Rosyères",
    "Petalburg City": "Clémenti-Ville",
    "Rustboro City": "Mérouville",
    "Dewford Town": "Mysdibior",
    "Slateport City": "Poivressel",
    "Mauville City": "Lavandia",
    "Verdanturf Town": "Vergazon",
    "Fallarbor Town": "Autequia",
    "Lavaridge Town": "Vermilava",
    "Fortree City": "Cimetronelle",
    "Lilycove City": "Nénucrique",
    "Mossdeep City": "Algatia",
    "Sootopolis City": "Atalanopolis",
    "Pacifidlog Town": "Pacifiville",
    "Ever Grande City": "Éternara",
    "Meteor Falls": "Cascade Météore",
    "Granite Cave": "Grotte Granite",
    "Fiery Path": "Chemin Ardent",
    "Jagged Pass": "Sentier Sinueux",
    "Mt. Chimney": "Mont Chimney",
    "Desert Underpass": "Passage Désert",
    "Mirage Tower": "Tour Mirage",
    "Abandoned Ship": "Épave",
    "New Mauville": "Nouveau Lavandia",
    "Shoal Cave": "Grotte Tréfonds",
    "Sky Pillar": "Pilier Céleste",
    "Cave Of Origin": "Grotte Origine",
    "Mt. Pyre": "Mont Mémoria",
    "Aqua Hideout": "Repaire Aqua",
    "Magma Hideout": "Repaire Magma",
    "Artisan Cave": "Grotte Artisan",
    "Scorched Slab": "Dalle Brûlante",
    "Battle Frontier": "Zone de Combat",
    # Sinnoh
    "Twinleaf Town": "Bonaugure",
    "Sandgem Town": "Littorella",
    "Jubilife City": "Féli-Cité",
    "Oreburgh City": "Charbourg",
    "Floaroma Town": "Floraville",
    "Eterna City": "Vestigion",
    "Eterna Forest": "Forêt de Vestigion",
    "Hearthome City": "Unionpolis",
    "Solaceon Town": "Bonville",
    "Veilstone City": "Voilaroc",
    "Pastoria City": "Verchamps",
    "Celestic Town": "Célestia",
    "Canalave City": "Joliberges",
    "Snowpoint City": "Frimapic",
    "Sunyshore City": "Rivamar",
    "Fight Area": "Zone Combat",
    "Survival Area": "Zone Survie",
    "Resort Area": "Zone Détente",
    "Oreburgh Mine": "Mine de Charbourg",
    "Oreburgh Gate": "Entrée Charbourg",
    "Valley Windworks": "Éolienne Vallée",
    "Wayward Cave": "Grotte Revêche",
    "Mt. Coronet": "Mont Couronné",
    "Lost Tower": "Tour Perdue",
    "Iron Island": "Île de Fer",
    "Old Chateau": "Vieux Château",
    "Lake Verity": "Lac Vérité",
    "Lake Valor": "Lac Courage",
    "Lake Acuity": "Lac Savoir",
    "Stark Mountain": "Mont Abrupt",
    "Snowpoint Temple": "Temple Frimapic",
    "Turnback Cave": "Grotte Retour",
    "Spring Path": "Chemin Source",
    "Sendoff Spring": "Source Adieu",
    # Unova
    "Nuvema Town": "Renouet",
    "Accumula Town": "Arabelle",
    "Striaton City": "Ogoesse",
    "Nacrene City": "Maillard",
    "Castelia City": "Volucité",
    "Nimbasa City": "Méanville",
    "Driftveil City": "Port Yoneuve",
    "Mistralton City": "Parsemille",
    "Icirrus City": "Flocombe",
    "Opelucid City": "Janusia",
    "Lacunosa Town": "Entrelasque",
    "Undella Town": "Undella",
    "Black City": "Ville Noire",
    "White Forest": "Forêt Blanche",
    "Anville Town": "Rotombourg",
    "Aspertia City": "PavPokemon",
    "Virbank City": "Virbank",
    "Humilau City": "Papeloa",
    "Lentimas Town": "Escourbes",
    "Floccesy Town": "Méré",
    "Pinwheel Forest": "Bois des Illusions",
    "Desert Resort": "Désert Délassant",
    "Relic Castle": "Château Enfoui",
    "Chargestone Cave": "Grotte Électrolithe",
    "Twist Mountain": "Mont Foré",
    "Dragonspiral Tower": "Tour Dragospire",
    "Challenger'S Cave": "Grotte Cyclopéenne",
    "Giant Chasm": "Faille Géante",
    "Wellspring Cave": "Grotte Parsemille",
    "Mistralton Cave": "Grotte Parsemille",
    "Clay Tunnel": "Tunnel Yoneuve",
    "Reversal Mountain": "Mont Revers",
    "Strange House": "Maison Étrange",
    "Victory Road": "Route Victoire",
    "Abundant Shrine": "Sanctuaire Abondance",
    "Celestial Tower": "Tour Céleste",
    "Moor Of Icirrus": "Marais Flocombe",
    "P2 Laboratory": "Labo P2",
    "Lostlorn Forest": "Forêt d'Empoigne",
    "Undella Bay": "Baie Ondule",
    "Seaside Cave": "Grotte Littorale",
    "Plasma Frigate": "Frégate Plasma",
}

# Gym leader translations
LEADER_FR = {
    "Brock": "Pierre", "Misty": "Ondine", "Lt. Surge": "Major Bob",
    "Erika": "Erika", "Koga": "Koga", "Sabrina": "Morgane",
    "Blaine": "Auguste", "Giovanni": "Giovanni",
    "Falkner": "Albert", "Bugsy": "Hector", "Whitney": "Blanche",
    "Morty": "Mortimer", "Chuck": "Chuck", "Jasmine": "Jasmine",
    "Pryce": "Frédo", "Clair": "Sandra",
    "Roxanne": "Roxanne", "Brawly": "Bastien", "Wattson": "Voltère",
    "Flannery": "Adriane", "Norman": "Norman", "Winona": "Alizée",
    "Tate and Liza": "Lévy et Tatia", "Wallace": "Marc",
    "Roark": "Pierrick", "Gardenia": "Flo", "Maylene": "Mélina",
    "Crasher Wake": "Lovis", "Fantina": "Kiméra", "Byron": "Charles",
    "Candice": "Gladys", "Volkner": "Tanguy",
    "Cilan": "Rachid", "Lenora": "Aloé", "Burgh": "Artie",
    "Elesa": "Inezia", "Clay": "Bardane", "Skyla": "Carolina",
    "Brycen": "Zhu", "Drayden": "Watson", "Iris": "Iris",
}


def translate_text(text: str) -> str:
    """Translate a text string replacing known location/leader names."""
    result = text
    # Sort by length (longest first) to avoid partial replacements
    for en, fr in sorted(LOCATION_FR.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, fr)
    for en, fr in sorted(LEADER_FR.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, fr)
    # Common game terms
    replacements = {
        "Get your starter from Prof. Oak": "Reçois ton starter du Prof. Chen",
        "Head north": "Va vers le nord",
        "catch Pidgey/Rattata": "attrape Roucool/Rattata",
        "Get Pokedex from Oak": "Reçois le Pokédex du Prof. Chen",
        "buy Poke Balls": "achète des Poké Balls",
        "Catch Pikachu (rare!)": "Attrape Pikachu (rare !)",
        "train to Lv.": "entraîne-toi au Niv.",
        "Rock type": "Type Roche",
        "Water type": "Type Eau",
        "Electric type": "Type Électrik",
        "Grass type": "Type Plante",
        "Psychic type": "Type Psy",
        "Poison type": "Type Poison",
        "Fire type": "Type Feu",
        "Ice type": "Type Glace",
        "Ground type": "Type Sol",
        "Fighting type": "Type Combat",
        "Normal type": "Type Normal",
        "Ghost type": "Type Spectre",
        "Dragon type": "Type Dragon",
        "Dark type": "Type Ténèbres",
        "Steel type": "Type Acier",
        "Flying type": "Type Vol",
        "Bug type": "Type Insecte",
        "Use Water/Grass/Fighting": "Utilise Eau/Plante/Combat",
        "Use Ground/Water/Grass": "Utilise Sol/Eau/Plante",
        "Use Ground/Water": "Utilise Sol/Eau",
        "Use Fighting/Ground": "Utilise Combat/Sol",
        "Gym": "Arène",
        "gym": "arène",
        "Elite Four": "Conseil 4",
        "Champion": "Maître",
        "Badge": "Badge",
        "Surf": "Surf",
        "Fly": "Vol",
        "Cut": "Coupe",
        "Strength": "Force",
        "Flash": "Flash",
        "Waterfall": "Cascade",
        "Rock Smash": "Éclate-Roc",
        "Rock Climb": "Escalade",
        "Defog": "Anti-Brume",
        "HM": "CS",
        "TM": "CT",
        "Defeat": "Bats",
        "defeat": "bats",
        "Train": "Entraîne-toi",
        "train": "entraîne-toi",
        "Head to": "Va à",
        "head to": "va à",
        "Go to": "Va à",
        "go to": "va à",
        "Explore": "Explore",
        "Level up to": "Monte au Niv.",
    }
    for en, fr in replacements.items():
        result = result.replace(en, fr)
    return result


def main():
    conn = sqlite3.connect(DB_PATH)

    # Add name_fr column to routes if not exists
    cols = [r[1] for r in conn.execute('PRAGMA table_info(routes)').fetchall()]
    if 'name_fr' not in cols:
        conn.execute('ALTER TABLE routes ADD COLUMN name_fr TEXT')
        print('Added name_fr column to routes table')

    # Translate route names
    routes = conn.execute('SELECT id, name FROM routes').fetchall()
    translated_routes = 0
    for rid, name in routes:
        fr_name = LOCATION_FR.get(name)
        if not fr_name:
            # Try partial match
            for en, fr in LOCATION_FR.items():
                if en.lower() == name.lower():
                    fr_name = fr
                    break
        if fr_name:
            conn.execute('UPDATE routes SET name_fr = ? WHERE id = ?', (fr_name, rid))
            translated_routes += 1

    print(f'Routes translated: {translated_routes}/{len(routes)}')

    # Translate progression
    prog_cols = [r[1] for r in conn.execute('PRAGMA table_info(progression)').fetchall()]
    if 'title_fr' not in prog_cols:
        conn.execute('ALTER TABLE progression ADD COLUMN title_fr TEXT')
        conn.execute('ALTER TABLE progression ADD COLUMN description_fr TEXT')
        conn.execute('ALTER TABLE progression ADD COLUMN location_fr TEXT')
        print('Added FR columns to progression table')

    steps = conn.execute('SELECT id, title, description, location FROM progression').fetchall()
    for sid, title, desc, loc in steps:
        title_fr = translate_text(title)
        desc_fr = translate_text(desc) if desc else ''
        loc_fr = LOCATION_FR.get(loc, loc) if loc else ''
        conn.execute('UPDATE progression SET title_fr = ?, description_fr = ?, location_fr = ? WHERE id = ?',
                     (title_fr, desc_fr, loc_fr, sid))

    conn.commit()

    # Verify
    print('\nKanto progression (FR):')
    rows = conn.execute('SELECT step, title, title_fr, description_fr, location_fr FROM progression WHERE region = "Kanto" ORDER BY step LIMIT 8').fetchall()
    for r in rows:
        print(f'  {r[0]}. {r[2]} — {r[3]} (📍 {r[4]})')

    print('\nSample route translations:')
    rows2 = conn.execute('SELECT name, name_fr FROM routes WHERE name_fr IS NOT NULL ORDER BY region, name LIMIT 10').fetchall()
    for r in rows2:
        print(f'  {r[0]} → {r[1]}')

    fr_routes = conn.execute('SELECT COUNT(*) FROM routes WHERE name_fr IS NOT NULL').fetchone()[0]
    print(f'\nRoutes with FR names: {fr_routes}/{len(routes)}')

    conn.close()


if __name__ == '__main__':
    main()
