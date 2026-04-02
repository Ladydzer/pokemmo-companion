"""OCR engine using Tesseract for reading game text.

Integrates techniques from pokemon-ocr-scrapper (nthGP):
- Contrast enhancement before OCR
- HSV color-based icon detection (shiny/alpha/hidden ability)
- IV/EV/Nature extraction from stats screens
- Fuzzy name matching with difflib
"""
from __future__ import annotations

import re
import difflib
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

try:
    import numpy as np  # type: ignore[no-redef]
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

from ..utils.config import AppConfig
from ..utils.logger import log

_config = None


# === Perceptual hash + LRU cache for OCR results ===

class OCRCache:
    """LRU cache keyed by perceptual image hash — skips OCR on identical frames."""

    def __init__(self, maxsize: int = 100):
        self._cache: OrderedDict[int, str] = OrderedDict()
        self._maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def _phash(self, image: np.ndarray) -> int:
        """Compute a fast perceptual hash (8x8 mean-based).

        Downsample to 8x8 grayscale, compare each pixel to mean → 64-bit hash.
        Robust to small noise/compression artifacts.
        Returns -1 for uniform/black images (not cacheable).
        """
        if image is None or image.size == 0:
            return -1
        gray = image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Skip uniform images (black screen, loading, etc.) — not worth caching
        if gray.std() < 5:
            return -1
        resized = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA)
        mean_val = resized.mean()
        bits = (resized > mean_val).flatten()
        return int(''.join('1' if b else '0' for b in bits), 2)

    def get(self, image: np.ndarray) -> str | None:
        """Look up cached OCR result for this image. Returns None on miss."""
        h = self._phash(image)
        if h == -1:
            return None  # Uniform image — always reprocess
        if h in self._cache:
            self._cache.move_to_end(h)
            self.hits += 1
            return self._cache[h]
        self.misses += 1
        return None

    def put(self, image: np.ndarray, text: str) -> None:
        """Store OCR result for this image hash."""
        h = self._phash(image)
        if h == -1:
            return  # Don't cache uniform images
        self._cache[h] = text
        self._cache.move_to_end(h)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


# Shared cache instances (one per OCR function type)
_route_cache = None
_pokemon_cache = None


def _get_route_cache() -> OCRCache:
    global _route_cache
    if _route_cache is None:
        _route_cache = OCRCache(maxsize=100)
    return _route_cache


def _get_pokemon_cache() -> OCRCache:
    global _pokemon_cache
    if _pokemon_cache is None:
        _pokemon_cache = OCRCache(maxsize=100)
    return _pokemon_cache

def _get_config():
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def init_tesseract() -> bool:
    """Initialize Tesseract OCR. Returns True if available."""
    import shutil
    config = _get_config()

    # Try configured path first, then PATH, then common locations
    tesseract_paths = [
        config.ocr.tesseract_path,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in tesseract_paths:
        if path:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = path
                pytesseract.get_tesseract_version()
                log.info(f"Tesseract OCR initialized at {path}")
                return True
            except Exception:
                continue

    log.warning("Tesseract OCR not found! Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    log.warning("OCR features will be disabled until Tesseract is installed.")
    return False


def isolate_text_by_color(image: np.ndarray) -> np.ndarray:
    """Extract text pixels by HSV color range, removing background noise.

    PokeMMO text colors:
    - White text: low saturation, high value (route names, menus)
    - Yellow text: H 20-40 (Pokemon names, highlights)
    Returns binary image: white text on black background.
    """
    if image is None or image.size == 0 or len(image.shape) < 3:
        return image

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # White text mask (low saturation, high brightness)
    white_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 50, 255]))

    # Yellow text mask
    yellow_mask = cv2.inRange(hsv, np.array([18, 80, 150]), np.array([40, 255, 255]))

    # Light gray/cream text (some UI elements)
    light_mask = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 30, 255]))

    # Combine all text masks
    text_mask = white_mask | yellow_mask | light_mask

    # Apply mask: text becomes white, everything else black
    result = np.zeros(image.shape[:2], dtype=np.uint8)
    result[text_mask > 0] = 255

    return result


