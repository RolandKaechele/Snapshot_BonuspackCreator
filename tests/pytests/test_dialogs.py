"""Tests for src/ui/dialogs.py."""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QDialog, QPushButton, QTextEdit, QCheckBox

from ui.dialogs import (
    BaseAppDialog, _ClipboardDialog,
    show_info, show_warning, show_error,
    show_confirm_with_checkbox,
)


# ── BaseAppDialog ────────────────────────────────────────────────────────────

class TestBaseAppDialog:
    def test_window_title(self, qtbot):
        dlg = BaseAppDialog(None, "My Title", level="info")
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "My Title"

    def test_minimum_width(self, qtbot):
        dlg = BaseAppDialog(None, "T", level="info")
        qtbot.addWidget(dlg)
        assert dlg.minimumWidth() == 480

    def test_level_stored(self, qtbot):
        dlg = BaseAppDialog(None, "T", level="error")
        qtbot.addWidget(dlg)
        assert dlg._level == "error"

    def test_level_colors_present(self, qtbot):
        for level in ("info", "warning", "error"):
            dlg = BaseAppDialog(None, "T", level=level)
            qtbot.addWidget(dlg)
            assert level in dlg._LEVEL_COLORS

    def test_add_button_row_close_accepts(self, qtbot):
        dlg = BaseAppDialog(None, "T", level="info")
        qtbot.addWidget(dlg)
        dlg._add_button_row("some text")
        close_btn = dlg.findChild(QPushButton, "primaryButton")
        assert close_btn is not None
        with qtbot.waitSignal(dlg.accepted, timeout=500):
            close_btn.click()

    def test_add_button_row_copy(self, qtbot):
        dlg = BaseAppDialog(None, "T", level="info")
        qtbot.addWidget(dlg)
        dlg._add_button_row("clipboard content")
        buttons = dlg.findChildren(QPushButton)
        copy_btn = next(b for b in buttons if "Clipboard" in b.text())
        copy_btn.click()
        assert QApplication.clipboard().text() == "clipboard content"

    def test_is_qdialog_subclass(self, qtbot):
        dlg = BaseAppDialog(None, "T")
        qtbot.addWidget(dlg)
        assert isinstance(dlg, QDialog)


# ── _ClipboardDialog ─────────────────────────────────────────────────────────

class TestClipboardDialog:
    def test_shows_message_in_textedit(self, qtbot):
        dlg = _ClipboardDialog(None, "T", "hello world", level="info")
        qtbot.addWidget(dlg)
        txt = dlg.findChild(QTextEdit)
        assert txt is not None
        assert txt.toPlainText() == "hello world"

    def test_inherits_base(self, qtbot):
        dlg = _ClipboardDialog(None, "T", "msg", level="warning")
        qtbot.addWidget(dlg)
        assert isinstance(dlg, BaseAppDialog)

    def test_level_warning(self, qtbot):
        dlg = _ClipboardDialog(None, "T", "msg", level="warning")
        qtbot.addWidget(dlg)
        assert dlg._level == "warning"


# ── show_info / show_warning / show_error ────────────────────────────────────

