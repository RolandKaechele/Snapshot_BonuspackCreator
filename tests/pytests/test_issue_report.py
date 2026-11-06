"""Tests for modules.issue_report — id-range-too-small detection and report rendering."""

from modules.issue_report import (
    detect_id_range_too_small, detect_rare_photo_cap_exceeded, generate_issue_report_markdown,
)


def _pack(id_range: str, photo_count: int, extra: dict | None = None) -> dict:
    data = {
        "id": "mypack",
        "title": "My Pack",
        "game": "snapshot",
        "pack_type": "photos",
        "id_range": id_range,
        "photos": [{"name": f"mypack{i}"} for i in range(photo_count)],
    }
    if extra:
        data.update(extra)
    return data


def test_detect_id_range_too_small_flags_narrow_range():
    data = _pack("100-159", 69)  # width 60, 69 photos
    result = detect_id_range_too_small(data)
    assert result == {"id_range": "100-159", "range_width": 60, "photo_count": 69}


def test_detect_id_range_too_small_ok_when_wide_enough():
    data = _pack("100-199", 69)  # width 100, 69 photos
    assert detect_id_range_too_small(data) is None


def test_detect_id_range_too_small_ignored_without_photos():
    data = _pack("100-109", 0)
    assert detect_id_range_too_small(data) is None


def test_detect_id_range_too_small_ignored_with_invalid_range():
    data = _pack("not-a-range", 5)
    assert detect_id_range_too_small(data) is None


def test_detect_id_range_too_small_skipped_for_multipart_import():
    data = _pack("100-159", 69, extra={"special_types_parts": [[], []]})
    assert detect_id_range_too_small(data) is None


def test_issue_report_includes_id_range_too_small_section():
    data = _pack("100-159", 69)
    report = generate_issue_report_markdown(data)
    assert "## ID Range Too Small" in report
    assert "idrange=100-159" in report
    assert "60 ID(s)" in report
    assert "69 photo(s)" in report


def test_issue_report_no_issues_when_range_wide_enough():
    data = _pack("100-199", 69)
    report = generate_issue_report_markdown(data)
    assert "ID Range Too Small" not in report


# ── detect_rare_photo_cap_exceeded ───────────────────────────────────────────

def _pack_with_colors(colors: list[str], game: str = "snapshot") -> dict:
    return {
        "id": "mypack",
        "title": "My Pack",
        "game": game,
        "pack_type": "photos",
        "id_range": "100-199",
        "photos": [{"name": f"mypack{i}", "color": c} for i, c in enumerate(colors)],
    }


def test_detect_rare_photo_cap_exceeded_flags_over_limit():
    data = _pack_with_colors(["rare", "rare"] + ["white"] * 8)  # limit=1, 2 rare
    result = detect_rare_photo_cap_exceeded(data)
    assert result == {"rare_count": 2, "limit": 1, "photo_count": 10}


def test_detect_rare_photo_cap_exceeded_ok_within_limit():
    data = _pack_with_colors(["rare"] + ["white"] * 9)
    assert detect_rare_photo_cap_exceeded(data) is None


def test_detect_rare_photo_cap_exceeded_ignored_without_photos():
    data = _pack_with_colors([])
    assert detect_rare_photo_cap_exceeded(data) is None


def test_detect_rare_photo_cap_exceeded_ignored_for_lewdshores():
    data = _pack_with_colors(["rare", "rare"] + ["white"] * 8, game="lewdshores")
    assert detect_rare_photo_cap_exceeded(data) is None


def test_detect_rare_photo_cap_exceeded_ignored_for_non_photos_pack_type():
    data = _pack_with_colors(["rare", "rare"] + ["white"] * 8)
    data["pack_type"] = "events"
    assert detect_rare_photo_cap_exceeded(data) is None


def test_issue_report_includes_rare_photo_cap_section():
    data = _pack_with_colors(["rare", "rare"] + ["white"] * 8)
    report = generate_issue_report_markdown(data)
    assert "## Rare Photo Cap Exceeded" in report
    assert "2 photo(s)" in report
    assert "allows 1" in report


def test_issue_report_no_issues_when_rare_within_limit():
    data = _pack_with_colors(["rare"] + ["white"] * 9)
    report = generate_issue_report_markdown(data)
    assert "Rare Photo Cap Exceeded" not in report

