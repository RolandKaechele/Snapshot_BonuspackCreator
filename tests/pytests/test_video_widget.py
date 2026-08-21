"""Tests for video_widget module helpers (no Qt required)."""
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from modules.video_widget import is_video_file, _ms_to_str


# ── is_video_file ─────────────────────────────────────────────────────────────

def _write_mp4(path):
    """Write a minimal file with the MP4 magic bytes at offset 4."""
    with open(path, "wb") as fh:
        fh.write(b"\x00" * 4 + b"ftyp" + b"\x00" * 8)


def test_is_video_file_true_for_mp4_magic(tmp_path):
    p = str(tmp_path / "clip.byte")
    _write_mp4(p)
    assert is_video_file(p) is True


def test_is_video_file_false_for_png(tmp_path):
    p = str(tmp_path / "img.png")
    with open(p, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    assert is_video_file(p) is False


def test_is_video_file_false_for_missing_file(tmp_path):
    assert is_video_file(str(tmp_path / "missing.byte")) is False


def test_is_video_file_false_for_short_file(tmp_path):
    p = str(tmp_path / "tiny.byte")
    p_obj = tmp_path / "tiny.byte"
    p_obj.write_bytes(b"\x00\x01")
    assert is_video_file(str(p_obj)) is False


# ── _ms_to_str ────────────────────────────────────────────────────────────────

def test_ms_to_str_zero():
    assert _ms_to_str(0) == "0:00"


def test_ms_to_str_one_minute():
    assert _ms_to_str(60_000) == "1:00"


def test_ms_to_str_ninety_seconds():
    assert _ms_to_str(90_000) == "1:30"


def test_ms_to_str_sub_second_rounds_down():
    assert _ms_to_str(999) == "0:00"


def test_ms_to_str_large_value():
    assert _ms_to_str(3_723_000) == "62:03"