class TestShowHelpers:
    def _stub_exec(self, monkeypatch):
        monkeypatch.setattr(_ClipboardDialog, "exec", lambda self: None)

    def test_show_info_calls_dlog(self, qtbot, monkeypatch):
        self._stub_exec(monkeypatch)
        logged = []
        monkeypatch.setattr("ui.dialogs._dlog", lambda tag, msg: logged.append((tag, msg)))
        show_info(None, "Title", "msg", tag="test.tag")
        assert logged == [("test.tag", "msg")]

    def test_show_warning_calls_dlog(self, qtbot, monkeypatch):
        self._stub_exec(monkeypatch)
        logged = []
        monkeypatch.setattr("ui.dialogs._dlog", lambda tag, msg: logged.append((tag, msg)))
        show_warning(None, "Warn", "bad thing", tag="test.warn")
        assert logged == [("test.warn", "bad thing")]

    def test_show_error_calls_dlog(self, qtbot, monkeypatch):
        self._stub_exec(monkeypatch)
        logged = []
        monkeypatch.setattr("ui.dialogs._dlog", lambda tag, msg: logged.append((tag, msg)))
        show_error(None, "Err", "oops", tag="test.err")
        assert logged[0][0] == "test.err"

    def test_show_error_with_exc_includes_traceback_in_debug(self, qtbot, monkeypatch):
        self._stub_exec(monkeypatch)
        monkeypatch.setattr("ui.dialogs.is_debug", lambda: True)
        shown = []
        original_init = _ClipboardDialog.__init__
        def capture_init(self, parent, title, message, level="info"):
            shown.append(message)
            original_init(self, parent, title, message, level)
        monkeypatch.setattr(_ClipboardDialog, "__init__", capture_init)
        monkeypatch.setattr("ui.dialogs._dlog", lambda *a: None)
        try:
            raise ValueError("test error")
        except ValueError as exc:
            show_error(None, "E", "base msg", exc=exc)
        assert len(shown) == 1
        # In debug mode the traceback is appended
        assert "base msg" in shown[0]

    def test_show_info_default_tag(self, qtbot, monkeypatch):
        self._stub_exec(monkeypatch)
        logged = []
        monkeypatch.setattr("ui.dialogs._dlog", lambda tag, msg: logged.append(tag))
        show_info(None, "MyTitle", "x")
        assert "MyTitle" in logged[0]

    def test_show_error_no_traceback_when_not_debug(self, qtbot, monkeypatch):
        self._stub_exec(monkeypatch)
        monkeypatch.setattr("ui.dialogs.is_debug", lambda: False)
        shown = []
        original_init = _ClipboardDialog.__init__
        def capture_init(self, parent, title, message, level="info"):
            shown.append(message)
            original_init(self, parent, title, message, level)
        monkeypatch.setattr(_ClipboardDialog, "__init__", capture_init)
        monkeypatch.setattr("ui.dialogs._dlog", lambda *a: None)
        try:
            raise ValueError("boom")
        except ValueError as exc:
            show_error(None, "E", "just the message", exc=exc)
        assert shown[0] == "just the message"


# ── show_confirm_with_checkbox ───────────────────────────────────────────────

class TestShowConfirmWithCheckbox:
    def test_returns_false_on_reject(self, qtbot, monkeypatch):
        monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
        proceed, checked = show_confirm_with_checkbox(None, "T", "msg", "do it")
        assert not proceed
        assert not checked

    def test_returns_true_on_accept_unchecked(self, qtbot, monkeypatch):
        monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
        proceed, checked = show_confirm_with_checkbox(None, "T", "msg", "do it")
        assert proceed
        assert not checked

    def test_no_checkbox_when_label_empty(self, qtbot, monkeypatch):
        captured = []
        original_exec = QDialog.exec
        def spy_exec(self):
            captured.append(self.findChildren(QCheckBox))
            return QDialog.DialogCode.Rejected
        monkeypatch.setattr(QDialog, "exec", spy_exec)
        monkeypatch.setattr("ui.dialogs._dlog", lambda *a: None)
        show_confirm_with_checkbox(None, "T", "msg", checkbox_label="")
        assert captured[0] == []

    def test_checkbox_present_when_label_given(self, qtbot, monkeypatch):
        captured_text = []
        def spy_exec(self):
            cbs = self.findChildren(QCheckBox)
            captured_text.extend(cb.text() for cb in cbs)
            return QDialog.DialogCode.Rejected
        monkeypatch.setattr(QDialog, "exec", spy_exec)
        monkeypatch.setattr("ui.dialogs._dlog", lambda *a: None)
        show_confirm_with_checkbox(None, "T", "msg", checkbox_label="Fix it")
        assert captured_text == ["Fix it"]
