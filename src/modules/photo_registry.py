"""Photo ID registry — shared helpers for scanning and verifying photo IDs across bonus packs.

A pack reserves a numeric ID range in ``pack.ini`` (``idrange=START-END``); the game assigns
photo IDs sequentially, starting at ``START``, in the order photos are listed in ``[Photos] names``.
The registry (``src/registry.json`` by default) records, for every scanned pack, which photo IDs
are already taken so a new pack's range can be checked for collisions before publishing it.
"""

import json
import os
import re
from typing import Any

_REGISTRY_FILENAME = "registry.json"


def default_registry_path() -> str:
    """Return the default registry file path: ``src/registry.json``."""
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(src_dir, _REGISTRY_FILENAME)


def load_registry(path: str | None = None) -> dict[str, Any]:
    path = path or default_registry_path()
    if not os.path.exists(path):
        return {"entries": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_registry(registry: dict[str, Any], path: str | None = None) -> None:
    path = path or default_registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def parse_id_range(id_range: str) -> tuple[int, int] | None:
    """Parse a ``START-END`` id range string. Returns ``(start, end)`` or ``None`` if invalid.
    For a multi-part pack's combined ``"START1-END1;START2-END2;..."`` string (see
    ``parse_id_ranges()``), only the first segment is parsed."""
    first = (id_range or "").split(";", 1)[0]
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", first)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_id_ranges(id_range: str) -> list[tuple[int, int]]:
    """Parse a ``;``-delimited list of ``START-END`` id ranges (one pack can reserve
    several disjoint ranges when imported from a multi-part/multi-ini pack).
    Returns ``[(start, end), ...]``; invalid/empty segments are skipped."""
    ranges: list[tuple[int, int]] = []
    for segment in (id_range or "").split(";"):
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", segment)
        if m:
            ranges.append((int(m.group(1)), int(m.group(2))))
    return ranges


def compute_photo_ids(id_range: str, photo_names: list[str]) -> list[tuple[int, str]]:
    """Return ``[(photo_id, photo_name), ...]``, IDs assigned sequentially from each
    range's start; once a range is filled, assignment continues from the start of the
    next ``;``-delimited range (if any). Stops once every photo has an ID."""
    ranges = parse_id_ranges(id_range)
    if not ranges:
        return []
    result: list[tuple[int, str]] = []
    idx = 0
    for start, end in ranges:
        for offset in range(max(end - start + 1, 0)):
            if idx >= len(photo_names):
                return result
            result.append((start + offset, photo_names[idx]))
            idx += 1
    return result


def merge_pack_entries(
    registry: dict[str, Any], game_id: str, pack_name: str,
    photo_ids: list[tuple[int, str]], source: str = "",
) -> dict[str, Any]:
    """Replace all registry entries for ``(game_id, pack_name)`` with a freshly scanned set."""
    kept = [
        e for e in registry.get("entries", [])
        if not (e.get("game_id") == game_id and e.get("pack_name") == pack_name)
    ]
    for photo_id, photo_name in photo_ids:
        kept.append({
            "game_id": game_id,
            "pack_name": pack_name,
            "photo_id": photo_id,
            "photo_name": photo_name,
            "source": source,
        })
    kept.sort(key=lambda e: (e["game_id"], e["pack_name"], e["photo_id"]))
    registry["entries"] = kept
    return registry


def find_conflicts(
    registry: dict[str, Any], game_id: str, pack_name: str, photo_ids: list[tuple[int, str]],
) -> list[dict[str, Any]]:
    """Return registry entries whose ``photo_id`` collides with *photo_ids*, excluding *pack_name*."""
    wanted_ids = {photo_id for photo_id, _name in photo_ids}
    conflicts = []
    for entry in registry.get("entries", []):
        if entry.get("game_id") != game_id:
            continue
        if entry.get("pack_name") == pack_name:
            continue
        if entry.get("photo_id") in wanted_ids:
            conflicts.append(entry)
    return conflicts
