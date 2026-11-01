"""Overwrite Texts — editor for the [Hypnosis Text] dialogue section."""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QPlainTextEdit, QSplitter, QInputDialog, QLineEdit,
)
from PyQt6.QtCore import Qt  # type: ignore

from app_debug import dlog as _dlog

if TYPE_CHECKING:
    from modules.pack_manager import PackManager

_SECTION_HEADER = "[Hypnosis Text]"
_SECTION_KEY = _SECTION_HEADER.lower()

# Default speaker name for a key's paired `key.tag=` field, ported from the
# V2.8 browser prototype's hypnosisDefaultTextOverrides map (its only entry
# with a non-empty default tag).
_DEFAULT_SPEAKER_TAGS = {
    "hypno_start_mod.4": "Woman",
}


class OverwriteTextsWidget(QWidget):
    """Two-panel editor: key list left, value text + speaker tag right."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._entries: list[tuple[str, str]] = []
        self._loading = False
        self._build_ui()

    def _entry_index(self, key: str) -> int:
        return next((i for i, (k, _) in enumerate(self._entries) if k == key), -1)

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

        speaker_row = QHBoxLayout()
        speaker_row.setContentsMargins(0, 0, 0, 0)
        speaker_row.addWidget(QLabel("Speaker:"))
        self._tag_edit = QLineEdit()
        self._tag_edit.setPlaceholderText("(empty for narration)")
        self._tag_edit.setEnabled(False)
        self._tag_edit.textChanged.connect(self._on_tag_changed)
        speaker_row.addWidget(self._tag_edit, 1)
        right_layout.addLayout(speaker_row)

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
        if not key.endswith(".tag"):
            default_tag = _DEFAULT_SPEAKER_TAGS.get(key)
            if default_tag and self._entry_index(f"{key}.tag") < 0:
                self._entries.append((f"{key}.tag", default_tag))
            self._key_list.addItem(key)
            self._key_list.setCurrentRow(self._key_list.count() - 1)
        self._lbl_count.setText(f"{len(self._entries)} entries")
        self._save()

    def _on_remove(self) -> None:
        row = self._key_list.currentRow()
        if row < 0:
            return
        key = self._key_list.item(row).text()
        for lookup in (key, f"{key}.tag"):
            idx = self._entry_index(lookup)
            if idx >= 0:
                self._entries.pop(idx)
        self._key_list.takeItem(row)
        self._lbl_count.setText(f"{len(self._entries)} entries")
        self._value_edit.clear()
        self._tag_edit.clear()
        self._save()

    def _on_key_selected(self, row: int) -> None:
        self._loading = True
        if row >= 0 and row < self._key_list.count():
            key = self._key_list.item(row).text()
            idx = self._entry_index(key)
            self._value_edit.setPlainText(self._entries[idx][1] if idx >= 0 else "")
            self._value_edit.setEnabled(True)
            tag_idx = self._entry_index(f"{key}.tag")
            self._tag_edit.setText(self._entries[tag_idx][1] if tag_idx >= 0 else "")
            self._tag_edit.setEnabled(True)
        else:
            self._value_edit.clear()
            self._value_edit.setEnabled(False)
            self._tag_edit.clear()
            self._tag_edit.setEnabled(False)
        self._loading = False

    def _on_value_changed(self) -> None:
        if self._loading:
            return
        row = self._key_list.currentRow()
        if row < 0:
            return
        key = self._key_list.item(row).text()
        idx = self._entry_index(key)
        if idx >= 0:
            self._entries[idx] = (key, self._value_edit.toPlainText())
            self._save()

    def _on_tag_changed(self, text: str) -> None:
        if self._loading:
            return
        row = self._key_list.currentRow()
        if row < 0:
            return
        key = self._key_list.item(row).text()
        tag_key = f"{key}.tag"
        idx = self._entry_index(tag_key)
        text = text.strip()
        if text:
            if idx >= 0:
                self._entries[idx] = (tag_key, text)
            else:
                self._entries.append((tag_key, text))
        elif idx >= 0:
            self._entries.pop(idx)
        self._lbl_count.setText(f"{len(self._entries)} entries")
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
        self._tag_edit.clear()
        self._tag_edit.setEnabled(False)

        pt = self._pm.data.get("passthrough_sections", [])
        for h, content_lines in pt:
            if h.lower() == _SECTION_KEY:
                for line in content_lines:
                    s = line.strip()
                    if not s or s.startswith((";", "#")):
                        continue
                    if "=" in s:
                        k, _, v = s.partition("=")
                        k = k.strip()
                        self._entries.append((k, v.strip()))
                        if not k.endswith(".tag"):
                            self._key_list.addItem(k)
                break

        self._lbl_count.setText(f"{len(self._entries)} entries")
        self._loading = False
