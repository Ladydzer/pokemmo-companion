"""Sprite cache — loads and caches Pokemon sprite images for the UI."""
from pathlib import Path
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QSize

from ..utils.config import PROJECT_ROOT

SPRITES_DIR = PROJECT_ROOT / "data" / "sprites"
_cache: dict[str, QPixmap] = {}


def get_sprite(pokemon_id: int, size: int = 96) -> QPixmap | None:
    """Get a Pokemon sprite as a QPixmap.

    Args:
        pokemon_id: National dex number (1-649)
        size: Desired size in pixels (sprites are scaled)

    Returns:
        QPixmap or None if sprite not found.
    """
    cache_key = f"{pokemon_id}_{size}"
    if cache_key in _cache:
        return _cache[cache_key]

    sprite_path = SPRITES_DIR / f"{pokemon_id}.png"
    if not sprite_path.exists():
        return None

    pixmap = QPixmap(str(sprite_path))
    if pixmap.isNull():
        return None

    if size != 96:
        from PyQt6.QtCore import Qt
        pixmap = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    _cache[cache_key] = pixmap
    return pixmap


def get_type_icon_html(type_name: str) -> str:
    """Get an HTML-styled type badge for use in QLabel rich text."""
    from .theme import TYPE_COLORS
    color = TYPE_COLORS.get(type_name, "#888")
    return (f'<span style="background-color:{color}; color:white; '
            f'padding:2px 8px; border-radius:3px; font-size:11px; '
            f'font-weight:bold;">{type_name}</span>')


def has_sprites() -> bool:
    """Check if sprites are available."""
    return SPRITES_DIR.exists() and any(SPRITES_DIR.glob("*.png"))


def sprite_count() -> int:
    """Count available sprites."""
    if not SPRITES_DIR.exists():
        return 0
    return len(list(SPRITES_DIR.glob("*.png")))
