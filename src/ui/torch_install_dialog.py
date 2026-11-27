"""First-run torch install progress dialog -- see modules/torch_installer.py."""

from PyQt6.QtWidgets import ( #type: ignore
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QWidget,
)
from PyQt6.QtCore import Qt #type: ignore

from app_debug import dlog as _dlog
from modules.torch_installer import TorchInstallWorker

_TAG = "torch_install_dialog"


class TorchInstallDialog(QDialog):
    """Modal, blocking dialog shown on first start while torch is installed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Installing PyTorch")
        self.setMinimumWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.success = False

        layout = QVBoxLayout(self)
        self._label = QLabel(
            "Setting up PyTorch for AI image generation (~2-3 GB, one-time download)…"
        )
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        layout.addWidget(self._log)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_skip = QPushButton("Skip (AI features will be unavailable)")
        self._btn_skip.clicked.connect(self._on_skip)
        self._btn_close = QPushButton("Close")
        self._btn_close.setObjectName("primaryButton")
        self._btn_close.setEnabled(False)
        self._btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_skip)
        btn_row.addWidget(self._btn_close)
        layout.addLayout(btn_row)

        self._worker = TorchInstallWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._worker.isRunning():
            self._worker.start()

    def _on_progress(self, line: str) -> None:
        if line:
            self._log.appendPlainText(line)

    def _on_finished(self, success: bool, message: str) -> None:
        _dlog(_TAG, f"install finished: success={success} message={message}")
        # main.py restarts the whole app in a fresh process on success -- a
        # mid-process importlib.invalidate_caches() isn't reliable enough for
        # torch's native extensions/DLL search paths.
        self.success = success
        self._label.setText(message + (" Restarting…" if success else ""))
        self._btn_skip.setEnabled(False)
        self._btn_close.setEnabled(True)

    def _on_skip(self) -> None:
        _dlog(_TAG, "user skipped torch install")
        self._worker.terminate()
        self.success = False
        self.reject()
