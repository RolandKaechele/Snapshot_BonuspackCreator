"""Tests for StatusbarController."""

import pytest
from unittest.mock import MagicMock, patch

from ui.statusbar import StatusbarController


@pytest.fixture
def mock_bar():
    return MagicMock()


@pytest.fixture
def ctrl(mock_bar):
    with patch("ui.statusbar.QLabel"):
        return StatusbarController(mock_bar)


def test_set_info_calls_show_message(ctrl, mock_bar):
    ctrl.set_info("hello", timeout_ms=2000)
    mock_bar.showMessage.assert_called_once_with("hello", 2000)


def test_set_ok_calls_show_message(ctrl, mock_bar):
    ctrl.set_ok("all good", timeout_ms=3000)
    mock_bar.showMessage.assert_called_once_with("all good", 3000)


def test_set_error_calls_show_message(ctrl, mock_bar):
    ctrl.set_error("fail", timeout_ms=5000)
    mock_bar.showMessage.assert_called_once_with("fail", 5000)


def test_set_info_default_timeout(ctrl, mock_bar):
    ctrl.set_info("msg")
    _, timeout = mock_bar.showMessage.call_args[0]
    assert timeout == 4000


def test_set_ok_default_timeout(ctrl, mock_bar):
    ctrl.set_ok("msg")
    _, timeout = mock_bar.showMessage.call_args[0]
    assert timeout == 4000


def test_set_error_default_timeout(ctrl, mock_bar):
    ctrl.set_error("msg")
    _, timeout = mock_bar.showMessage.call_args[0]
    assert timeout == 6000


def test_clear_calls_clear_message(ctrl, mock_bar):
    ctrl.clear()
    mock_bar.clearMessage.assert_called_once()


def test_set_permanent_sets_label_text(mock_bar):
    label = MagicMock()
    with patch("ui.statusbar.QLabel", return_value=label):
        ctrl = StatusbarController(mock_bar)
    ctrl.set_permanent("v1.0")
    label.setText.assert_called_with("v1.0")
