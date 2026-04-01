"""FastAPI web server — serves the companion app UI + API."""
import random
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import sqlite3

from ..utils.config import DB_PATH, PROJECT_ROOT
from ..utils.logger import log

SPRITES_DIR = PROJECT_ROOT / "data" / "sprites"
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"

app = FastAPI(title="PokeMMO Companion", version="0.5.0")

# Mount static files (create dir if missing)
static_dir = WEB_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


from contextlib import contextmanager

@contextmanager
def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# === Pages ===

@app.get("/", response_class=HTMLResponse)
async def index():
    return (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


# === API ===

@app.get("/api/stats")
async def get_stats():
    with _db() as conn:
        pokemon_count = conn.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
        route_count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
        spawn_count = conn.execute("SELECT COUNT(*) FROM spawns").fetchone()[0]
        evo_count = conn.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0]
    return {
        "pokemon": pokemon_count, "routes": route_count,
        "spawns": spawn_count, "evolutions": evo_count,
        "sprites": len(list(SPRITES_DIR.glob("*.png"))) if SPRITES_DIR.exists() else 0,
    }


@app.get("/api/pokemon/all")
async def get_all_pokemon():
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, name, name_fr, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed FROM pokemon ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


_CONDITION_FR = {
    "Level": "Niveau", "Trade": "Echange", "Friendship": "Bonheur",
    "Water Stone": "Pierre Eau", "Fire Stone": "Pierre Feu",
    "Thunder Stone": "Pierre Foudre", "Leaf Stone": "Pierre Plante",
    "Moon Stone": "Pierre Lune", "Sun Stone": "Pierre Soleil",
    "Shiny Stone": "Pierre Eclat", "Dusk Stone": "Pierre Nuit",
    "Dawn Stone": "Pierre Aube", "Oval Stone": "Pierre Ovale",
    "King's Rock": "Roche Royale", "Metal Coat": "Peau Metal",
    "Dragon Scale": "Ecaille Draco", "Upgrade": "Ameliorator",
    "Dubious Disc": "CD Douteux", "Protector": "Protecteur",
    "Electirizer": "Electriseur", "Magmarizer": "Magmariseur",
    "Reaper Cloth": "Tissu Fauche", "Deep Sea Tooth": "Dent Ocean",
    "Deep Sea Scale": "Ecaille Ocean", "Prism Scale": "Bel Ecaille",
    "Use item": "Utiliser objet", "Happiness": "Bonheur",
    "at night": "la nuit", "during the day": "le jour",
    "male": "male", "female": "femelle",
    "with high Beauty": "avec haute Beaute",
    "in a Magnetic Field area": "dans une zone magnetique",
    "near a Mossy Rock": "pres Roche Mousse",
    "near an Icy Rock": "pres Roche Glacee",
    "knowing": "en connaissant", "with": "avec",
    "holding": "en tenant",
}

def _condition_fr(cond: str | None) -> str:
    """Translate evolution condition to French."""
    if not cond:
        return ""
    result = cond
    # Sort by length descending to replace longer phrases first
    for en, fr in sorted(_CONDITION_FR.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, fr)
    return result


