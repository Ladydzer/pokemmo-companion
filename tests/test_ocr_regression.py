"""OCR regression tests on real PokeMMO crops.

Validates that the OCR pipeline correctly reads text from actual game screenshots.
Requires Tesseract OCR to be installed (skips gracefully if not available).

Crops from ladyd_ (2026-04-02):
- route_victoire_ch4.png: "Route Victoire Ch. 4" (top-left route name)
- fermite_niv42.png: "Fermite Niv. 42" (opponent name in battle)
"""
import os
import sys
import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

CROPS_DIR = os.path.join(PROJECT_ROOT, "tests", "crops")

# Check dependencies
try:
    import cv2
    import numpy as np
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    _TESSERACT = True
except Exception:
    _TESSERACT = False

requires_ocr = pytest.mark.skipif(
    not (_CV2 and _TESSERACT),
    reason="Requires cv2 + Tesseract OCR installed"
)


def load_crop(filename: str) -> "np.ndarray":
    """Load a test crop image."""
    path = os.path.join(CROPS_DIR, filename)
    img = cv2.imread(path)
    assert img is not None, f"Could not load crop: {path}"
    return img


# === Preprocessing pipeline tests ===

@requires_ocr
class TestPreprocessing:
    """Test that preprocessing functions produce valid output."""

    def test_vector_font_produces_binary(self):
        from src.detection.ocr_engine import preprocess_vector_font
        img = load_crop("route_victoire_ch4.png")
        result = preprocess_vector_font(img, upscale=3)
        assert result is not None
        assert len(result.shape) == 2  # grayscale
        assert result.shape[0] > img.shape[0]  # upscaled + border

    def test_pixel_font_produces_binary(self):
        from src.detection.ocr_engine import preprocess_pixel_font
        img = load_crop("route_victoire_ch4.png")
        result = preprocess_pixel_font(img, upscale=4)
        assert result is not None
        assert len(result.shape) == 2

    def test_light_text_produces_binary(self):
        from src.detection.ocr_engine import preprocess_light_text
        img = load_crop("fermite_niv42.png")
        result = preprocess_light_text(img, upscale=4)
        assert result is not None
        assert len(result.shape) == 2


# === Route name OCR tests ===

@requires_ocr
class TestRouteOCR:
    """Test route name detection on real crop."""

    def test_read_route_name(self):
        from src.detection.ocr_engine import read_route_name
        img = load_crop("route_victoire_ch4.png")
        result = read_route_name(img)
        assert result, "OCR returned empty string for route crop"
        # Should contain "Route" and "Victoire" (possibly stuck together)
        result_lower = result.lower().replace(" ", "")
        assert "route" in result_lower or "victoire" in result_lower, \
            f"Expected 'Route Victoire' in OCR result, got: '{result}'"

    def test_vector_font_on_route(self):
        """Vector font pipeline should read route name correctly."""
        from src.detection.ocr_engine import preprocess_vector_font, read_text
        img = load_crop("route_victoire_ch4.png")
        processed = preprocess_vector_font(img, upscale=3)
        whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .'-"
        result = read_text(processed, psm=7, oem=1, preprocess=False, whitelist=whitelist)
        assert len(result) >= 3, f"Vector font produced too short result: '{result}'"


# === Pokemon name OCR tests ===

@requires_ocr
class TestPokemonOCR:
    """Test Pokemon name detection on real crop."""

    def test_read_pokemon_name(self):
        from src.detection.ocr_engine import read_pokemon_name
        img = load_crop("fermite_niv42.png")
        result = read_pokemon_name(img)
        assert result, "OCR returned empty string for pokemon crop"
        # Should contain "Fermite" (possibly misspelled)
        # At minimum, should have 4+ alpha characters
        alpha_count = sum(1 for c in result if c.isalpha())
        assert alpha_count >= 4, \
            f"Expected Pokemon name with 4+ letters, got: '{result}'"

    def test_gender_symbol_stripped(self):
        """Gender symbols should be removed from pokemon name."""
        from src.detection.ocr_engine import read_pokemon_name
        img = load_crop("fermite_niv42.png")
        result = read_pokemon_name(img)
        assert "\u2640" not in result, f"Female symbol not stripped: '{result}'"
        assert "\u2642" not in result, f"Male symbol not stripped: '{result}'"

    def test_level_stripped(self):
        """'Niv. 42' should be stripped from pokemon name."""
        from src.detection.ocr_engine import read_pokemon_name
        img = load_crop("fermite_niv42.png")
        result = read_pokemon_name(img)
        assert "42" not in result, f"Level not stripped from name: '{result}'"


