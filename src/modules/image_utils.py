"""Shared image helpers: extension lists, file-dialog filter, pixmap loader."""

import io
import os

from PyQt6.QtGui import QPixmap  # type: ignore

from app_debug import dlog as _dlog

# All extensions the game uses for image/video assets (.byte = MP4 video)
ASSET_EXTS: tuple[str, ...] = (".dat", ".jpa", ".pna", ".png", ".jpg", ".jpeg", ".bytes", ".byte")

# Extensions used for bundled sound assets
AUDIO_EXTS: tuple[str, ...] = (".ogg", ".wav", ".mp3")

# Ready-made filter string for QFileDialog
ASSET_FILTER = "Images & Videos (*.png *.jpg *.jpeg *.dat *.jpa *.pna *.bytes *.byte)"


def load_pixmap(path: str) -> QPixmap:
    """Load a QPixmap from any supported game asset format.

    Reads raw bytes so Qt detects format from content, not extension.
    Falls back to Pillow for exotic formats (e.g. palette-mode PNG).
    Returns a null QPixmap when the file cannot be decoded.
    """
    if not os.path.exists(path):
        _dlog("image_utils.load_pixmap", f"not found: {path!r}")
        return QPixmap()
    with open(path, "rb") as fh:
        raw = fh.read()
    px = QPixmap()
    px.loadFromData(raw)
    if px.isNull():
        try:
            from PIL import Image  # type: ignore
            buf = io.BytesIO()
            Image.open(io.BytesIO(raw)).convert("RGBA").save(buf, format="PNG")
            px = QPixmap()
            px.loadFromData(buf.getvalue(), "PNG")
        except Exception as exc:
            _dlog("image_utils.load_pixmap", f"Pillow error: {exc}")
    return px


def resolve_asset(name: str, folder: str) -> str:
    """Resolve a bare asset name to a full path inside *folder*.

    Searches <folder>/Data/ then <folder>/; returns *name* unchanged when
    no file is found so callers can still store the name for export.
    """
    for d in (os.path.join(folder, "Data"), folder):
        for ext in ASSET_EXTS:
            p = os.path.join(d, name + ext)
            if os.path.exists(p):
                return p
    return name


def resolve_audio_asset(name: str, folder: str) -> str:
    """Resolve a bare sound name to a full path inside *folder*; returns "" if not found."""
    for d in (os.path.join(folder, "Data"), folder):
        for ext in AUDIO_EXTS:
            p = os.path.join(d, name + ext)
            if os.path.exists(p):
                return p
    return ""


def _assets_root() -> str:
    """Return the src/assets/ folder (two levels up from this file)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def game_asset_dir(asset_type: str, game: str) -> str:
    """Return src/assets/<asset_type>/<game>/, e.g. ("Texture2D", "snapshot")."""
    return os.path.join(_assets_root(), asset_type, game)


def list_game_assets(asset_type: str, game: str) -> list[str]:
    """Return sorted stem names of files found under game_asset_dir(asset_type, game)."""
    d = game_asset_dir(asset_type, game)
    if not os.path.isdir(d):
        return []
    stems = set()
    for f in os.listdir(d):
        stem, ext = os.path.splitext(f)
        if ext:
            stems.add(stem)
    return sorted(stems)


def resolve_game_asset(name: str, asset_type: str, game: str) -> str:
    """Resolve *name* to a full path under game_asset_dir(asset_type, game); "" if missing."""
    d = game_asset_dir(asset_type, game)
    if not os.path.isdir(d):
        return ""
    for f in os.listdir(d):
        stem, ext = os.path.splitext(f)
        if stem == name:
            return os.path.join(d, f)
    return ""
