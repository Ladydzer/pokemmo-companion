"""Route name detection — hybrid approach: window title + OCR fallback.

Strategy (fastest to slowest):
1. Read game window title via Win32 API (instant, 0% error)
2. OCR on the location text area (20-50ms, ~90% accuracy)
"""
import time
import re
import numpy as np
import cv2

from .ocr_engine import read_route_name, preprocess_light_text
from ..capture.screen_capture import get_window_title
from ..utils.logger import log


class RouteDetector:
    """Detects the current route/location name from the game screen.

    Uses hybrid approach: window title first, OCR as fallback.
    """

    def __init__(self):
        self.current_route: str = ""
        self.current_region: str = ""
        self.last_change: float = 0.0
        self._consecutive_reads: dict[str, int] = {}
        self._min_consecutive = 2  # Require 2 consistent reads before updating

        # ROI (Region of Interest) ratios relative to game window
        # Calibrated from real PokeMMO screenshot: route name is in a small
        # dark banner at the top-left of the game window
        self._route_roi = {
            "x_ratio": 0.01,
            "y_ratio": 0.01,
            "w_ratio": 0.18,
            "h_ratio": 0.04,
        }

    def set_roi(self, x_ratio: float, y_ratio: float,
                w_ratio: float, h_ratio: float) -> None:
        """Set the region of interest for route name detection."""
        self._route_roi = {
            "x_ratio": x_ratio, "y_ratio": y_ratio,
            "w_ratio": w_ratio, "h_ratio": h_ratio,
        }

    def detect_from_window_title(self, hwnd: int) -> str | None:
        """Try to detect route from game window title (instant, no OCR needed).

        PokeMMO may include location info in its window title.
        Returns route name if detected and changed, None otherwise.
        """
        if not hwnd:
            return None

        title = get_window_title(hwnd)
        if not title:
            return None

        # Log title for debugging (helps ladyd_ tell us what it shows)
        if not hasattr(self, '_last_title') or title != self._last_title:
            self._last_title = title
            log.info(f"Window title: '{title}'")

        # Try to extract location from title
        # Common patterns: "PokeMMO - Route 101" or "PokeMMO [Route 101]"
        patterns = [
            r'PokeMMO\s*[-:]\s*(.+)',
            r'PokeMMO\s*\[(.+?)\]',
            r'PokeMMO\s*\((.+?)\)',
        ]
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location and location != self.current_route:
                    return self._process_route_change(location)

        return None

    def detect_route(self, frame: np.ndarray) -> str | None:
        """Detect the route name from a game screenshot using OCR.

        This is the fallback method when window title doesn't contain location.
        Returns the route name if changed, None if unchanged.
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]
        roi = self._route_roi

        # Extract the route name region
        x = int(roi["x_ratio"] * w)
        y = int(roi["y_ratio"] * h)
        rw = int(roi["w_ratio"] * w)
        rh = int(roi["h_ratio"] * h)

        route_region = frame[y:y + rh, x:x + rw]
        if route_region.size == 0:
            return None

        # Try OCR on the region
        text = read_route_name(route_region)

        if not text or len(text) < 3:
            # Try with inverted preprocessing (light text on dark background)
            processed = preprocess_light_text(route_region)
            text = read_route_name(processed)

        if not text or len(text) < 3:
            return None

        # Clean up the text
        text = self._clean_route_name(text)
        if not text:
            return None

        # Require consecutive consistent reads to avoid OCR flicker
        self._consecutive_reads[text] = self._consecutive_reads.get(text, 0) + 1

        # Clear counts for other values
        for key in list(self._consecutive_reads.keys()):
            if key != text:
                self._consecutive_reads[key] = max(0, self._consecutive_reads[key] - 1)
                if self._consecutive_reads[key] == 0:
                    del self._consecutive_reads[key]

        if self._consecutive_reads[text] >= self._min_consecutive:
            if text != self.current_route:
                return self._process_route_change(text)

        return None

    def _process_route_change(self, text: str) -> str:
        """Process a confirmed route change."""
        old_route = self.current_route
        self.current_route = text
        self.current_region = self._infer_region(text)
        self.last_change = time.time()
        log.info(f"Route changed: '{old_route}' -> '{text}' (region: {self.current_region})")
        return text

    def _clean_route_name(self, text: str) -> str:
        """Clean up OCR artifacts and normalize PokeMMO route names."""
        # Remove leading/trailing junk
        text = text.strip().strip("_|[]{}()!@#$%^&*")

        # Fix common OCR misreads for route names
        replacements = {
            "Reute": "Route",
            "Raute": "Route",
            "Toute": "Route",
            "Rte ": "Route ",
            "Rte.": "Route",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Expand PokeMMO abbreviations
        abbreviations = {
            "Ch.": "Chambre",
            "Niv.": "Niveau",
            "Rte.": "Route",
            "Mt.": "Mont",
            "Pt.": "Pont",
        }
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)

        # Validate: must contain at least one letter
        if not any(c.isalpha() for c in text):
            return ""

        return text

    def _infer_region(self, route_name: str) -> str:
        """Try to infer the region from the route name.

        This is a basic heuristic — the database lookup is more reliable.
        """
        route_lower = route_name.lower()

        # Kanto landmarks
        kanto_places = ["pallet", "viridian", "pewter", "cerulean", "vermilion",
                        "lavender", "celadon", "fuchsia", "saffron", "cinnabar"]
        for place in kanto_places:
            if place in route_lower:
                return "Kanto"

        # Route number heuristics
        import re
        match = re.search(r'route\s*(\d+)', route_lower)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 28:
                return "Kanto"
            elif 29 <= num <= 46:
                return "Johto"
            elif 101 <= num <= 134:
                return "Hoenn"
            elif 201 <= num <= 230:
                return "Sinnoh"
            elif num >= 1 and "unova" in route_lower:
                return "Unova"

        # Hoenn landmarks
        hoenn_places = ["littleroot", "oldale", "petalburg", "rustboro", "dewford",
                        "slateport", "mauville", "verdanturf", "fallarbor", "lavaridge"]
        for place in hoenn_places:
            if place in route_lower:
                return "Hoenn"

        # Sinnoh landmarks
        sinnoh_places = ["twinleaf", "sandgem", "jubilife", "oreburgh", "floaroma",
                         "eterna", "hearthome", "solaceon", "veilstone", "pastoria"]
        for place in sinnoh_places:
            if place in route_lower:
                return "Sinnoh"

        # Unova landmarks
        unova_places = ["nuvema", "accumula", "striaton", "nacrene", "castelia",
                        "nimbasa", "driftveil", "mistralton", "icirrus", "opelucid"]
        for place in unova_places:
            if place in route_lower:
                return "Unova"

        # Johto landmarks
        johto_places = ["new bark", "cherrygrove", "violet", "azalea", "goldenrod",
                        "ecruteak", "olivine", "cianwood", "mahogany", "blackthorn"]
        for place in johto_places:
            if place in route_lower:
                return "Johto"

        return ""

    def get_time_on_route(self) -> float:
        """Get seconds spent on current route."""
        if self.last_change == 0:
            return 0.0
        return time.time() - self.last_change


if __name__ == "__main__":
    detector = RouteDetector()

    # Test region inference
    test_routes = [
        "Route 1", "Route 101", "Route 201",
        "Pallet Town", "Littleroot Town", "Twinleaf Town",
        "Cerulean City", "Mauville City", "Jubilife City",
    ]
    for route in test_routes:
        region = detector._infer_region(route)
        print(f"{route} → {region}")
