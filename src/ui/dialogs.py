"""Shared dialog helpers with optional Copy-to-Clipboard and dlog support."""

import traceback

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QHBoxLayout,
    QPushButton, QLabel, QWidget, QApplication, QCheckBox,
)
from PyQt6.QtCore import Qt

from app_debug import dlog as _dlog, is_debug


def show_warning(parent: QWidget, title: str, message: str, tag: str = "") -> None:
    _dlog(tag or f"dialog.warning.{title}", message)
    _ClipboardDialog(parent, title, message, level="warning").exec()


def show_error(parent: QWidget, title: str, message: str,
               exc: Exception | None = None, tag: str = "") -> None:
    detail = traceback.format_exc() if exc is not None else ""
    body = f"{message}\n\n{detail}".strip() if (is_debug() and detail) else message
    _dlog(tag or f"dialog.error.{title}", body)
    _ClipboardDialog(parent, title, body, level="error").exec()


def show_info(parent: QWidget, title: str, message: str, tag: str = "") -> None:
    _dlog(tag or f"dialog.info.{title}", message)
    _ClipboardDialog(parent, title, message, level="info").exec()


def show_confirm(parent: QWidget, title: str, message: str, tag: str = "") -> bool:
    """Yes/No question dialog. Returns True when the user clicks Yes."""
    from PyQt6.QtWidgets import QMessageBox  # type: ignore
    _dlog(tag or f"dialog.confirm.{title}", message)
    result = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def show_confirm_with_checkbox(
    parent: QWidget,
    title: str,
    message: str,
    checkbox_label: str,
    tag: str = "",
) -> tuple[bool, bool]:
    """Yes/No dialog with an optional action checkbox.

    Returns (proceed, checkbox_checked).
    """
    _dlog(tag or f"dialog.confirm_cb.{title}", message)
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    layout = QVBoxLayout(dlg)
    lbl = QLabel(message)
    lbl.setWordWrap(True)
    layout.addWidget(lbl)
    cb = QCheckBox(checkbox_label) if checkbox_label else None
    if cb:
        layout.addWidget(cb)
    btn_row = QHBoxLayout()
    btn_yes = QPushButton("Yes")
    btn_no  = QPushButton("No")
    btn_yes.setDefault(True)
    btn_row.addStretch()
    btn_row.addWidget(btn_yes)
    btn_row.addWidget(btn_no)
    layout.addLayout(btn_row)
    btn_yes.clicked.connect(dlg.accept)
    btn_no.clicked.connect(dlg.reject)
    accepted = dlg.exec() == QDialog.DialogCode.Accepted
    return accepted, bool(cb and cb.isChecked())


class BaseAppDialog(QDialog):
    """Base class for all application dialogs.

    Provides the standard minimum width, level-coloured title label, and the
    Copy-to-Clipboard / Close button row.  Subclasses call ``_build_ui`` to
    insert their own content widget between the title label and the button row.
    """

    _LEVEL_COLORS = {
        "error":   "#f38ba8",
        "warning": "#fab387",
        "info":    "#89b4fa",
    }

    def __init__(self, parent: QWidget, title: str, level: str = "info") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self._level = level
        self._title_text = title
        self._layout = QVBoxLayout(self)

        color = self._LEVEL_COLORS.get(level, "#cdd6f4")
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        self._layout.addWidget(lbl)

    def _add_button_row(self, copy_text: str) -> None:
        """Append Copy-to-Clipboard + Close buttons; copy_text is what gets copied."""
        btn_row = QHBoxLayout()
        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(copy_text))
        btn_close = QPushButton("Close")
        btn_close.setObjectName("primaryButton")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        self._layout.addLayout(btn_row)


class _ClipboardDialog(BaseAppDialog):
    """Pre-built dialog: scrollable read-only text body + clipboard button."""

    def __init__(self, parent: QWidget, title: str, message: str,
                 level: str = "info") -> None:
        super().__init__(parent, title, level)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(message)
        txt.setMinimumHeight(80)
        self._layout.addWidget(txt)

        self._add_button_row(message)

