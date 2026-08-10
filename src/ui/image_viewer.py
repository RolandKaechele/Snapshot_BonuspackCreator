"""Zoomable image viewer dialog with system-editor launch."""

import os

from PyQt6.QtWidgets import (  # type: ignore
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtGui import QWheelEvent  # type: ignore
from PyQt6.QtCore import Qt, QObject, QEvent  # type: ignore

from app_debug import dlog as _dlog


class _DoubleClickFilter(QObject):
    """Event filter that fires a callback on double-click."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self._cb = callback

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self._cb()
            return True
        return False


def attach_viewer(label: QLabel, get_path) -> None:
    """Install a double-click handler on *label* that opens ImageViewerDialog.

    *get_path* is a zero-argument callable that returns the current image path.
    The filter is owned by *label* so it lives as long as the label does.
    """
    def _open():
        path = get_path()
        if path and os.path.isfile(path):
            ImageViewerDialog(label, path).exec()

    label.installEventFilter(_DoubleClickFilter(label, _open))
    label.setCursor(Qt.CursorShape.PointingHandCursor)


class ImageViewerDialog(QDialog):
    """Full-resolution viewer with zoom and system-editor launch."""

    _MIN_ZOOM = 0.05
    _MAX_ZOOM = 8.0
    _ZOOM_STEP = 0.25

    def __init__(self, parent, path: str) -> None:
        super().__init__(parent)
        self._path = path
        self._zoom = 1.0
        self._pixmap = None
        self.setWindowTitle(os.path.basename(path))
        self.resize(860, 640)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        btn_in   = QPushButton("＋")
        btn_out  = QPushButton("－")
        btn_one  = QPushButton("1:1")
        btn_fit  = QPushButton("Fit")
        for b in (btn_in, btn_out, btn_one, btn_fit):
            b.setFixedWidth(40)
        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setFixedWidth(52)
        btn_edit  = QPushButton("Open in Editor")
        btn_close = QPushButton("Close")
        btn_edit.setToolTip("Open the file with the system default program.")
        toolbar.addWidget(btn_in)
        toolbar.addWidget(btn_out)
        toolbar.addWidget(btn_one)
        toolbar.addWidget(btn_fit)
        toolbar.addWidget(self._lbl_zoom)
        toolbar.addStretch()
        toolbar.addWidget(btn_edit)
        toolbar.addWidget(btn_close)
        layout.addLayout(toolbar)

        self._scroll = QScrollArea()
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._scroll.setWidget(self._img_label)
        self._scroll.setWidgetResizable(False)
        layout.addWidget(self._scroll, 1)

        btn_in.clicked.connect(lambda: self._zoom_by(self._ZOOM_STEP))
        btn_out.clicked.connect(lambda: self._zoom_by(-self._ZOOM_STEP))
        btn_one.clicked.connect(lambda: self._set_zoom(1.0))
        btn_fit.clicked.connect(self._fit)
        btn_edit.clicked.connect(self._open_in_editor)
        btn_close.clicked.connect(self.accept)

    def _load(self) -> None:
        from modules.image_utils import load_pixmap
        self._pixmap = load_pixmap(self._path)
        if self._pixmap.isNull():
            self._img_label.setText(f"Cannot load:\n{self._path}")
        else:
            self._fit()

    def _fit(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return
        vp = self._scroll.viewport()
        w, h = vp.width() - 4, vp.height() - 4
        if self._pixmap.width() > 0:
            self._zoom = min(w / self._pixmap.width(), h / self._pixmap.height())
        self._apply_zoom()

    def _zoom_by(self, delta: float) -> None:
        self._set_zoom(self._zoom + delta)

    def _set_zoom(self, zoom: float) -> None:
        self._zoom = max(self._MIN_ZOOM, min(self._MAX_ZOOM, zoom))
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return
        w = int(self._pixmap.width()  * self._zoom)
        h = int(self._pixmap.height() * self._zoom)
        scaled = self._pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._img_label.setPixmap(scaled)
        self._img_label.resize(scaled.size())
        self._lbl_zoom.setText(f"{int(self._zoom * 100)}%")

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._zoom_by(self._ZOOM_STEP if event.angleDelta().y() > 0
                          else -self._ZOOM_STEP)
            event.accept()
        else:
            super().wheelEvent(event)

    def _open_in_editor(self) -> None:
        try:
            os.startfile(self._path)  # Windows: open with default associated program
            _dlog("ImageViewerDialog", f"Opened in editor: {self._path}")
        except Exception as exc:
            _dlog("ImageViewerDialog", f"startfile failed: {exc}")
