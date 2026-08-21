"""Tests for dialog_graph module constants (no Qt required)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from modules.dialog_graph import _TAG_COLORS, _TAG_DEFAULT, _PORTS


# ── _TAG_COLORS ───────────────────────────────────────────────────────────────

def test_tag_colors_contains_new_tags():
    assert "Schoolgirl" in _TAG_COLORS
    assert "Teacher"    in _TAG_COLORS
    assert "Trio"       in _TAG_COLORS


def test_tag_colors_contains_core_speakers():
    for tag in ("You", "Aya", "Boy", "Girl", "Guy", "Old Man", "Punk Guy", "Store Owner", "SKIP"):
        assert tag in _TAG_COLORS, f"Missing tag: {tag!r}"


def test_tag_colors_all_values_are_hex_strings():
    for tag, color in _TAG_COLORS.items():
        assert color.startswith("#"), f"Tag {tag!r} color {color!r} is not a hex string"
        assert len(color) == 7, f"Tag {tag!r} color {color!r} is not 7 chars"


def test_tag_default_is_hex():
    assert _TAG_DEFAULT.startswith("#")
    assert len(_TAG_DEFAULT) == 7


# ── _PORTS ────────────────────────────────────────────────────────────────────

def test_ports_has_three_entries():
    assert len(_PORTS) == 3


def test_ports_names():
    names = [p[0] for p in _PORTS]
    assert names == ["oNPC", "oSet", "oAct"]


def test_ports_labels():
    labels = [p[2] for p in _PORTS]
    assert labels == ["N", "B", "A"]
