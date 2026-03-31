"""Parse Pokemon Showdown team format into structured data.

Example input:
    Charizard @ Life Orb
    Ability: Blaze
    EVs: 252 SpA / 4 SpD / 252 Spe
    Timid Nature
    - Flamethrower
    - Air Slash
    - Dragon Pulse
    - Roost
"""
import re


def parse_showdown_team(text: str) -> list[dict]:
    """Parse a Showdown format team export into a list of Pokemon dicts."""
    pokemon_list = []
    current: dict | None = None

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            if current:
                pokemon_list.append(current)
                current = None
            continue

        if not current:
            # First line: "Name @ Item" or "Name (Nickname) @ Item" or just "Name"
            current = {"name": "", "item": "", "ability": "", "evs": {},
                       "ivs": {}, "nature": "", "moves": [], "level": 100}

            # Parse name and item
            match = re.match(r"^(.+?)(?:\s*@\s*(.+))?$", line)
            if match:
                name_part = match.group(1).strip()
                current["item"] = (match.group(2) or "").strip()

                # Handle nickname: "Nickname (Species)"
                nick_match = re.match(r"^(.+?)\s*\((.+?)\)\s*$", name_part)
                if nick_match:
                    current["nickname"] = nick_match.group(1).strip()
                    current["name"] = nick_match.group(2).strip()
                else:
                    current["name"] = name_part

                # Handle gender: (M) or (F) at the end
                current["name"] = re.sub(r"\s*\([MF]\)\s*$", "", current["name"]).strip()

        elif line.startswith("Ability:"):
            current["ability"] = line.split(":", 1)[1].strip()

        elif line.startswith("Level:"):
            try:
                current["level"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass

        elif line.startswith("EVs:"):
            ev_str = line.split(":", 1)[1].strip()
            for part in ev_str.split("/"):
                part = part.strip()
                match = re.match(r"(\d+)\s+(HP|Atk|Def|SpA|SpD|Spe)", part)
                if match:
                    stat_map = {"HP": "hp", "Atk": "attack", "Def": "defense",
                                "SpA": "sp_attack", "SpD": "sp_defense", "Spe": "speed"}
                    current["evs"][stat_map.get(match.group(2), match.group(2))] = int(match.group(1))

        elif line.startswith("IVs:"):
            iv_str = line.split(":", 1)[1].strip()
            for part in iv_str.split("/"):
                part = part.strip()
                match = re.match(r"(\d+)\s+(HP|Atk|Def|SpA|SpD|Spe)", part)
                if match:
                    stat_map = {"HP": "hp", "Atk": "attack", "Def": "defense",
                                "SpA": "sp_attack", "SpD": "sp_defense", "Spe": "speed"}
                    current["ivs"][stat_map.get(match.group(2), match.group(2))] = int(match.group(1))

        elif "Nature" in line:
            match = re.match(r"(\w+)\s+Nature", line)
            if match:
                current["nature"] = match.group(1)

        elif line.startswith("- "):
            current["moves"].append(line[2:].strip())

    # Don't forget the last Pokemon
    if current:
        pokemon_list.append(current)

    return pokemon_list


def format_team_summary(team: list[dict]) -> str:
    """Format a parsed team for display."""
    lines = []
    for i, p in enumerate(team, 1):
        item = f" @ {p['item']}" if p.get("item") else ""
        lines.append(f"{i}. {p['name']}{item}")
        if p.get("nature"):
            lines.append(f"   Nature: {p['nature']}")
        if p.get("evs"):
            ev_parts = [f"{v} {k}" for k, v in p["evs"].items()]
            lines.append(f"   EVs: {' / '.join(ev_parts)}")
        if p.get("moves"):
            lines.append(f"   Moves: {', '.join(p['moves'])}")
    return "\n".join(lines)


if __name__ == "__main__":
    test = """Charizard @ Life Orb
Ability: Blaze
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Flamethrower
- Air Slash
- Dragon Pulse
- Roost

Garchomp @ Choice Scarf
Ability: Rough Skin
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Earthquake
- Outrage
- Stone Edge
- Fire Fang"""

    team = parse_showdown_team(test)
    print(format_team_summary(team))
