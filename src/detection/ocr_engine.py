"""OCR engine using Tesseract for reading game text."""
import numpy as np
import cv2

from ..utils.config import AppConfig
from ..utils.logger import log

_config = AppConfig.load()


def init_tesseract() -> bool:
    """Initialize Tesseract OCR. Returns True if available."""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = _config.ocr.tesseract_path
        # Quick test
        pytesseract.get_tesseract_version()
        log.info("Tesseract OCR initialized")
        return True
    except Exception as e:
        log.warning(f"Tesseract not available: {e}")
        return False


def preprocess_for_ocr(image: np.ndarray, upscale: int = 3) -> np.ndarray:
    """Pre-process image for better OCR accuracy.

    Steps:
    1. Convert to grayscale
    2. Upscale (Tesseract works best at ~300 DPI)
    3. Apply adaptive thresholding
    4. Denoise
    """
    if image is None or image.size == 0:
        return image

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
        processed = preprocess_for_ocr(image, upscale=_config.ocr.upscale_factor)
    else:
        processed = image

    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"

    try:
        text = pytesseract.image_to_string(processed, lang=_config.ocr.language, config=config)
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


if __name__ == "__main__":
    # Test OCR initialization
    if init_tesseract():
        print("Tesseract OCR ready!")

        # Test with a synthetic image
        test_img = np.ones((50, 300, 3), dtype=np.uint8) * 255
        cv2.putText(test_img, "Route 101", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        result = read_route_name(test_img)
        print(f"OCR test: '{result}'")
    else:
        print("Tesseract not available. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
