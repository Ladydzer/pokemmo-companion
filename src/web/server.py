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
            "SELECT id, name, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed FROM pokemon ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/pokemon/search/{query}")
async def search_pokemon(query: str):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, name, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed FROM pokemon WHERE LOWER(name) LIKE LOWER(?) ORDER BY id LIMIT 30",
            (f"%{query}%",)
        ).fetchall()
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
        p = conn.execute("SELECT id, name, type1, type2 FROM pokemon WHERE id = ?", (current,)).fetchone()
        if p:
            chain.append({**dict(p), "condition": ""})
        while True:
            row = conn.execute(
                """SELECT e.to_pokemon_id, e.condition, p.name, p.type1, p.type2
                   FROM evolutions e JOIN pokemon p ON e.to_pokemon_id = p.id
                   WHERE e.from_pokemon_id = ?""", (current,)
            ).fetchone()
            if row:
                r = dict(row)
                chain.append({"id": r["to_pokemon_id"], "name": r["name"],
                              "type1": r["type1"], "type2": r["type2"], "condition": r["condition"]})
                current = r["to_pokemon_id"]
            else:
                break
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
        return {"error": "Pokemon not found"}
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
    return [dict(r) for r in rows]


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
    """Get walkthrough steps for a region."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM progression WHERE LOWER(region) = LOWER(?) ORDER BY step",
            (region,)
        ).fetchall()
    return [dict(r) for r in rows]


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
    from ..detection.ocr_engine import init_tesseract
    tesseract_ok = init_tesseract()
    from ..detection.route_detector import RouteDetector
    rd = RouteDetector()
    return {
        "tesseract_available": tesseract_ok,
        "route_roi": rd._route_roi,
        "ocr_regions": [
            {"name": "Route Name", "x": rd._route_roi["x_ratio"], "y": rd._route_roi["y_ratio"],
             "w": rd._route_roi["w_ratio"], "h": rd._route_roi["h_ratio"]},
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


@app.get("/sprite/{pokemon_id}")
async def get_sprite(pokemon_id: int):
    sprite_path = SPRITES_DIR / f"{pokemon_id}.png"
    if sprite_path.exists():
        return FileResponse(str(sprite_path))
    return FileResponse(str(SPRITES_DIR / "1.png"))  # Fallback to Bulbasaur
