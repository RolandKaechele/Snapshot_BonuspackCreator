"""Tests for the tooltips module."""

import pytest
from modules.tooltips import TIPS, set_tip, tip


def test_tips_is_nonempty_dict():
    assert isinstance(TIPS, dict)
    assert len(TIPS) > 0


def test_tip_returns_string_for_known_key():
    assert isinstance(tip("pack_id"), str)
    assert len(tip("pack_id")) > 0


def test_tip_returns_empty_string_for_unknown_key():
    assert tip("__nonexistent_key__") == ""


def test_all_tip_values_are_strings():
    for key, value in TIPS.items():
        assert isinstance(value, str), f"TIPS[{key!r}] is not a str"


def test_tip_known_keys_present():
    required_keys = [
        "pack_id", "pack_title", "pack_game", "pack_type", "pack_idrange",
        "defaults_position", "defaults_type", "defaults_color",
        "special_category", "special_category_color",
        "photo_add", "photo_remove", "photo_position", "photo_type", "photo_color",
    ]
    for key in required_keys:
        assert key in TIPS, f"Expected tooltip key missing: {key!r}"


def test_set_tip_attaches_tooltip(qtbot):
    from PyQt6.QtWidgets import QLabel
    widget = QLabel("test")
    set_tip(widget, "pack_id")
    assert widget.toolTip() == TIPS["pack_id"]


def test_set_tip_unknown_key_sets_empty(qtbot):
    from PyQt6.QtWidgets import QLabel
    widget = QLabel("test")
    set_tip(widget, "__unknown__")
    assert widget.toolTip() == ""
