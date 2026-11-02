"""Position values restricted to a specific pack_type (City Events / Love Lens)."""

# Position value -> the only pack_type it is valid for.
POSITION_TYPE_RESTRICTIONS: dict[str, str] = {
    "event": "events",
    "hypno": "lovelens",
}


def position_mismatch(position: str, pack_type: str) -> str | None:
    """Return the pack_type *position* is restricted to, when it conflicts with
    the pack's current *pack_type*; otherwise None."""
    restriction = POSITION_TYPE_RESTRICTIONS.get(position)
    if restriction and restriction != pack_type:
        return restriction
    return None
