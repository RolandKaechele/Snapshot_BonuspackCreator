"""Pack diff/compare — show differences between two pack project JSON files."""

import os
from typing import Any

_SCALAR_KEYS = (
    "title", "id", "id_range", "game", "pack_type",
    "defaults_position", "defaults_type", "defaults_color",
    "special_category", "special_category_color", "event_type",
)


def _photo_key(photo: dict) -> str:
    return photo.get("name") or os.path.basename(photo.get("source") or "")


def _diff_photo_lists(a: list, b: list) -> list[str]:
    lines: list[str] = []
    by_key_a = {_photo_key(p): p for p in a}
    by_key_b = {_photo_key(p): p for p in b}
    added = [k for k in by_key_b if k not in by_key_a]
    removed = [k for k in by_key_a if k not in by_key_b]
    for k in sorted(added):
        lines.append(f"  + photo added: {k}")
    for k in sorted(removed):
        lines.append(f"  - photo removed: {k}")
    for k in sorted(set(by_key_a) & set(by_key_b)):
        pa, pb = by_key_a[k], by_key_b[k]
        changed = [
            f"{field}: {pa.get(field)!r} -> {pb.get(field)!r}"
            for field in ("position", "type", "color", "overwrite_type", "overwrite_color", "thumbnail")
            if pa.get(field) != pb.get(field)
        ]
        if changed:
            lines.append(f"  ~ photo changed: {k}  ({'; '.join(changed)})")
    return lines


def _diff_event_lists(a: list, b: list) -> list[str]:
    lines: list[str] = []
    by_name_a = {e.get("name", ""): e for e in a}
    by_name_b = {e.get("name", ""): e for e in b}
    for name in sorted(set(by_name_b) - set(by_name_a)):
        lines.append(f"  + event added: {name}")
    for name in sorted(set(by_name_a) - set(by_name_b)):
        lines.append(f"  - event removed: {name}")
    for name in sorted(set(by_name_a) & set(by_name_b)):
        ea, eb = by_name_a[name], by_name_b[name]
        if ea.get("content") != eb.get("content") or ea.get("source") != eb.get("source"):
            lines.append(f"  ~ event changed: {name}")
    return lines


def diff_packs(data_a: dict, data_b: dict) -> str:
    """Return a human-readable diff report between two in-app pack JSON documents."""
    lines: list[str] = []

    scalar_changes = [
        f"  {key}: {data_a.get(key)!r} -> {data_b.get(key)!r}"
        for key in _SCALAR_KEYS
        if data_a.get(key) != data_b.get(key)
    ]
    if scalar_changes:
        lines.append("Pack info changes:")
        lines.extend(scalar_changes)

    photo_diffs = _diff_photo_lists(data_a.get("photos", []), data_b.get("photos", []))
    if photo_diffs:
        lines.append("")
        lines.append("Photos:")
        lines.extend(photo_diffs)

    event_diffs = _diff_event_lists(data_a.get("events", []), data_b.get("events", []))
    if event_diffs:
        lines.append("")
        lines.append("Events:")
        lines.extend(event_diffs)

    texts_a, texts_b = data_a.get("texts", {}), data_b.get("texts", {})
    if texts_a != texts_b:
        lines.append("")
        lines.append("Overwrite Texts changed.")

    love_a, love_b = data_a.get("love_lens", {}), data_b.get("love_lens", {})
    if love_a != love_b:
        lines.append("")
        lines.append("Love Lens configuration changed.")

    if not lines:
        return "No differences found."
    return "\n".join(lines)
