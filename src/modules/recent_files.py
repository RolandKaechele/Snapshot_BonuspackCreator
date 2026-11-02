"""Recent packs list — persisted small JSON file alongside the photo-ID registry."""

import json
import os

_RECENT_FILENAME = "recent_packs.json"
_MAX_RECENT = 10


def default_recent_path() -> str:
    """Return the default recent-packs file path: ``src/recent_packs.json``."""
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(src_dir, _RECENT_FILENAME)


def load_recent(path: str | None = None) -> list[str]:
    path = path or default_recent_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [p for p in data.get("paths", []) if isinstance(p, str)]
    except (OSError, json.JSONDecodeError):
        return []


def add_recent(pack_path: str, path: str | None = None) -> list[str]:
    """Add *pack_path* to the front of the recent list (deduped), persist, return the list."""
    path = path or default_recent_path()
    recents = [p for p in load_recent(path) if os.path.normcase(p) != os.path.normcase(pack_path)]
    recents.insert(0, pack_path)
    recents = recents[:_MAX_RECENT]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"paths": recents}, f, indent=2, ensure_ascii=False)
    return recents
