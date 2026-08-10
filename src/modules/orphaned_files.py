"""Orphaned Files tab — shows unreferenced assets in the pack folder.

An asset is "orphaned" when it exists on disk but is not referenced by any
photo, event, overlay, texture, or dialog JSON in the current pack.
A "broken" reference is the inverse: the ini mentions it but the file is absent.
"""

import json
import os
import re
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSplitter, QGroupBox, QPlainTextEdit, QStackedWidget,
)
from PyQt6.QtGui import QIcon, QPixmap, QColor  # type: ignore
from PyQt6.QtCore import Qt, QSize  # type: ignore

from app_debug import dlog as _dlog
from modules.image_utils import ASSET_EXTS, load_pixmap
from ui.image_viewer import attach_viewer

if TYPE_CHECKING:
    from modules.pack_manager import PackManager


# Extensions considered copy-able pack assets (images + dialog JSON)
_IMAGE_EXTS: frozenset[str] = frozenset(ASSET_EXTS) | frozenset([".json"])

# Regex: bare filenames (no path) referenced inside dialog JSON strings
_JSON_ASSET_RE = re.compile(r'"([^"]+\.(?:dat|jpa|pna|png|jpg|jpeg|bytes))"', re.IGNORECASE)


def _collect_referenced(data: dict) -> set[str]:
    """Return the set of lowercase basenames (stem only) that the pack references."""
    refs: set[str] = set()

    def _add(path: str) -> None:
        if path:
            refs.add(os.path.splitext(os.path.basename(path))[0].lower())

    for photo in data.get("photos", []):
        _add(photo.get("source", ""))

    for items in data.get("overlays", {}).values():
        for p in items:
            _add(p)

    for items in data.get("textures", {}).values():
        for p in items:
            _add(p)

    for event in data.get("events", []):
        src = event.get("source", "")
        if src:
            _add(src)
        # parse image filenames out of dialog JSON content
        content = event.get("content", "")
        if content:
            for m in _JSON_ASSET_RE.finditer(content):
                refs.add(os.path.splitext(m.group(1))[0].lower())

    return refs


def _collect_disk_assets(folder: str) -> list[str]:
    """Return full paths of image files inside *folder*/Data/ (or *folder* root)."""
    data_dir = os.path.join(folder, "Data")
    search = data_dir if os.path.isdir(data_dir) else folder
    result = []
    if not os.path.isdir(search):
        return result
    for f in os.listdir(search):
        if os.path.splitext(f)[1].lower() in _IMAGE_EXTS:
            result.append(os.path.join(search, f))
    return result


def _collect_broken(data: dict) -> list[str]:
    """Return basenames (with extension) of referenced files missing from disk."""
    broken: list[str] = []

    def _check(path: str, label: str) -> None:
        if path and not os.path.exists(path):
            broken.append(label or os.path.basename(path))

    for photo in data.get("photos", []):
        _check(photo.get("source", ""), photo.get("name", ""))

    for key, items in data.get("overlays", {}).items():
        for p in items:
            _check(p, os.path.basename(p) if p else "")

    for key, items in data.get("textures", {}).items():
        for p in items:
            _check(p, os.path.basename(p) if p else "")

    for event in data.get("events", []):
        src = event.get("source", "")
        _check(src, event.get("name", "") or os.path.basename(src))

    return broken


def _yellow_icon(size: int = 16) -> QIcon:
    px = QPixmap(size, size)
    px.fill(QColor("#f0c040"))
    return QIcon(px)


