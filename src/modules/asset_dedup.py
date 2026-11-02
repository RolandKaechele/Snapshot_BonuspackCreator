"""Asset deduplication — hash-compare pack images/audio/video to flag duplicates."""

import hashlib
import os
from typing import Any

from app_debug import dlog as _dlog

_HASH_CHUNK = 1 << 20  # 1 MiB


def _hash_file(path: str) -> str | None:
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(_HASH_CHUNK), b""):
                h.update(chunk)
    except OSError as exc:
        _dlog("asset_dedup._hash_file", f"read failed for {path!r}: {exc}")
        return None
    return h.hexdigest()


def collect_pack_assets(pack_data: dict) -> list[tuple[str, str]]:
    """Return [(label, path), ...] for every asset path referenced by *pack_data*."""
    assets: list[tuple[str, str]] = []
    for photo in pack_data.get("photos", []):
        src = photo.get("source")
        if src:
            assets.append((photo.get("name") or os.path.basename(src), src))
    for event in pack_data.get("events", []):
        src = event.get("source")
        if src:
            assets.append((event.get("name") or os.path.basename(src), src))
    for dict_key in ("overlays", "textures", "love_lens_photos"):
        for slot, paths in pack_data.get(dict_key, {}).items():
            for p in paths:
                if p:
                    assets.append((f"{dict_key}/{slot}", p))
    return assets


def find_duplicate_assets(pack_data: dict) -> list[list[tuple[str, str]]]:
    """Group assets referenced by *pack_data* that share identical file content.

    Returns a list of duplicate groups; each group is a list of (label, path)
    with 2 or more entries sharing the same SHA-256 hash.
    """
    by_hash: dict[str, list[tuple[str, str]]] = {}
    for label, path in collect_pack_assets(pack_data):
        digest = _hash_file(path)
        if digest is None:
            continue
        by_hash.setdefault(digest, []).append((label, path))
    groups = [entries for entries in by_hash.values() if len(entries) > 1]
    groups.sort(key=lambda g: -len(g))
    _dlog("asset_dedup.find_duplicate_assets", f"{len(groups)} duplicate group(s) found")
    return groups