def preprocess_pixel_font(image: np.ndarray, upscale: int = 4) -> np.ndarray:
    """Optimized preprocessing for PokeMMO pixel art fonts.

    Pipeline: HSV isolation → INTER_NEAREST upscale → Otsu → 10px border.
    No CLAHE (adds noise to clean pixel art).
    No medianBlur (destroys 1px strokes).
    """
    if image is None or image.size == 0:
        return image

    # Step 1: HSV color isolation (removes background noise)
    if len(image.shape) == 3:
        text_only = isolate_text_by_color(image)
    else:
        text_only = image.copy()

    # Step 2: Upscale with INTER_NEAREST (preserves pixel edges, no anti-aliasing)
    if upscale > 1:
        h, w = text_only.shape[:2]
        text_only = cv2.resize(text_only, (w * upscale, h * upscale),
                               interpolation=cv2.INTER_NEAREST)

    # Step 3: Light Gaussian blur to smooth jagged edges after upscale
    text_only = cv2.GaussianBlur(text_only, (3, 3), 0)

    # Step 4: Otsu threshold (uniform intensity, better than adaptive for pixel fonts)
    _, binary = cv2.threshold(text_only, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Step 5: Add 10px white border (Tesseract needs margin around text)
    binary = cv2.copyMakeBorder(binary, 10, 10, 10, 10,
                                cv2.BORDER_CONSTANT, value=255)

    return binary


def preprocess_vector_font(image: np.ndarray, upscale: int = 3) -> np.ndarray:
    """Optimized preprocessing for NotoSans (anti-aliased vector font).

    PokeMMO uses NotoSans — a smooth vector font with anti-aliasing.
    Pipeline: grayscale → INTER_CUBIC upscale → Otsu → 10px border.
    INTER_CUBIC preserves smooth curves (unlike INTER_NEAREST which creates staircasing).
    """
    if image is None or image.size == 0:
        return image

    # Step 1: Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Step 2: Upscale with INTER_CUBIC (preserves anti-aliased curves)
    if upscale > 1:
        h, w = gray.shape
        gray = cv2.resize(gray, (w * upscale, h * upscale),
                          interpolation=cv2.INTER_CUBIC)

    # Step 3: Auto-invert if light text on dark background
    if gray.mean() < 128:
        gray = cv2.bitwise_not(gray)

    # Step 4: Otsu threshold for clean binarization
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Step 5: Add 10px white border (Tesseract needs margin)
    binary = cv2.copyMakeBorder(binary, 10, 10, 10, 10,
                                cv2.BORDER_CONSTANT, value=255)

    return binary


def enhance_contrast(image: np.ndarray, factor: float = 1.5) -> np.ndarray:
    """Boost contrast before OCR (technique from pokemon-ocr-scrapper).

    PokeMMO text can be low-contrast against gradients. A 1.5x contrast
    boost significantly improves Tesseract accuracy.
    """
    if image is None or image.size == 0:
        return image
    # CLAHE provides adaptive contrast without blowing out bright areas
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        clahe = cv2.createCLAHE(clipLimit=factor * 2, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(l_channel)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=factor * 2, tileGridSize=(8, 8))
        return clahe.apply(image)


def preprocess_for_ocr(image: np.ndarray, upscale: int = 3,
                       contrast: bool = True) -> np.ndarray:
    """Pre-process image for better OCR accuracy.

    Steps:
    1. Contrast enhancement (CLAHE)
    2. Convert to grayscale
    3. Upscale (Tesseract works best at ~300 DPI)
    4. Apply adaptive thresholding
    5. Denoise
    """
    if image is None or image.size == 0:
        return image

    # Contrast boost before grayscale conversion
    if contrast and len(image.shape) == 3:
        image = enhance_contrast(image)

    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Upscale with INTER_NEAREST (preserves pixel font edges)
    if upscale > 1:
        h, w = gray.shape
        gray = cv2.resize(gray, (w * upscale, h * upscale), interpolation=cv2.INTER_NEAREST)

    # Adaptive threshold to isolate text
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    return binary


def preprocess_light_text(image: np.ndarray, upscale: int = 3) -> np.ndarray:
    """Pre-process image with light text on dark background (common in PokeMMO)."""
    if image is None or image.size == 0:
        return image

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if upscale > 1:
        h, w = gray.shape
        gray = cv2.resize(gray, (w * upscale, h * upscale), interpolation=cv2.INTER_NEAREST)

    # Invert (light text on dark bg -> dark text on light bg for Tesseract)
    inverted = cv2.bitwise_not(gray)

    # Threshold
    _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def read_text(image: np.ndarray, psm: int = 7, oem: int = 1,
              preprocess: bool = True, whitelist: str = "") -> str:
    """Read text from an image region using Tesseract.

    Args:
        image: BGR or grayscale image
        psm: Page segmentation mode (7=single line, 6=block, 13=raw line)
        oem: OCR Engine Mode (0=legacy, 1=LSTM, 3=both)
        preprocess: Apply preprocessing pipeline
        whitelist: Limit characters (e.g., "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ")
    """
    try:
        import pytesseract
    except ImportError:
        log.error("pytesseract not installed")
        return ""

    if image is None or image.size == 0:
        return ""

    if preprocess:
        processed = preprocess_for_ocr(image, upscale=_get_config().ocr.upscale_factor)
    else:
        processed = image

    config = f"--psm {psm} --oem {oem}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"

    # Determine language — prefer fra for French Pokemon names
    cfg = _get_config()
    lang = cfg.ocr.language

    try:
        text = pytesseract.image_to_string(processed, lang=lang, config=config)
        return text.strip()
    except Exception as e:
        # Fallback to eng if fra not available
        if lang != "eng":
            try:
                text = pytesseract.image_to_string(processed, lang="eng", config=config)
                return text.strip()
            except Exception:
                pass
        log.debug(f"OCR failed: {e}")
        return ""


def read_pokemon_name(image: np.ndarray) -> str:
    """Read a Pokemon name from a battle screen region.

    Tries multiple preprocessing approaches. NotoSans (vector font) confirmed.
    Priority: vector font (INTER_CUBIC) > pixel font (HSV+INTER_NEAREST) > light text.
    Uses perceptual hash cache to skip OCR on identical frames.
    """
    if not _CV2_AVAILABLE or image is None or image.size == 0:
        return ""

    # Check cache first — skip expensive OCR if frame region hasn't changed
    cache = _get_pokemon_cache()
    cached = cache.get(image)
    if cached is not None:
        return cached

    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzéèêëàâùûôîïçÉÈÊËÀÂÙÛÔÎÏÇ.-' 0123456789"
    results = []

    # Method 1 (PRIMARY): Vector font — INTER_CUBIC upscale + Otsu (NotoSans)
    vector_img = preprocess_vector_font(image, upscale=3)
    t1 = read_text(vector_img, psm=7, oem=1, preprocess=False, whitelist=whitelist)
    if t1 and len(t1) >= 3:
        results.append(t1)

    # Method 2: Pixel font pipeline — HSV isolation + INTER_NEAREST (fallback)
    pixel_img = preprocess_pixel_font(image, upscale=4)
    t2 = read_text(pixel_img, psm=7, oem=1, preprocess=False, whitelist=whitelist)
    if t2 and len(t2) >= 3:
        results.append(t2)

    # Method 3: Light text (invert + Otsu, legacy)
    t3 = read_text(preprocess_light_text(image, upscale=4), psm=7, oem=1,
                   preprocess=False, whitelist=whitelist)
    if t3 and len(t3) >= 3:
        results.append(t3)

    if not results:
        return ""

    # Pick best result (most alpha chars = least noise)
    text = max(results, key=lambda t: sum(1 for c in t if c.isalpha()))

    # Clean up
    text = text.strip().strip("_|[]{}()")
    text = re.sub(r'\s*Niv\.?\s*\d+', '', text).strip()
    # Remove gender symbols (♀/♂) that appear after level
    text = text.replace('\u2640', '').replace('\u2642', '').strip()

    cache.put(image, text)
    return text


def read_route_name(image: np.ndarray) -> str:
    """Read a route/area name from the minimap/header region.

    Tries multiple preprocessing approaches and picks the best result.
    Priority: pixel font pipeline (HSV) > inverted NN upscale > standard.
    Uses perceptual hash cache to skip OCR on identical frames.
    """
    if not _CV2_AVAILABLE or image is None or image.size == 0:
        return ""

    # Check cache first — skip expensive OCR if frame region hasn't changed
    cache = _get_route_cache()
    cached = cache.get(image)
    if cached is not None:
        return cached

    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .'-éèêëàâùûôîïçÉÈÊËÀÂÙÛÔÎÏÇ"
    results = []

    # Method 1 (PRIMARY): Vector font — INTER_CUBIC upscale + Otsu (NotoSans)
    vector_img = preprocess_vector_font(image, upscale=3)
    text1 = read_text(vector_img, psm=7, oem=1, preprocess=False, whitelist=whitelist)
    if text1:
        results.append(text1)

    # Method 2: Pixel font pipeline — HSV + INTER_NEAREST (fallback for themed UIs)
    pixel_img = preprocess_pixel_font(image, upscale=4)
    text2 = read_text(pixel_img, psm=7, oem=1, preprocess=False, whitelist=whitelist)
    if text2:
        results.append(text2)

    # Method 3: Light text preprocessing (legacy)
    text3 = read_text(preprocess_light_text(image, upscale=4), psm=7, oem=1,
                      preprocess=False, whitelist=whitelist)
    if text3:
        results.append(text3)

    if not results:
        return ""

    # Pick the result with the most alphabetic chars (least noise)
    best = max(results, key=lambda t: sum(1 for c in t if c.isalpha()))
    result = best.strip()
    cache.put(image, result)
    return result


def read_level(image: np.ndarray) -> int | None:
    """Read a Pokemon level from battle screen (e.g., 'Lv.25')."""
    text = read_text(image, psm=7, whitelist="Llv.0123456789 ")

    # Extract number from "Lv.25" or "Lv 25" or just "25"
    import re
    match = re.search(r'(\d+)', text)
    if match:
        level = int(match.group(1))
        if 1 <= level <= 100:
            return level
    return None


# === Icon detection (HSV color-based, from pokemon-ocr-scrapper) ===

def _hsv_ranges():
    """Build HSV ranges lazily (needs numpy)."""
    return {
        "shiny": {"lower": np.array([20, 100, 50]), "upper": np.array([50, 255, 255])},
        "alpha": [
            {"lower": np.array([0, 50, 50]), "upper": np.array([10, 255, 255])},
            {"lower": np.array([170, 50, 50]), "upper": np.array([180, 255, 255])},
        ],
        "hidden_ability": {"lower": np.array([90, 200, 200]), "upper": np.array([100, 255, 255])},
    }


def detect_special_icons(image) -> dict[str, bool]:
    """Detect shiny star, alpha mark, and hidden ability icon via HSV color ranges.

    Checks the top-left 12% of the image for shiny/alpha icons,
    and a central region (45-65% x, 65-73% y) for hidden ability badge.
    """
    default = {"shiny": False, "alpha": False, "hidden_ability": False}
    if not _CV2_AVAILABLE or image is None or image.size == 0:
        return default

    h, w = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    ranges = _hsv_ranges()

    # Icon region: top-left 12%
    icon_region = hsv[:int(h * 0.12), :int(w * 0.12)]
    # HA region: center area
    ha_region = hsv[int(h * 0.65):int(h * 0.73), int(w * 0.45):int(w * 0.65)]

    min_pixels = 30  # Minimum colored pixels to count as detected

    # Shiny
    shiny_mask = cv2.inRange(icon_region, ranges["shiny"]["lower"],
                             ranges["shiny"]["upper"])
    is_shiny = cv2.countNonZero(shiny_mask) > min_pixels

    # Alpha (red hue wraps around 0/180)
    alpha_ranges = ranges["alpha"]
    alpha_mask1 = cv2.inRange(icon_region, alpha_ranges[0]["lower"], alpha_ranges[0]["upper"])
    alpha_mask2 = cv2.inRange(icon_region, alpha_ranges[1]["lower"], alpha_ranges[1]["upper"])
    is_alpha = cv2.countNonZero(alpha_mask1 | alpha_mask2) > min_pixels

    # Hidden ability
    ha_mask = cv2.inRange(ha_region, ranges["hidden_ability"]["lower"],
                          ranges["hidden_ability"]["upper"])
    is_ha = cv2.countNonZero(ha_mask) > min_pixels

    return {"shiny": is_shiny, "alpha": is_alpha, "hidden_ability": is_ha}


# === Stats screen extraction (IVs, EVs, Nature) ===

NATURES = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
]

