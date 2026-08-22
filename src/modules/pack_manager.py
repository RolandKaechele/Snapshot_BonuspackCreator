"""Pack manager — Load and Save the pack project JSON."""

import json
import os
import shutil
import tempfile
from typing import Any

from app_debug import dlog as _dlog


class _DirtyDict(dict):
    """dict that calls _on_change() on any mutation."""

    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cb = callback

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._cb()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._cb()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._cb()

    def pop(self, *args):
        result = super().pop(*args)
        self._cb()
        return result

    def setdefault(self, key, default=None):
        existed = key in self
        result = super().setdefault(key, default)
        if not existed:
            self._cb()
        return result


# Default in-memory pack structure
_EMPTY_PACK: dict[str, Any] = {
    "version": 1,
    "game": "snapshot",          # "snapshot" | "lewdshores"
    "pack_type": "photos",       # "photos" | "lovelens" | "events"
    "title": "",
    "id": "",
    "id_range": "",
    # [Defaults] section values
    "defaults_position": "upskirt",
    "defaults_type": "plain",
    "defaults_color": "white",
    # [Special Category]
    "special_category": "",
    "special_category_color": "#dea3a5",
    # [Special Traits] — list of raw triplet strings
    "special_types": [],
    "special_colors": [],
    # preserved verbatim on export
    "passthrough_sections": [],
    "photos": [],
    "overlays": {},
    "textures": {},
    "texts": {},
    "event_type": "normal",
    "events": [],
    "cutscenes": [],
    "love_lens": {},
}


class PackManager:
    """Holds the in-memory pack state and handles JSON serialisation."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._path: str | None = None
        self._dirty: bool = False
        self.new_pack()

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def current_path(self) -> str | None:
        return self._path

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def _make_dirty_dict(self, source: dict) -> "_DirtyDict":
        d = _DirtyDict(self.mark_dirty)
        d.update(source)   # populate without triggering dirty
        self._dirty = False  # initial load is not dirty
        return d

    def new_pack(self) -> None:
        import copy
        self._data = self._make_dirty_dict(copy.deepcopy(_EMPTY_PACK))
        self._path = None
        self._dirty = False
        _dlog("PackManager.new_pack", "In-memory pack reset")

    def load(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            loaded: dict[str, Any] = json.load(f)
        # Merge with defaults so old files gain new keys
        merged = dict(_EMPTY_PACK)
        merged.update(loaded)
        self._data = self._make_dirty_dict(merged)
        self._path = path
        self._dirty = False
        _dlog("PackManager.load", f"Loaded {path}")

    def save(self, path: str) -> None:
        pack_dir = os.path.dirname(os.path.abspath(path))
        self._relocate_ai_images(pack_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        self._path = path
        self._dirty = False
        _dlog("PackManager.save", f"Saved {path}")

    def _relocate_ai_images(self, pack_dir: str) -> None:
        """Move any AI-generated images from the temp dir into the pack folder."""
        temp_ai = os.path.normcase(
            os.path.join(tempfile.gettempdir(), "snapshot_pack_creator_ai")
        )

        def _move(src: str) -> str:
            if not src:
                return src
            norm = os.path.normcase(os.path.abspath(src))
            if not norm.startswith(temp_ai):
                return src
            dest = os.path.join(pack_dir, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dest):
                shutil.move(src, dest)
                _dlog("PackManager._relocate_ai_images", f"{os.path.basename(src)} → pack dir")
            return dest if os.path.exists(dest) else src

        for entry in self._data.get("photos", []):
            if entry.get("source"):
                entry["source"] = _move(entry["source"])

        for key in ("overlays", "textures", "love_lens_photos"):
            for slot, paths in self._data.get(key, {}).items():
                self._data[key][slot] = [_move(p) for p in paths]

        for entry in self._data.get("events", []):
            if entry.get("source"):
                entry["source"] = _move(entry["source"])

    # ── Convenience accessors ───────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def add_photo(self, entry: dict[str, Any]) -> None:
        self._data.setdefault("photos", []).append(entry)

    def remove_photo(self, index: int) -> None:
        photos: list = self._data.get("photos", [])
        if 0 <= index < len(photos):
            photos.pop(index)
