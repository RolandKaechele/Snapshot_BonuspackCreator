"""Cutscene Widget — add, remove, and preview cutscene sequences."""

import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QGroupBox, QFileDialog, QSplitter, QTextEdit, QTabWidget,
)
from PyQt6.QtGui import QPixmap  # type: ignore
from PyQt6.QtCore import Qt  # type: ignore

from app_debug import dlog as _dlog

if TYPE_CHECKING:
    from modules.pack_manager import PackManager


class CutsceneWidget(QWidget):
    """Manages cutscene entries (image sequence + optional JSON metadata)."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._current_frame_idx = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Sequence list + manage buttons (top strip, fixed height)
        list_row = QHBoxLayout()
        self._btn_add = QPushButton("Add Cutscene…")
        self._btn_add.clicked.connect(self._on_add)
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.clicked.connect(self._on_remove)
        self._list = QListWidget()
        self._list.setMaximumHeight(90)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        list_row.addWidget(self._btn_add)
        list_row.addWidget(self._btn_remove)
        list_row.addStretch()
        root.addLayout(list_row)
        root.addWidget(self._list)

        # Detail area in sub-tabs: Preview | Metadata
        self._detail_tabs = QTabWidget()
        root.addWidget(self._detail_tabs, 1)

        # Preview tab
        preview_page = QWidget()
        prev_layout = QVBoxLayout(preview_page)
        prev_layout.setContentsMargins(4, 4, 4, 4)
        self._preview_label = QLabel()
        self._preview_label.setObjectName("imagePlaceholder")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(180)
        self._preview_label.setText("No cutscene selected")
        prev_layout.addWidget(self._preview_label, 1)
        nav_row = QHBoxLayout()
        self._btn_prev_frame = QPushButton("◀ Prev")
        self._btn_prev_frame.clicked.connect(self._on_prev_frame)
        self._lbl_frame = QLabel("Frame 0 / 0")
        self._lbl_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_next_frame = QPushButton("Next ▶")
        self._btn_next_frame.clicked.connect(self._on_next_frame)
        nav_row.addWidget(self._btn_prev_frame)
        nav_row.addWidget(self._lbl_frame, 1)
        nav_row.addWidget(self._btn_next_frame)
        prev_layout.addLayout(nav_row)
        self._detail_tabs.addTab(preview_page, "Preview")

        # Metadata tab
        meta_page = QWidget()
        meta_layout = QVBoxLayout(meta_page)
        meta_layout.setContentsMargins(4, 4, 4, 4)
        self._meta_editor = QTextEdit()
        self._meta_editor.setPlaceholderText("Optional JSON metadata for this cutscene…")
        self._meta_editor.textChanged.connect(self._on_meta_edited)
        meta_layout.addWidget(self._meta_editor)
        self._detail_tabs.addTab(meta_page, "Metadata")

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Cutscene Frames (PNG)", "", "PNG Images (*.png)"
        )
        if not paths:
            return
        cutscenes: list = self._pm.data.setdefault("cutscenes", [])
        name = f"cutscene_{len(cutscenes) + 1}"
        cutscenes.append({"name": name, "frames": paths, "meta": ""})
        self._rebuild_list()
        _dlog("CutsceneWidget._on_add", f"Added cutscene {name} with {len(paths)} frames")

    def _on_remove(self) -> None:
        row = self._list.currentRow()
        cutscenes: list = self._pm.data.get("cutscenes", [])
        if 0 <= row < len(cutscenes):
            cutscenes.pop(row)
        self._rebuild_list()

    def _on_selection_changed(self, row: int) -> None:
        self._current_frame_idx = 0
        self._show_frame()

    def _on_prev_frame(self) -> None:
        self._current_frame_idx = max(0, self._current_frame_idx - 1)
        self._show_frame()

    def _on_next_frame(self) -> None:
        cutscene = self._current_cutscene()
        if cutscene:
            frames = cutscene.get("frames", [])
            self._current_frame_idx = min(len(frames) - 1, self._current_frame_idx + 1)
        self._show_frame()

    def _on_meta_edited(self) -> None:
        cutscene = self._current_cutscene()
        if cutscene is not None:
            cutscene["meta"] = self._meta_editor.toPlainText()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _current_cutscene(self) -> dict | None:
        row = self._list.currentRow()
        cutscenes: list = self._pm.data.get("cutscenes", [])
        if 0 <= row < len(cutscenes):
            return cutscenes[row]
        return None

    def _show_frame(self) -> None:
        cutscene = self._current_cutscene()
        if not cutscene:
            self._preview_label.setText("No cutscene selected")
            self._preview_label.setPixmap(QPixmap())
            self._lbl_frame.setText("Frame 0 / 0")
            self._meta_editor.clear()
            return

        frames: list[str] = cutscene.get("frames", [])
        total = len(frames)
        idx = self._current_frame_idx
        self._lbl_frame.setText(f"Frame {idx + 1 if total else 0} / {total}")

        if total and 0 <= idx < total and os.path.exists(frames[idx]):
            pix = QPixmap(frames[idx])
            self._preview_label.setPixmap(
                pix.scaled(320, 200, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self._preview_label.setPixmap(QPixmap())
            self._preview_label.setText("No preview")

        self._meta_editor.blockSignals(True)
        self._meta_editor.setPlainText(cutscene.get("meta", ""))
        self._meta_editor.blockSignals(False)

    def _rebuild_list(self) -> None:
        cutscenes: list = self._pm.data.get("cutscenes", [])
        self._list.clear()
        for cs in cutscenes:
            frames = cs.get("frames", [])
            self._list.addItem(f"{cs.get('name', '')}  ({len(frames)} frames)")

    def refresh(self) -> None:
        self._rebuild_list()
        self._preview_label.setText("No cutscene selected")
        self._preview_label.setPixmap(QPixmap())
        self._lbl_frame.setText("Frame 0 / 0")
        self._meta_editor.clear()
