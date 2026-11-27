"""Tests for app_debug module."""

import importlib
import os
import pytest
import app_debug


@pytest.fixture(autouse=True)
def reset_debug_flag():
    """Ensure the debug flag is off before and after every test."""
    app_debug.set_debug(False)
    yield
    app_debug.set_debug(False)
    if app_debug._log_file is not None:
        app_debug._log_file.close()
        app_debug._log_file = None


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


def test_default_log_path_in_project_root_when_not_frozen():
    path = app_debug.default_log_path()
    assert os.path.basename(path) == "debug.log"
    assert not os.path.dirname(path).endswith("src")


def test_enable_file_logging_writes_entries(tmp_path, capsys):
    log_path = str(tmp_path / "debug.log")
    app_debug.set_debug(True)
    returned_path = app_debug.enable_file_logging(log_path)
    app_debug.dlog("Tag.method", "hello file")
    capsys.readouterr()  # drain stdout, not under test here

    assert returned_path == log_path
    content = open(log_path, encoding="utf-8").read()
    assert "debug log started" in content
    assert "[Tag.method] hello file" in content


def test_enable_file_logging_falls_back_silently_on_bad_path(tmp_path):
    bad_path = str(tmp_path / "no_such_dir" / "debug.log")
    app_debug.set_debug(True)
    app_debug.enable_file_logging(bad_path)
    app_debug.dlog("Tag.method", "should not raise")  # must not raise
    assert app_debug._log_file is None