def _strip_accents(s: str) -> str:
    """Remove accents for accent-insensitive search."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


@app.get("/api/pokemon/search/{query}")
async def search_pokemon(query: str):
    q_clean = _strip_accents(query.lower())
    with _db() as conn:
        # First try standard LIKE search
        rows = conn.execute(
            "SELECT id, name, name_fr, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed FROM pokemon WHERE (LOWER(name) LIKE LOWER(?) OR LOWER(name_fr) LIKE LOWER(?)) ORDER BY id LIMIT 30",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
        if not rows:
            # Fallback: accent-insensitive search
            all_rows = conn.execute(
                "SELECT id, name, name_fr, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed FROM pokemon ORDER BY id"
            ).fetchall()
            rows = [r for r in all_rows
                    if q_clean in _strip_accents((r["name"] or "").lower())
                    or q_clean in _strip_accents((r["name_fr"] or "").lower())][:30]
    return [dict(r) for r in rows]


@app.get("/api/pokemon/{pokemon_id}")
async def get_pokemon(pokemon_id: int):
    from fastapi.responses import JSONResponse
    with _db() as conn:
        row = conn.execute("SELECT * FROM pokemon WHERE id = ?", (pokemon_id,)).fetchone()
    if row:
        return dict(row)
    return JSONResponse(status_code=404, content={"error": "Pokemon non trouve"})


@app.get("/api/pokemon/{pokemon_id}/locations")
async def get_pokemon_locations(pokemon_id: int):
    with _db() as conn:
        pokemon = conn.execute("SELECT name FROM pokemon WHERE id = ?", (pokemon_id,)).fetchone()
        if not pokemon:
            return []
        rows = conn.execute(
            """SELECT r.name as route_name, r.region, s.method, s.rate, s.level_min, s.level_max
               FROM spawns s JOIN routes r ON s.route_id = r.id
               JOIN pokemon p ON s.pokemon_id = p.id
               WHERE LOWER(p.name) = LOWER(?) ORDER BY s.rate DESC LIMIT 15""",
            (dict(pokemon)["name"],)
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/pokemon/{pokemon_id}/evolutions")
async def get_evolutions(pokemon_id: int):
    with _db() as conn:
        # Walk back to base
        base_id = pokemon_id
        while True:
            row = conn.execute("SELECT from_pokemon_id FROM evolutions WHERE to_pokemon_id = ?", (base_id,)).fetchone()
            if row:
                base_id = row[0]
            else:
                break
        # Walk forward
        chain = []
        current = base_id
        p = conn.execute("SELECT id, name, name_fr, type1, type2 FROM pokemon WHERE id = ?", (current,)).fetchone()
        if p:
            chain.append({**dict(p), "condition": ""})
        while True:
            rows = conn.execute(
                """SELECT e.to_pokemon_id, e.condition, p.name, p.name_fr, p.type1, p.type2
                   FROM evolutions e JOIN pokemon p ON e.to_pokemon_id = p.id
                   WHERE e.from_pokemon_id = ?""", (current,)
            ).fetchall()
            if not rows:
                break
            for row in rows:
                r = dict(row)
                chain.append({"id": r["to_pokemon_id"], "name": r["name"],
                              "name_fr": r["name_fr"],
                              "type1": r["type1"], "type2": r["type2"],
                              "condition": _condition_fr(r["condition"])})
            current = dict(rows[0])["to_pokemon_id"]
    return chain


@app.get("/api/spawns/{route_name}")
async def get_spawns(route_name: str, region: str = ""):
    with _db() as conn:
        if region:
            rows = conn.execute(
                """SELECT s.*, p.name as pokemon_name, p.id as pokemon_id, p.type1, p.type2
                   FROM spawns s JOIN pokemon p ON s.pokemon_id = p.id
                   JOIN routes r ON s.route_id = r.id
                   WHERE LOWER(r.name) LIKE LOWER(?) AND LOWER(r.region) = LOWER(?)
                   ORDER BY s.rate DESC LIMIT 20""",
                (f"%{route_name}%", region)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT s.*, p.name as pokemon_name, p.id as pokemon_id, p.type1, p.type2, r.region
                   FROM spawns s JOIN pokemon p ON s.pokemon_id = p.id
                   JOIN routes r ON s.route_id = r.id
                   WHERE LOWER(r.name) LIKE LOWER(?)
                   ORDER BY s.rate DESC LIMIT 20""",
                (f"%{route_name}%",)
            ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/spotlight")
async def get_spotlight():
    """Random Pokemon for the spotlight."""
    pid = random.randint(1, 649)
    with _db() as conn:
        pokemon = conn.execute("SELECT * FROM pokemon WHERE id = ?", (pid,)).fetchone()
        locs = conn.execute(
            """SELECT r.name as route_name, r.region FROM spawns s
               JOIN routes r ON s.route_id = r.id WHERE s.pokemon_id = ?
               ORDER BY s.rate DESC LIMIT 1""", (pid,)
        ).fetchall()
    result = dict(pokemon) if pokemon else {}
    if locs:
        result["location"] = dict(locs[0])
    return result


@app.get("/api/type-chart")
async def get_type_chart():
    from ..utils.constants import TYPES, TYPE_CHART
    return {"types": TYPES, "chart": {f"{k[0]}_{k[1]}": v for k, v in TYPE_CHART.items()}}


