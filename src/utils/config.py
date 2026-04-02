"""Configuration for PokeMMO Companion."""
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path.home() / ".pokemmo-companion"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Handle PyInstaller bundled paths
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "pokemon.db"


@dataclass
class CaptureConfig:
    target_fps: int = 2
    capture_region: str = "auto"  # "auto" or "manual"
    game_window_title: str = "PokeMMO"


@dataclass
class OCRConfig:
    tesseract_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    language: str = "fra"  # French — PokeMMO displays FR names (fallback to eng)
    psm: int = 7  # Single line
    oem: int = 1  # LSTM engine
    upscale_factor: int = 4  # 4x for pixel fonts (need ~300 DPI equivalent)


@dataclass
class OverlayConfig:
    opacity: float = 0.75  # 75% — less intrusive during gameplay
    auto_hide_delay: int = 10  # seconds before auto-hide (0 = disabled)
    toggle_hotkey: str = "f9"
    position_x: int = -1  # -1 = auto (right side)
    position_y: int = -1
    width: int = 300
    theme: str = "dark"


@dataclass
class AppConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    first_run: bool = True
    resolution: tuple[int, int] = (1920, 1080)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                config = cls()
                config.capture = CaptureConfig(**data.get("capture", {}))
                config.ocr = OCRConfig(**data.get("ocr", {}))
                config.overlay = OverlayConfig(**data.get("overlay", {}))
                config.first_run = data.get("first_run", True)
                res = data.get("resolution", [1920, 1080])
                config.resolution = tuple(res)
                return config
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()
