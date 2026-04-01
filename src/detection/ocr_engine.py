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

    # Upscale
    if upscale > 1:
        h, w = gray.shape
        gray = cv2.resize(gray, (w * upscale, h * upscale), interpolation=cv2.INTER_CUBIC)

    # Adaptive threshold to isolate text
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Light denoise
    binary = cv2.medianBlur(binary, 3)

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
        gray = cv2.resize(gray, (w * upscale, h * upscale), interpolation=cv2.INTER_CUBIC)

    # Invert (light text on dark bg -> dark text on light bg for Tesseract)
    inverted = cv2.bitwise_not(gray)

    # Threshold
    _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def read_text(image: np.ndarray, psm: int = 7, preprocess: bool = True,
              whitelist: str = "") -> str:
    """Read text from an image region using Tesseract.

    Args:
        image: BGR or grayscale image
        psm: Page segmentation mode (7=single line, 6=block, 13=raw line)
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

    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"

    try:
        text = pytesseract.image_to_string(processed, lang=_get_config().ocr.language, config=config)
        return text.strip()
    except Exception as e:
        log.debug(f"OCR failed: {e}")
        return ""


def read_pokemon_name(image: np.ndarray) -> str:
    """Read a Pokemon name from a battle screen region.

    Optimized for the specific font and layout of PokeMMO battle text.
    """
    # Pokemon names are ASCII letters + some special chars (Nidoran♀/♂, Mr. Mime, etc.)
    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-' 2♀♂"
    text = read_text(image, psm=7, whitelist=whitelist)

    # Clean up common OCR artifacts
    text = text.strip().strip("_|[]{}()")

    # Fix common misreads
    replacements = {
        "0": "O",  # Zero -> O in names
        "1": "l",  # One -> l in names
    }
    for old, new in replacements.items():
        if old in text and not text.isdigit():
            text = text.replace(old, new)

    return text


def read_route_name(image: np.ndarray) -> str:
    """Read a route/area name from the minimap/header region.

    Route names in PokeMMO follow patterns like:
    - "Route 101", "Route 1"
    - "Littleroot Town", "Pallet Town"
    - "Mt. Moon", "Viridian Forest"
    """
    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .'-"
    text = read_text(image, psm=7, whitelist=whitelist)
    return text.strip()


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
    """Fuzzy-match an OCR-read name against a list of valid Pokemon names.

    Uses difflib SequenceMatcher (same approach as pokemon-ocr-scrapper).
    Returns the best match above the cutoff, or None.
    """
    if not name or not valid_names:
        return None
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