class OrphanedFilesWidget(QWidget):
    """Shows orphaned (unreferenced) assets and broken (missing) references."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._folder: str = ""
        self._current_path: str = ""
        self._build_ui()

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: two lists ────────────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Orphaned files list
        orphan_grp = QGroupBox("Orphaned files (on disk, not referenced)")
        orphan_vbox = QVBoxLayout(orphan_grp)
        self._list_orphaned = QListWidget()
        self._list_orphaned.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection)
        self._list_orphaned.currentItemChanged.connect(self._on_selection_changed)
        self._list_orphaned.itemDoubleClicked.connect(self._on_double_click)
        orphan_vbox.addWidget(self._list_orphaned)

        btn_row = QHBoxLayout()
        self._btn_delete = QPushButton("Delete selected from disk")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self._btn_delete)
        btn_row.addStretch()
        orphan_vbox.addLayout(btn_row)

        # Broken references list
        broken_grp = QGroupBox("Broken references (in ini, missing on disk)")
        broken_vbox = QVBoxLayout(broken_grp)
        self._list_broken = QListWidget()
        broken_vbox.addWidget(self._list_broken)

        left_layout.addWidget(orphan_grp, 3)
        left_layout.addWidget(broken_grp, 1)

        # ── Right: preview ─────────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_grp = QGroupBox("Preview")
        preview_vbox = QVBoxLayout(preview_grp)

        self._preview_stack = QStackedWidget()

        self._lbl_preview = QLabel()
        self._lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_preview.setMinimumSize(300, 300)
        self._lbl_preview.setText("Select a file to preview")
        attach_viewer(self._lbl_preview, lambda: self._current_path)
        self._preview_stack.addWidget(self._lbl_preview)  # index 0: image

        self._txt_preview = QPlainTextEdit()
        self._txt_preview.setReadOnly(True)
        self._txt_preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._preview_stack.addWidget(self._txt_preview)  # index 1: text

        preview_vbox.addWidget(self._preview_stack)
        self._lbl_info = QLabel()
        self._lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_vbox.addWidget(self._lbl_info)

        right_layout.addWidget(preview_grp)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

    # ── Public API ──────────────────────────────────────────────────────────

    def refresh(self, folder: str = "") -> None:
        """Repopulate lists from *folder* (pack's source folder on disk)."""
        self._folder = folder
        self._list_orphaned.clear()
        self._list_broken.clear()
        self._lbl_preview.clear()
        self._lbl_preview.setText("Select a file to preview")
        self._txt_preview.clear()
        self._preview_stack.setCurrentIndex(0)
        self._lbl_info.clear()
        self._btn_delete.setEnabled(False)

        if not folder or not os.path.isdir(folder):
            return

        data = self._pm.data
        referenced = _collect_referenced(data)
        disk_files = _collect_disk_assets(folder)

        _dlog("OrphanedFilesWidget.refresh",
              f"folder={folder!r}, referenced={len(referenced)}, disk={len(disk_files)}")

        for path in sorted(disk_files, key=lambda p: os.path.basename(p).lower()):
            stem = os.path.splitext(os.path.basename(path))[0].lower()
            if stem not in referenced:
                item = QListWidgetItem(os.path.basename(path))
                item.setData(Qt.ItemDataRole.UserRole, path)
                self._list_orphaned.addItem(item)

        # Broken references with yellow icon
        yellow = _yellow_icon()
        for label in sorted(set(_collect_broken(data))):
            item = QListWidgetItem(yellow, label)
            self._list_broken.addItem(item)

    def notify_referenced(self, stem: str) -> None:
        """Call when *stem* (filename without extension, any case) becomes referenced.

        Removes the matching item from the orphaned list automatically.
        """
        stem_low = stem.lower()
        for i in range(self._list_orphaned.count() - 1, -1, -1):
            item = self._list_orphaned.item(i)
            path = item.data(Qt.ItemDataRole.UserRole) or ""
            if os.path.splitext(os.path.basename(path))[0].lower() == stem_low:
                self._list_orphaned.takeItem(i)
                _dlog("OrphanedFilesWidget.notify_referenced", f"removed {stem!r}")

    # ── Slots ───────────────────────────────────────────────────────────────

    def _on_selection_changed(self, current: QListWidgetItem, _prev) -> None:
        self._btn_delete.setEnabled(current is not None
                                    and self._list_orphaned.selectedItems() != [])
        if current is None:
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self._show_preview(path)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._show_preview(path)

    def _show_preview(self, path: str) -> None:
        self._current_path = path
        if path.lower().endswith(".json"):
            self._preview_stack.setCurrentIndex(1)
            try:
                raw = open(path, encoding="utf-8", errors="replace").read()
                text = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
            except Exception:
                text = open(path, encoding="utf-8", errors="replace").read()
            self._txt_preview.setPlainText(text)
            self._lbl_info.setText(os.path.basename(path))
            return
        self._preview_stack.setCurrentIndex(0)
        px = load_pixmap(path)
        if px.isNull():
            self._lbl_preview.setText("Cannot preview this file.")
            self._lbl_info.clear()
        else:
            scaled = px.scaled(
                QSize(480, 480),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._lbl_preview.setPixmap(scaled)
            self._lbl_info.setText(
                f"{os.path.basename(path)}  •  {px.width()}×{px.height()}")

    def _on_delete(self) -> None:
        from ui.dialogs import show_warning  # type: ignore
        items = self._list_orphaned.selectedItems()
        if not items:
            return
        names = ", ".join(os.path.basename(
            i.data(Qt.ItemDataRole.UserRole)) for i in items)
        # Confirm before deleting
        from PyQt6.QtWidgets import QMessageBox  # type: ignore
        reply = QMessageBox.question(
            self, "Delete files?",
            f"Permanently delete {len(items)} file(s) from disk?\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for item in items:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    _dlog("OrphanedFilesWidget._on_delete", f"deleted {path!r}")
                except OSError as exc:
                    _dlog("OrphanedFilesWidget._on_delete", f"error: {exc}")
        # Refresh to remove deleted items from list
        self.refresh(self._folder)
