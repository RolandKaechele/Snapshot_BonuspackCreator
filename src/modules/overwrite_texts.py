"""Overwrite Texts — editor for the [Hypnosis Text] dialogue section."""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QPlainTextEdit, QSplitter, QInputDialog,
)
from PyQt6.QtCore import Qt  # type: ignore

from app_debug import dlog as _dlog

if TYPE_CHECKING:
    from modules.pack_manager import PackManager

_SECTION_HEADER = "[Hypnosis Text]"
_SECTION_KEY = _SECTION_HEADER.lower()


class OverwriteTextsWidget(QWidget):
    """Two-panel editor: key list left, value text box right."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._entries: list[tuple[str, str]] = []
        self._loading = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        header = QLabel("Overwrite Texts")
        header.setObjectName("sectionLabel")
        root.addWidget(header)

        note = QLabel("Special Category is configured on the Pack Info tab.")
        note.setWordWrap(True)
        root.addWidget(note)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        self._btn_add = QPushButton("Add…")
        self._btn_add.setFixedWidth(70)
        self._btn_add.clicked.connect(self._on_add)
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.setFixedWidth(70)
        self._btn_remove.clicked.connect(self._on_remove)
        self._lbl_count = QLabel("0 entries")
        toolbar.addWidget(self._btn_add)
        toolbar.addWidget(self._btn_remove)
        toolbar.addStretch()
        toolbar.addWidget(self._lbl_count)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        self._key_list = QListWidget()
        self._key_list.setMinimumWidth(180)
        self._key_list.setMaximumWidth(380)
        self._key_list.currentRowChanged.connect(self._on_key_selected)
        splitter.addWidget(self._key_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)
        self._value_edit = QPlainTextEdit()
        self._value_edit.setPlaceholderText("Select a key to edit its text…")
        self._value_edit.setEnabled(False)
        self._value_edit.textChanged.connect(self._on_value_changed)
        right_layout.addWidget(self._value_edit)
        splitter.addWidget(right)

    def _on_add(self) -> None:
        key, ok = QInputDialog.getText(self, "Add Entry", "Key (e.g. hypno_start_mod.0):")
        if not ok or not key.strip():
            return
        key = key.strip()
        self._entries.append((key, ""))
        self._key_list.addItem(key)
        self._lbl_count.setText(f"{len(self._entries)} entries")
        self._key_list.setCurrentRow(len(self._entries) - 1)
        self._save()

    def _on_remove(self) -> None:
        row = self._key_list.currentRow()
        if row < 0:
            return
        self._entries.pop(row)
        self._key_list.takeItem(row)
        self._lbl_count.setText(f"{len(self._entries)} entries")
        self._value_edit.clear()
        self._save()

    def _on_key_selected(self, row: int) -> None:
        self._loading = True
        if 0 <= row < len(self._entries):
            self._value_edit.setPlainText(self._entries[row][1])
            self._value_edit.setEnabled(True)
        else:
            self._value_edit.clear()
            self._value_edit.setEnabled(False)
        self._loading = False

    def _on_value_changed(self) -> None:
        if self._loading:
            return
        row = self._key_list.currentRow()
        if 0 <= row < len(self._entries):
            key = self._entries[row][0]
            self._entries[row] = (key, self._value_edit.toPlainText())
            self._save()

    def _save(self) -> None:
        lines = [f"{k}={v}\n" for k, v in self._entries if k]
        pt: list = self._pm.data.setdefault("passthrough_sections", [])
        for i, (h, _) in enumerate(pt):
            if h.lower() == _SECTION_KEY:
                if lines:
                    pt[i] = (h, lines)
                else:
                    del pt[i]
                _dlog("OverwriteTextsWidget._save", f"{len(lines)} entries")
                return
        if lines:
            pt.append((_SECTION_HEADER, lines))

    def refresh(self) -> None:
        self._loading = True
        self._entries.clear()
        self._key_list.clear()
        self._value_edit.clear()
        self._value_edit.setEnabled(False)

        pt = self._pm.data.get("passthrough_sections", [])
        for h, content_lines in pt:
            if h.lower() == _SECTION_KEY:
                for line in content_lines:
                    s = line.strip()
                    if not s or s.startswith((";", "#")):
                        continue
                    if "=" in s:
                        k, _, v = s.partition("=")
                        self._entries.append((k.strip(), v.strip()))
                        self._key_list.addItem(k.strip())
                break

        self._lbl_count.setText(f"{len(self._entries)} entries")
        self._loading = False
