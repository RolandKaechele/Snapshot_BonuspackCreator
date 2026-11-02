"""Pack statistics dashboard — counts and warnings for the current pack."""

from collections import Counter


def compute_stats(pack_data: dict) -> dict:
    """Return summary statistics for *pack_data* (Photos tab oriented)."""
    photos = pack_data.get("photos", [])
    positions = Counter(p.get("position", "") for p in photos)
    types = Counter(p.get("type", "") for p in photos)
    colors = Counter(p.get("color", "") for p in photos)
    missing_position = sum(1 for p in photos if not p.get("position"))
    missing_type = sum(1 for p in photos if not p.get("type"))
    thumbnails = sum(1 for p in photos if p.get("thumbnail"))

    events = pack_data.get("events", [])
    dialog_scenes = sum(1 for e in events if e.get("type") == "dialog")

    return {
        "total_photos": len(photos),
        "positions": dict(positions.most_common()),
        "types": dict(types.most_common()),
        "colors": dict(colors.most_common()),
        "missing_position": missing_position,
        "missing_type": missing_type,
        "thumbnails": thumbnails,
        "total_events": len(events),
        "dialog_scenes": dialog_scenes,
    }


def format_stats_report(stats: dict) -> str:
    """Render *stats* (from compute_stats) as a plain-text report."""
    lines = [f"Total photos: {stats['total_photos']}"]
    if stats["missing_position"]:
        lines.append(f"  \u26a0 {stats['missing_position']} photo(s) missing a position")
    if stats["missing_type"]:
        lines.append(f"  \u26a0 {stats['missing_type']} photo(s) missing a type")
    lines.append(f"  Thumbnails set: {stats['thumbnails']}")

    def _section(title: str, counts: dict) -> None:
        if not counts:
            return
        lines.append("")
        lines.append(f"{title}:")
        for key, count in counts.items():
            lines.append(f"  {key or '(blank)'}: {count}")

    _section("By Position", stats["positions"])
    _section("By Type", stats["types"])
    _section("By Color/Special", stats["colors"])

    lines.append("")
    lines.append(f"Total events: {stats['total_events']} ({stats['dialog_scenes']} dialog scene(s))")
    return "\n".join(lines)
