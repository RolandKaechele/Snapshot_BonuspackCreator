"""Tests for dialog_player module helpers (no Qt required)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from modules.dialog_player import _tag_bg, _resolve_image


# ── _tag_bg ───────────────────────────────────────────────────────────────────

def test_tag_bg_known_speaker_you():
    assert _tag_bg("You") == "#1e4d7a"


def test_tag_bg_known_speaker_aya():
    assert _tag_bg("Aya") == "#5a3a7a"


def test_tag_bg_skip_tag():
    assert _tag_bg("SKIP") == "#444444"


def test_tag_bg_new_tags():
    assert _tag_bg("Schoolgirl") == "#7a2a4a"
    assert _tag_bg("Teacher")    == "#4a2a7a"
    assert _tag_bg("Trio")       == "#2a5a3a"


def test_tag_bg_empty_tag():
    assert _tag_bg("") == "#3a3a3a"


def test_tag_bg_unknown_tag_returns_default():
    result = _tag_bg("UnknownSpeaker")
    assert result == "#2a4a2a"


# ── _resolve_image ────────────────────────────────────────────────────────────

def test_resolve_image_finds_png(tmp_path):
    (tmp_path / "scene01.png").write_bytes(b"PNG")
    result = _resolve_image("scene01", str(tmp_path))
    assert result.endswith("scene01.png")


def test_resolve_image_finds_byte_extension(tmp_path):
    (tmp_path / "clip01.byte").write_bytes(b"MP4")
    result = _resolve_image("clip01", str(tmp_path))
    assert result.endswith("clip01.byte")


def test_resolve_image_finds_in_subdir(tmp_path):
    sub = tmp_path / "Data"
    sub.mkdir()
    (sub / "bg01.jpg").write_bytes(b"JPG")
    result = _resolve_image("bg01", str(tmp_path))
    assert result.endswith("bg01.jpg")


def test_resolve_image_returns_empty_when_missing(tmp_path):
    assert _resolve_image("nope", str(tmp_path)) == ""


def test_resolve_image_returns_empty_for_blank_stem(tmp_path):
    assert _resolve_image("", str(tmp_path)) == ""


def test_resolve_image_returns_empty_for_blank_dir():
    assert _resolve_image("scene01", "") == ""