@app.get("/api/damage")
async def calc_damage(attacker: str, defender: str, power: int = 80, move_type: str = "Normal"):
    """Calculate damage between two Pokemon."""
    with _db() as conn:
        atk = conn.execute("SELECT * FROM pokemon WHERE LOWER(name) LIKE LOWER(?)", (f"%{attacker}%",)).fetchone()
        dfn = conn.execute("SELECT * FROM pokemon WHERE LOWER(name) LIKE LOWER(?)", (f"%{defender}%",)).fetchone()
    if not atk or not dfn:
        return {"error": "Pokemon non trouve"}
    atk, dfn = dict(atk), dict(dfn)
    from ..tools.damage_calc import calc_damage as _calc, format_damage_result
    atk_stat = max(atk["attack"], atk["sp_attack"])
    def_stat = dfn["defense"] if atk["attack"] >= atk["sp_attack"] else dfn["sp_defense"]
    def_types = [dfn["type1"]]
    if dfn.get("type2"): def_types.append(dfn["type2"])
    atk_types = [atk["type1"]]
    if atk.get("type2"): atk_types.append(atk["type2"])
    result = _calc(50, power, move_type, atk_stat, def_stat, dfn["hp"]+60, def_types, atk_types)
    result["attacker"] = atk["name"]
    result["defender"] = dfn["name"]
    result["text"] = format_damage_result(result)
    return result


@app.get("/api/recommend-moves/{pokemon_id}")
async def recommend_moves(pokemon_id: int):
    with _db() as conn:
        p = conn.execute("SELECT * FROM pokemon WHERE id = ?", (pokemon_id,)).fetchone()
    if not p:
        return []
    p = dict(p)
    types = [p["type1"]]
    if p.get("type2"): types.append(p["type2"])
    from ..tools.move_recommender import recommend_moves as _rec
    return _rec(types, p["attack"], p["sp_attack"], p["speed"])