# === Pipeline comparison ===

@requires_ocr
class TestPipelineComparison:
    """Compare all preprocessing methods on real crops.

    Not assertions — just logging which method produces the best result.
    Run with `pytest -s` to see output.
    """

    def test_compare_route_pipelines(self):
        """Compare all pipelines on route crop."""
        from src.detection.ocr_engine import (
            preprocess_vector_font, preprocess_pixel_font,
            preprocess_light_text, read_text
        )
        img = load_crop("route_victoire_ch4.png")
        whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .'-"

        results = {}
        for name, fn, kwargs in [
            ("vector_font", preprocess_vector_font, {"upscale": 3}),
            ("pixel_font", preprocess_pixel_font, {"upscale": 4}),
            ("light_text", preprocess_light_text, {"upscale": 4}),
        ]:
            processed = fn(img, **kwargs)
            text = read_text(processed, psm=7, oem=1, preprocess=False, whitelist=whitelist)
            alpha = sum(1 for c in text if c.isalpha())
            results[name] = {"text": text, "alpha_count": alpha}
            print(f"\n  [{name}] -> '{text}' (alpha={alpha})")

        # Best = most alpha characters
        best = max(results, key=lambda k: results[k]["alpha_count"])
        print(f"\n  WINNER: {best} -> '{results[best]['text']}'")

    def test_compare_pokemon_pipelines(self):
        """Compare all pipelines on pokemon crop."""
        from src.detection.ocr_engine import (
            preprocess_vector_font, preprocess_pixel_font,
            preprocess_light_text, read_text
        )
        img = load_crop("fermite_niv42.png")
        whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .'-"

        results = {}
        for name, fn, kwargs in [
            ("vector_font", preprocess_vector_font, {"upscale": 3}),
            ("pixel_font", preprocess_pixel_font, {"upscale": 4}),
            ("light_text", preprocess_light_text, {"upscale": 4}),
        ]:
            processed = fn(img, **kwargs)
            text = read_text(processed, psm=7, oem=1, preprocess=False, whitelist=whitelist)
            alpha = sum(1 for c in text if c.isalpha())
            results[name] = {"text": text, "alpha_count": alpha}
            print(f"\n  [{name}] -> '{text}' (alpha={alpha})")

        best = max(results, key=lambda k: results[k]["alpha_count"])
        print(f"\n  WINNER: {best} -> '{results[best]['text']}'")


# === Cache tests ===

class TestOCRCache:
    """Test OCR cache (no Tesseract needed)."""

    def test_cache_hit_miss(self):
        from src.detection.ocr_engine import OCRCache
        cache = OCRCache(maxsize=5)
        img = np.random.randint(0, 255, (30, 200), dtype=np.uint8)
        assert cache.get(img) is None  # miss
        cache.put(img, "test")
        assert cache.get(img) == "test"  # hit
        assert cache.hits == 1
        assert cache.misses == 1

    def test_cache_uniform_not_cached(self):
        from src.detection.ocr_engine import OCRCache
        cache = OCRCache(maxsize=5)
        black = np.zeros((30, 200), dtype=np.uint8)
        cache.put(black, "should not cache")
        assert cache.get(black) is None  # uniform → not cached

    def test_cache_lru_eviction(self):
        from src.detection.ocr_engine import OCRCache
        cache = OCRCache(maxsize=3)
        imgs = [np.random.randint(0, 255, (30, 200), dtype=np.uint8) for _ in range(5)]
        for i, img in enumerate(imgs):
            cache.put(img, f"text_{i}")
        assert len(cache._cache) <= 3
