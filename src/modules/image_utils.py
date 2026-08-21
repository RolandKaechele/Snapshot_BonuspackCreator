"""Shared image helpers: extension lists, file-dialog filter, pixmap loader."""

import io
import os

from PyQt6.QtGui import QPixmap  # type: ignore

from app_debug import dlog as _dlog

# All extensions the game uses for image/video assets (.byte = MP4 video)
ASSET_EXTS: tuple[str, ...] = (".dat", ".jpa", ".pna", ".png", ".jpg", ".jpeg", ".bytes", ".byte")

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
