"""Battle detection — identifies opponent Pokemon and provides type info."""
import time
import numpy as np
import cv2

from .ocr_engine import (read_pokemon_name, read_level, preprocess_light_text,
                         detect_special_icons, fuzzy_match_name)
from ..data.type_chart import get_battle_summary, format_battle_summary
from ..utils.logger import log


class BattleDetector:
    """Detects battle state and reads opponent Pokemon info.

    In PokeMMO battle screen:
    - Opponent Pokemon name: top area (roughly 10-20% from top, 55-85% from left)
    - Opponent HP bar: just below the name
    - Opponent level: near the name ("Lv.XX")
    - Player Pokemon: bottom area
    """

    def __init__(self, db=None):
        self.db = db  # Database instance for Pokemon lookups
        self.current_opponent: str = ""
        self.current_opponent_level: int | None = None
        self.current_opponent_types: list[str] = []
        self._last_battle_info: dict | None = None

        # Anti-flipflop: require consecutive consistent reads before changing
        self._consecutive_reads: dict[str, int] = {}
        self._min_consecutive: int = 3  # 3 consistent reads to confirm
        self._last_change_time: float = 0.0
        self._change_cooldown: float = 1.5  # seconds between opponent changes
        self._no_detection_count: int = 0
        self._exit_threshold: int = 5  # frames without detection to exit battle

        # ROI ratios for opponent info (relative to game window)
        # Calibrated from ladyd_'s combat screenshot: opponent name is
        # top-center area, roughly "Geodite Niv. 38"
        self._opponent_name_roi = {
            "x_ratio": 0.05, "y_ratio": 0.06,
            "w_ratio": 0.25, "h_ratio": 0.05,
        }
        self._opponent_level_roi = {
            "x_ratio": 0.25, "y_ratio": 0.06,
            "w_ratio": 0.10, "h_ratio": 0.05,
        }

    def set_name_roi(self, x_ratio: float, y_ratio: float,
                     w_ratio: float, h_ratio: float) -> None:
        """Set the region of interest for opponent name."""
        self._opponent_name_roi = {
            "x_ratio": x_ratio, "y_ratio": y_ratio,
            "w_ratio": w_ratio, "h_ratio": h_ratio,
        }

    def detect_opponent(self, frame: np.ndarray) -> dict | None:
        """Detect opponent Pokemon from battle screen.

        Anti-flipflop: requires 3 consecutive consistent reads + 1.5s cooldown
        before reporting a new opponent. Exits battle after 5 frames with no detection.
        Returns battle info dict or None if detection failed.
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]

        # Extract opponent name region
        roi = self._opponent_name_roi
        x = int(roi["x_ratio"] * w)
        y = int(roi["y_ratio"] * h)
        rw = int(roi["w_ratio"] * w)
        rh = int(roi["h_ratio"] * h)

        name_region = frame[y:y + rh, x:x + rw]
        if name_region.size == 0:
            self._no_detection_count += 1
            if self._no_detection_count >= self._exit_threshold:
                return None  # Battle ended (hysteresis exit)
            return self._last_battle_info

        # Read opponent name
        name = read_pokemon_name(name_region)
        if not name or len(name) < 3:
            # Try inverted
            processed = preprocess_light_text(name_region)
            name = read_pokemon_name(processed)

        if not name or len(name) < 3:
            self._no_detection_count += 1
            if self._no_detection_count >= self._exit_threshold:
                return None  # Battle ended (hysteresis exit)
            return self._last_battle_info

        # Filter garbage OCR results (special chars, too short, our own app)
        import re as _re
        if _re.search(r'[#~—_\[\]={}|]', name) or len(name.strip()) < 4:
            self._no_detection_count += 1
            if self._no_detection_count >= self._exit_threshold:
                return None
            return self._last_battle_info
        if any(x in name.lower() for x in ["companion", "overlay", "pokemmo"]):
            return self._last_battle_info

        # Valid detection — reset no-detection counter
        self._no_detection_count = 0

        # Read opponent level
        lroi = self._opponent_level_roi
        lx = int(lroi["x_ratio"] * w)
        ly = int(lroi["y_ratio"] * h)
        lw = int(lroi["w_ratio"] * w)
        lh = int(lroi["h_ratio"] * h)
        level_region = frame[ly:ly + lh, lx:lx + lw]
        level = read_level(level_region) if level_region.size > 0 else None

        # Look up Pokemon in database (with fuzzy matching fallback)
        # PokeMMO displays names in French, so search name_fr first
        pokemon_data = None
        types = []
        if self.db:
            # Try exact match (EN name)
            pokemon_data = self.db.get_pokemon_by_name(name)
            if not pokemon_data:
                # Try FR name match
                pokemon_data = self.db.get_pokemon_by_name_fr(name) if hasattr(self.db, 'get_pokemon_by_name_fr') else None
            if not pokemon_data:
                # Fuzzy match against FR names (cutoff 0.75 — ScoutBot recommendation)
                all_fr = self.db.get_all_pokemon_names_fr() if hasattr(self.db, 'get_all_pokemon_names_fr') else []
                matched_fr = fuzzy_match_name(name, all_fr, cutoff=0.75) if all_fr and len(name) >= 4 else None
                if matched_fr:
                    pokemon_data = self.db.get_pokemon_by_name_fr(matched_fr)
                    log.info(f"Fuzzy matched FR '{name}' -> '{matched_fr}'")
                else:
                    # Fallback: fuzzy match EN names
                    all_en = self.db.get_all_pokemon_names() if hasattr(self.db, 'get_all_pokemon_names') else []
                    matched_en = fuzzy_match_name(name, all_en, cutoff=0.75) if all_en else None
                    if matched_en:
                        pokemon_data = self.db.get_pokemon_by_name(matched_en)
                        log.info(f"Fuzzy matched EN '{name}' -> '{matched_en}'")
            if pokemon_data:
                types = [pokemon_data["type1"]]
                if pokemon_data.get("type2"):
                    types.append(pokemon_data["type2"])
                name = pokemon_data["name"]  # Use canonical name from DB

        # Anti-flipflop: require consecutive consistent reads
        self._consecutive_reads[name] = self._consecutive_reads.get(name, 0) + 1
        for key in list(self._consecutive_reads.keys()):
            if key != name:
                self._consecutive_reads[key] = max(0, self._consecutive_reads[key] - 1)
                if self._consecutive_reads[key] == 0:
                    del self._consecutive_reads[key]

        # Detect special icons (shiny/alpha/HA)
        icons = detect_special_icons(frame)

        # Get battle summary
        battle_summary = get_battle_summary(types) if types else None

        info = {
            "name": name,
            "level": level,
            "types": types,
            "battle_summary": battle_summary,
            "pokemon_data": pokemon_data,
            "shiny": icons["shiny"],
            "alpha": icons["alpha"],
            "hidden_ability": icons["hidden_ability"],
        }

        # Only update if enough consecutive reads AND cooldown elapsed
        now = time.time()
        consec = self._consecutive_reads.get(name, 0)
        if name != self.current_opponent:
            elapsed = now - self._last_change_time
            if consec < self._min_consecutive or elapsed < self._change_cooldown:
                log.debug(f"Battle pending: '{name}' reads={consec}/{self._min_consecutive} "
                          f"cooldown={elapsed:.1f}/{self._change_cooldown}s")
                return self._last_battle_info

            self._last_change_time = now
            old = self.current_opponent or "(none)"
            self.current_opponent = name
            self.current_opponent_level = level
            self.current_opponent_types = types
            types_str = '/'.join(types) if types else '?'
            log.info(f"Battle transition: '{old}' -> '{name}' (Lv.{level}) "
                     f"Types: {types_str} | reads={consec} elapsed={elapsed:.1f}s")

        self._last_battle_info = info
        return info

    def get_counter_text(self) -> str:
        """Get formatted counter info for the current opponent."""
        if not self._last_battle_info or not self._last_battle_info.get("battle_summary"):
            return ""

        info = self._last_battle_info
        summary = info["battle_summary"]

        lines = [f"VS: {info['name']}"]
        if info["level"]:
            lines[0] += f" Lv.{info['level']}"

        lines.append(format_battle_summary(summary))
        return "\n".join(lines)

    def fuzzy_match_pokemon(self, ocr_text: str) -> str | None:
        """Try to match an OCR-read name to a known Pokemon name.

        Uses simple edit distance for fuzzy matching.
        """
        if not self.db:
            return None

        # First try exact match
        pokemon = self.db.get_pokemon_by_name(ocr_text)
        if pokemon:
            return pokemon["name"]

        # Try search
        results = self.db.search_pokemon(ocr_text, limit=5)
        if results:
            # Return closest match (first result from LIKE query)
            return results[0]["name"]

        return None


if __name__ == "__main__":
    detector = BattleDetector()

    # Test without DB
    from ..data.type_chart import get_battle_summary, format_battle_summary
    summary = get_battle_summary(["Rock", "Ground"])
    print("Test — Geodude (Rock/Ground):")
    print(format_battle_summary(summary))
