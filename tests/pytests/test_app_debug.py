"""Tests for app_debug module."""

import importlib
import pytest
import app_debug


@pytest.fixture(autouse=True)
def reset_debug_flag():
    """Ensure the debug flag is off before and after every test."""
    app_debug.set_debug(False)
    yield
    app_debug.set_debug(False)


def test_is_debug_default_false():
    assert app_debug.is_debug() is False


def test_set_debug_true():
    app_debug.set_debug(True)
    assert app_debug.is_debug() is True


def test_set_debug_false_after_true():
    app_debug.set_debug(True)
    app_debug.set_debug(False)
    assert app_debug.is_debug() is False


def test_dlog_prints_when_enabled(capsys):
    app_debug.set_debug(True)
    app_debug.dlog("Tag.method", "hello world")
    captured = capsys.readouterr()
    assert "[Tag.method] hello world" in captured.out


def test_dlog_silent_when_disabled(capsys):
    app_debug.set_debug(False)
    app_debug.dlog("Tag.method", "should not appear")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_dlog_format(capsys):
    app_debug.set_debug(True)
    app_debug.dlog("MyClass.my_method", "test message")
    captured = capsys.readouterr()
    assert captured.out.strip() == "[MyClass.my_method] test message"
