"""Tests for modules.issue_report — id-range-too-small detection and report rendering."""

from modules.issue_report import detect_id_range_too_small, generate_issue_report_markdown


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
