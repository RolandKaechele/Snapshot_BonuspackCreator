"""Tests for modules.warnings_tab — the Warnings tab's pack-warnings aggregation."""

from modules.warnings_tab import _collect_pack_warnings


def _pack(**extra) -> dict:
    data = {
        "id": "mypack",
        "title": "My Pack",
        "game": "snapshot",
        "pack_type": "photos",
        "id_range": "100-199",
        "photos": [],
    }
    data.update(extra)
    return data


def test_collect_pack_warnings_empty_for_clean_pack():
    data = _pack(photos=[{"name": "p0", "position": "upskirt", "color": "white"}])
    assert _collect_pack_warnings(data) == []


def test_collect_pack_warnings_includes_flagged_photo():
    data = _pack(photos=[
        {"name": "p0", "issue_flag": True, "issue_note": "wrong angle"},
    ])
    warnings = _collect_pack_warnings(data)
    assert any("p0" in label for label, _ in warnings)
    assert any("wrong angle" in tip for _, tip in warnings)


def test_collect_pack_warnings_includes_position_mismatch():
    data = _pack(photos=[{"name": "p0", "position": "hypno"}])
    warnings = _collect_pack_warnings(data)
    assert any("mismatch" in label.lower() for label, _ in warnings)


def test_collect_pack_warnings_includes_id_range_too_small():
    data = _pack(
        id_range="100-109",
        photos=[{"name": f"p{i}"} for i in range(20)],
    )
    warnings = _collect_pack_warnings(data)
    assert any("ID Range Too Small" in label for label, _ in warnings)


def test_collect_pack_warnings_includes_rare_cap_exceeded():
    photos = [{"name": f"p{i}", "color": "rare" if i < 2 else "white"} for i in range(10)]
    data = _pack(photos=photos)
    warnings = _collect_pack_warnings(data)
    assert any("Rare Photo Cap Exceeded" in label for label, _ in warnings)
    tip = next(tip for label, tip in warnings if "Rare Photo Cap Exceeded" in label)
    assert "p0" in tip and "p1" in tip