NATURES_FR = {
    "Hardy": "Hardi", "Lonely": "Solo", "Brave": "Brave", "Adamant": "Rigide",
    "Naughty": "Mauvais", "Bold": "Assuré", "Docile": "Docile", "Relaxed": "Relax",
    "Impish": "Malin", "Lax": "Lâche", "Timid": "Timide", "Hasty": "Pressé",
    "Serious": "Sérieux", "Jolly": "Jovial", "Naive": "Naïf", "Modest": "Modeste",
    "Mild": "Doux", "Quiet": "Discret", "Bashful": "Pudique", "Rash": "Foufou",
    "Calm": "Calme", "Gentle": "Gentil", "Sassy": "Malpoli", "Careful": "Prudent",
    "Quirky": "Bizarre",
}


def read_stats_screen(image: np.ndarray) -> dict:
    """Extract IVs, EVs, nature, and name from a PokeMMO stats/PC screen.

    Expects a screenshot of the Pokemon summary/stats page.
    Returns a dict with extracted fields (empty strings if not found).
    """
    if image is None or image.size == 0:
        return {}

    # Full-image OCR for stats screen (block mode)
    full_text = read_text(image, psm=6, preprocess=True)

    result = {
        "name": "",
        "level": None,
        "nature": "",
        "nature_fr": "",
        "ivs": [],
        "evs": [],
        "ability": "",
    }

    # Extract name + level: "Lv.25 Pikachu" or "Pikachu Lv.25"
    name_match = re.search(r'(?:Lv\.?\s*(\d+))\s+([A-Za-z]+)', full_text)
    if name_match:
        result["level"] = int(name_match.group(1))
        result["name"] = name_match.group(2)
    else:
        name_match2 = re.search(r'([A-Za-z]{3,})\s+(?:Lv\.?\s*(\d+))', full_text)
        if name_match2:
            result["name"] = name_match2.group(1)
            result["level"] = int(name_match2.group(2))

    # Extract IVs: pattern like "31/28/31/31/25/31"
    iv_match = re.search(r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', full_text)
    if iv_match:
        ivs = [int(iv_match.group(i)) for i in range(1, 7)]
        if all(0 <= v <= 31 for v in ivs):
            result["ivs"] = ivs

    # Extract EVs: same pattern but values 0-252
    # Look for a second occurrence of the pattern
    stat_patterns = re.findall(r'(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})', full_text)
    if len(stat_patterns) >= 2:
        evs = [int(v) for v in stat_patterns[1]]
        if all(0 <= v <= 252 for v in evs):
            result["evs"] = evs

    # Extract nature
    for nature in NATURES:
        if nature.lower() in full_text.lower():
            # Avoid "Brave Bird" false positive
            idx = full_text.lower().find(nature.lower())
            after = full_text[idx + len(nature):idx + len(nature) + 5]
            if "bird" not in after.lower():
                result["nature"] = nature
                result["nature_fr"] = NATURES_FR.get(nature, nature)
                break

    # Detect special icons
    icons = detect_special_icons(image)
    result.update(icons)

    return result


def fuzzy_match_name(name: str, valid_names: list[str],
                     cutoff: float = 0.7) -> str | None:
    """Fuzzy-match an OCR-read name against a list of valid names.

    Uses rapidfuzz (77x faster than difflib) with fallback to difflib.
    cutoff: 0.0-1.0 (converted to 0-100 for rapidfuzz internally).
    """
    if not name or not valid_names:
        return None
    try:
        from rapidfuzz import process, fuzz
        result = process.extractOne(name, valid_names,
                                    scorer=fuzz.ratio,
                                    score_cutoff=cutoff * 100)
        return result[0] if result else None
    except ImportError:
        # Fallback to difflib if rapidfuzz not installed
        matches = difflib.get_close_matches(name, valid_names, n=1, cutoff=cutoff)
        return matches[0] if matches else None


if __name__ == "__main__":
    # Test OCR initialization
    if init_tesseract():
        print("Tesseract OCR ready!")

        # Test with a synthetic image
        test_img = np.ones((50, 300, 3), dtype=np.uint8) * 255
        cv2.putText(test_img, "Route 101", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        result = read_route_name(test_img)
        print(f"OCR test: '{result}'")

        # Test icon detection
        print(f"\nIcon detection test: {detect_special_icons(test_img)}")

        # Test fuzzy matching
        names = ["Pikachu", "Pidgey", "Pidgeotto", "Pichu", "Pinsir"]
        print(f"Fuzzy 'Plkachu' -> {fuzzy_match_name('Plkachu', names)}")
        print(f"Fuzzy 'Pidgey' -> {fuzzy_match_name('Pidgey', names)}")
    else:
        print("Tesseract not available. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
