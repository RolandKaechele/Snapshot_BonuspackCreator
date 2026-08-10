"""Statusbar controller."""

from PyQt6.QtWidgets import QStatusBar, QLabel #type: ignore
from PyQt6.QtCore import QTimer #type: ignore

from app_debug import dlog as _dlog


class StatusbarController:
    """Wraps QStatusBar with typed helper methods."""

    def __init__(self, bar: QStatusBar) -> None:
        self._bar = bar
        self._permanent = QLabel("")
        bar.addPermanentWidget(self._permanent)

    def set_info(self, message: str, timeout_ms: int = 4000) -> None:
        _dlog("statusbar.set_info", message)
        self._bar.setStyleSheet("")
        self._bar.showMessage(message, timeout_ms)

    def set_ok(self, message: str, timeout_ms: int = 4000) -> None:
        _dlog("statusbar.set_ok", message)
        self._bar.setStyleSheet("QStatusBar { color: #a6e3a1; }")
        self._bar.showMessage(message, timeout_ms)

    def set_error(self, message: str, timeout_ms: int = 6000) -> None:
        _dlog("statusbar.set_error", message)
        self._bar.setStyleSheet("QStatusBar { color: #f38ba8; }")
        self._bar.showMessage(message, timeout_ms)

    def set_permanent(self, message: str) -> None:
        self._permanent.setText(message)

    def clear(self) -> None:
        self._bar.clearMessage()
        self._bar.setStyleSheet("")