@app.get("/api/routes")
async def get_routes(region: str = ""):
    with _db() as conn:
        if region:
            rows = conn.execute("SELECT * FROM routes WHERE region = ? ORDER BY name", (region,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM routes ORDER BY region, name").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("name_fr"):
            d["display_name"] = d["name_fr"]
        else:
            d["display_name"] = d["name"]
        result.append(d)
    return result


@app.get("/api/routes/{route_id}/items")
async def get_route_items(route_id: int):
    with _db() as conn:
        rows = conn.execute("SELECT * FROM location_items WHERE route_id = ?", (route_id,)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/import-showdown")
async def import_showdown(body: dict):
    """Parse a Showdown format team."""
    from ..tools.showdown_parser import parse_showdown_team
    text = body.get("text", "")
    team = parse_showdown_team(text)
    # Enrich with DB data
    with _db() as conn:
        for p in team:
            row = conn.execute("SELECT * FROM pokemon WHERE LOWER(name) = LOWER(?)", (p["name"],)).fetchone()
            if row:
                db_data = dict(row)
                p["id"] = db_data["id"]
                p["type1"] = db_data["type1"]
                p["type2"] = db_data["type2"]
                p["hp"] = db_data["hp"]
                p["attack"] = db_data["attack"]
                p["defense"] = db_data["defense"]
                p["sp_attack"] = db_data["sp_attack"]
                p["sp_defense"] = db_data["sp_defense"]
                p["speed"] = db_data["speed"]
    return team


@app.get("/api/progression/{region}")
async def get_progression(region: str):
    """Get walkthrough steps for a region, preferring FR translations."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM progression WHERE LOWER(region) = LOWER(?) ORDER BY step",
            (region,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # Use FR fields if available
        if d.get("title_fr"):
            d["title"] = d["title_fr"]
        if d.get("description_fr"):
            d["description"] = d["description_fr"]
        if d.get("location_fr"):
            d["location"] = d["location_fr"]
        result.append(d)
    return result


@app.get("/api/game-status")
async def game_status():
    """Check if PokeMMO is running and return window info."""
    from ..capture.screen_capture import find_window, get_window_rect, get_window_title
    hwnd = find_window("PokeMMO")
    if hwnd and hwnd != 0:
        rect = get_window_rect(hwnd)
        title = get_window_title(hwnd)
        return {
            "connected": True,
            "title": title,
            "window": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3],
                        "width": rect[2]-rect[0], "height": rect[3]-rect[1]} if rect else None
        }
    return {"connected": False, "title": "", "window": None}


@app.get("/api/ocr/status")
async def ocr_status():
    """Check OCR availability and show current ROI settings."""
    try:
        from ..detection.ocr_engine import init_tesseract
        tesseract_ok = init_tesseract()
    except ImportError:
        tesseract_ok = False
    try:
        from ..detection.route_detector import RouteDetector
        rd = RouteDetector()
        route_roi = rd._route_roi
    except ImportError:
        route_roi = {"x_ratio": 0.01, "y_ratio": 0.01, "w_ratio": 0.18, "h_ratio": 0.04}
    return {
        "tesseract_available": tesseract_ok,
        "route_roi": route_roi,
        "ocr_regions": [
            {"name": "Route Name", "x": route_roi["x_ratio"], "y": route_roi["y_ratio"],
             "w": route_roi["w_ratio"], "h": route_roi["h_ratio"]},
            {"name": "Opponent Name", "x": 0.52, "y": 0.05, "w": 0.35, "h": 0.04},
            {"name": "Opponent Level", "x": 0.80, "y": 0.05, "w": 0.12, "h": 0.04},
        ]
    }


@app.post("/api/ocr/calibrate")
async def calibrate_ocr(body: dict):
    """Update OCR ROI positions from the web interface."""
    from ..detection.route_detector import RouteDetector
    rd = RouteDetector()
    if "route_roi" in body:
        roi = body["route_roi"]
        rd.set_roi(
            float(roi.get("x", rd._route_roi["x_ratio"])),
            float(roi.get("y", rd._route_roi["y_ratio"])),
            float(roi.get("w", rd._route_roi["w_ratio"])),
            float(roi.get("h", rd._route_roi["h_ratio"])),
        )
        return {"status": "ok", "roi": rd._route_roi}
    return {"status": "no changes"}


@app.get("/api/ocr/capture")
async def ocr_capture():
    """Capture a screenshot and try OCR on the route name region."""
    from ..capture.screen_capture import ScreenCapture
    from ..detection.ocr_engine import read_route_name, init_tesseract
    import base64, cv2, numpy as np

    if not init_tesseract():
        return {"error": "Tesseract non installe"}

    cap = ScreenCapture()
    if not cap.initialize():
        return {"error": "Fenetre PokeMMO non trouvee"}

    frame = cap.capture_full()
    cap.cleanup()

    if frame is None:
        return {"error": "Capture echouee"}

    h, w = frame.shape[:2]
    # Try OCR on route region
    roi_x = int(0.01 * w)
    roi_y = int(0.01 * h)
    roi_w = int(0.18 * w)
    roi_h = int(0.04 * h)
    route_region = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]

    text = ""
    if route_region.size > 0:
        text = read_route_name(route_region)

    # Encode a small preview as base64
    preview = cv2.resize(frame, (640, 360))
    # Draw ROI rectangle
    cv2.rectangle(preview,
                  (int(0.01*640), int(0.01*360)),
                  (int(0.19*640), int(0.05*360)),
                  (0, 255, 0), 2)
    _, buf = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 70])
    img_b64 = base64.b64encode(buf).decode()

    return {
        "text": text,
        "window_size": f"{w}x{h}",
        "preview": f"data:image/jpeg;base64,{img_b64}"
    }


@app.post("/api/sound/{sound_type}")
async def play_sound(sound_type: str):
    """Play a notification sound (shiny, encounter, notification)."""
    from ..utils.sound import play_shiny_alert, play_encounter_beep, play_notification
    sounds = {
        "shiny": play_shiny_alert,
        "encounter": play_encounter_beep,
        "notification": play_notification,
    }
    fn = sounds.get(sound_type)
    if fn:
        fn()
        return {"status": "playing", "sound": sound_type}
    return {"status": "unknown sound"}


@app.get("/api/hordes")
async def get_hordes(region: str = "", pokemon: str = "", poke_type: str = ""):
    """Get horde encounter spots, optionally filtered by region/pokemon/type."""
    with _db() as conn:
        query = """SELECT p.id as pokemon_id, p.name, p.type1, p.type2,
                   r.name as route_name, r.region, s.rate, s.level_min, s.level_max
                   FROM spawns s
                   JOIN pokemon p ON s.pokemon_id = p.id
                   JOIN routes r ON s.route_id = r.id
                   WHERE s.method = 'horde'"""
        params = []
        if region:
            query += " AND LOWER(r.region) = LOWER(?)"
            params.append(region)
        if pokemon:
            query += " AND LOWER(p.name) LIKE LOWER(?)"
            params.append(f"%{pokemon}%")
        if poke_type:
            query += " AND (LOWER(p.type1) = LOWER(?) OR LOWER(p.type2) = LOWER(?))"
            params.extend([poke_type, poke_type])
        query += " ORDER BY r.region, r.name, p.name"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/hordes/summary")
async def horde_summary():
    """Get horde stats per region."""
    with _db() as conn:
        rows = conn.execute("""
            SELECT r.region, COUNT(DISTINCT p.id) as pokemon_count,
                   COUNT(DISTINCT r.id) as route_count
            FROM spawns s
            JOIN pokemon p ON s.pokemon_id = p.id
            JOIN routes r ON s.route_id = r.id
            WHERE s.method = 'horde'
            GROUP BY r.region ORDER BY r.region
        """).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/abilities/translations")
async def get_ability_translations():
    """Get EN->FR ability name translations."""
    import json as _json
    tr_path = PROJECT_ROOT / "data" / "ability_fr.json"
    if tr_path.exists():
        return _json.loads(tr_path.read_text(encoding="utf-8"))
    return {}


@app.get("/api/abilities")
async def get_abilities(query: str = ""):
    """List all abilities with pokemon counts, optionally filtered."""
    with _db() as conn:
        # Get all unique abilities with counts
        rows = conn.execute("""
            SELECT ability, is_hidden, COUNT(*) as count, GROUP_CONCAT(name, ', ') as pokemon_names
            FROM (
                SELECT ability1 as ability, 0 as is_hidden, name FROM pokemon WHERE ability1 IS NOT NULL
                UNION ALL
                SELECT ability2, 0, name FROM pokemon WHERE ability2 IS NOT NULL
                UNION ALL
                SELECT hidden_ability, 1, name FROM pokemon WHERE hidden_ability IS NOT NULL
            )
            WHERE ability IS NOT NULL AND ability != ''
            GROUP BY ability
            ORDER BY ability
        """).fetchall()
    result = [dict(r) for r in rows]
    if query:
        q = query.lower()
        result = [r for r in result if q in r["ability"].lower() or q in r.get("pokemon_names", "").lower()]
    return result


@app.get("/api/abilities/{ability_name}")
async def get_ability_pokemon(ability_name: str):
    """Get all Pokemon with a specific ability."""
    with _db() as conn:
        rows = conn.execute("""
            SELECT id, name, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed,
                   ability1, ability2, hidden_ability
            FROM pokemon
            WHERE LOWER(ability1) = LOWER(?) OR LOWER(ability2) = LOWER(?) OR LOWER(hidden_ability) = LOWER(?)
            ORDER BY id
        """, (ability_name, ability_name, ability_name)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ability_type"] = "hidden" if d["hidden_ability"] and d["hidden_ability"].lower() == ability_name.lower() else "normal"
        result.append(d)
    return result


@app.get("/api/pokemon/{pokemon_id}/moves")
async def get_pokemon_moves(pokemon_id: int, method: str = ""):
    """Get moves a Pokemon can learn, optionally filtered by method."""
    with _db() as conn:
        query = """SELECT m.id, m.name, m.name_fr, m.type, m.power, m.accuracy, m.pp, m.category,
                   pm.method, pm.level
                   FROM pokemon_moves pm JOIN moves m ON pm.move_id = m.id
                   WHERE pm.pokemon_id = ?"""
        params: list = [pokemon_id]
        if method:
            query += " AND pm.method = ?"
            params.append(method)
        query += " ORDER BY pm.method, pm.level, m.name"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/ev-spots/{stat}")
async def get_ev_spots(stat: str, region: str = "", method: str = ""):
    """Get best EV training spots for a given stat. Prioritizes horde spots."""
    stat_col = {
        "hp": "ev_hp", "attack": "ev_attack", "defense": "ev_defense",
        "sp_attack": "ev_sp_attack", "sp_defense": "ev_sp_defense", "speed": "ev_speed"
    }.get(stat)
    if not stat_col:
        return {"error": "Stat invalide. Utilise: hp, attack, defense, sp_attack, sp_defense, speed"}
    with _db() as conn:
        query = f"""SELECT p.id as pokemon_id, p.name, p.type1, p.type2,
                   p.ev_hp, p.ev_attack, p.ev_defense, p.ev_sp_attack, p.ev_sp_defense, p.ev_speed,
                   r.name as route_name, r.region, s.method, s.rate, s.level_min, s.level_max
                   FROM spawns s
                   JOIN pokemon p ON s.pokemon_id = p.id
                   JOIN routes r ON s.route_id = r.id
                   WHERE p.{stat_col} >= 1"""
        params = []
        if region:
            query += " AND LOWER(r.region) = LOWER(?)"
            params.append(region)
        if method:
            query += " AND s.method = ?"
            params.append(method)
        query += f" ORDER BY p.{stat_col} DESC, CASE WHEN s.method='horde' THEN 0 ELSE 1 END, s.rate DESC"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/ocr/regions")
async def save_ocr_regions(body: dict):
    """Save OCR region config to a JSON file for the overlay to use."""
    import json as _json
    config_path = PROJECT_ROOT / "data" / "ocr_regions.json"
    config_path.write_text(_json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "path": str(config_path)}


@app.get("/api/ocr/regions")
async def load_ocr_regions():
    """Load saved OCR region config."""
    import json as _json
    config_path = PROJECT_ROOT / "data" / "ocr_regions.json"
    if config_path.exists():
        return _json.loads(config_path.read_text(encoding="utf-8"))
    # Default regions for standard PokeMMO 1280x720
    return {
        "regions": [
            {"id": "route_name", "label": "Nom de Route", "x": 1, "y": 1, "w": 18, "h": 4, "color": "#00e5ff"},
            {"id": "opponent_name", "label": "Nom Adversaire", "x": 52, "y": 5, "w": 35, "h": 4, "color": "#ff4081"},
            {"id": "opponent_level", "label": "Niveau Adversaire", "x": 80, "y": 5, "w": 12, "h": 4, "color": "#ffd740"},
            {"id": "player_hp", "label": "HP Joueur", "x": 55, "y": 75, "w": 20, "h": 3, "color": "#69f0ae"},
            {"id": "opponent_hp", "label": "HP Adversaire", "x": 55, "y": 12, "w": 20, "h": 3, "color": "#ff6e40"},
        ],
        "resolution": "1280x720"
    }


@app.post("/api/ocr/test-region")
async def test_ocr_region(body: dict):
    """Test OCR on a specific region of an uploaded image."""
    import base64
    try:
        import cv2
        import numpy as np
        from ..detection.ocr_engine import init_tesseract
        if not init_tesseract():
            return {"text": "(Tesseract non installe)", "available": False}

        img_data = body.get("image", "")
        if "base64," in img_data:
            img_data = img_data.split("base64,")[1]
        img_bytes = base64.b64decode(img_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"text": "(Image invalide)", "available": True}

        h, w = img.shape[:2]
        x = int(body.get("x", 0) / 100 * w)
        y = int(body.get("y", 0) / 100 * h)
        rw = int(body.get("w", 10) / 100 * w)
        rh = int(body.get("h", 4) / 100 * h)
        crop = img[y:y+rh, x:x+rw]

        if crop.size == 0:
            return {"text": "(Region vide)", "available": True}

        from ..detection.ocr_engine import read_route_name
        text = read_route_name(crop)
        return {"text": text or "(rien detecte)", "available": True}
    except ImportError:
        return {"text": "(OpenCV/Tesseract non installe — testable sur PC avec PokeMMO)", "available": False}
    except Exception as e:
        return {"text": f"(Erreur: {str(e)[:80]})", "available": False}


@app.post("/api/ocr/analyze-stats")
async def analyze_stats_screen(body: dict):
    """Analyze a full Pokemon stats screen — extract IVs, EVs, nature, icons.

    Expects base64 image of the PokeMMO PC/summary screen.
    """
    import base64
    try:
        import cv2
        import numpy as np
        from ..detection.ocr_engine import init_tesseract, read_stats_screen
        if not init_tesseract():
            return {"error": "Tesseract non installe", "available": False}

        img_data = body.get("image", "")
        if "base64," in img_data:
            img_data = img_data.split("base64,")[1]
        img_bytes = base64.b64decode(img_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Image invalide", "available": True}

        result = read_stats_screen(img)
        result["available"] = True
        return result
    except ImportError:
        return {"error": "OpenCV/Tesseract non installe", "available": False}
    except Exception as e:
        return {"error": str(e)[:100], "available": False}


@app.post("/api/ocr/detect-icons")
async def detect_icons(body: dict):
    """Detect shiny/alpha/hidden ability icons in a screenshot."""
    import base64
    try:
        import cv2
        import numpy as np
        from ..detection.ocr_engine import detect_special_icons

        img_data = body.get("image", "")
        if "base64," in img_data:
            img_data = img_data.split("base64,")[1]
        img_bytes = base64.b64decode(img_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Image invalide"}

        return detect_special_icons(img)
    except ImportError:
        return {"error": "OpenCV non installe"}
    except Exception as e:
        return {"error": str(e)[:100]}


@app.get("/sprite/{pokemon_id}")
async def get_sprite(pokemon_id: int):
    sprite_path = SPRITES_DIR / f"{pokemon_id}.png"
    if sprite_path.exists():
        return FileResponse(str(sprite_path))
    return FileResponse(str(SPRITES_DIR / "1.png"))  # Fallback to Bulbasaur
