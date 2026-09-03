"""Prompt Editor — edit prompts.json (AI image-generation prompt data) from the Tools menu."""

import json
import os

from PyQt6.QtWidgets import ( #type: ignore
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QWidget, QFileDialog,
    QHeaderView, QComboBox, QPlainTextEdit, QDialogButtonBox,
)

from app_debug import dlog as _dlog
from ui.dialogs import show_error, show_info, show_confirm
from modules import ai_image_gen

# Categories in prompts.json; kept in sync with ai_image_gen._PROMPT_CATEGORIES.
# Sorted alphabetically so tabs appear in a predictable order.
_CATEGORY_KEYS = (
    "EVENT_TYPES", "LEWD_SHORES_PHOTO_MODIFIERS", "LEWD_SHORES_PHOTO_TYPES",
    "LOVE_LENS_OVERLAY_TYPES", "LOVE_LENS_TYPES", "PHOTO_TYPES", "SNAPSHOT_PHOTO_MODIFIERS",
)
_COLUMNS = ("Key", "Label", "Prompt Enhancement", "Negative Prompt")

# Which game a category belongs to; only truly shared categories map to None.
# Love Lens and City Events are Snapshot-only features (see MainWindow._on_game_changed).
_CATEGORY_GAME: dict[str, str | None] = {
    "PHOTO_TYPES": "snapshot",
    "SNAPSHOT_PHOTO_MODIFIERS": "snapshot",
    "LOVE_LENS_TYPES": "snapshot",
    "LOVE_LENS_OVERLAY_TYPES": "snapshot",
    "EVENT_TYPES": "snapshot",
    "LEWD_SHORES_PHOTO_TYPES": "lewdshores",
    "LEWD_SHORES_PHOTO_MODIFIERS": "lewdshores",
}


class PromptEditorDialog(QDialog):
    """Edit the prompts.json file used by the AI Image Generator; saving reloads it live."""

    def __init__(self, parent=None, initial_game: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit AI Prompts")
        self.resize(900, 600)
        self._path = ai_image_gen.default_prompt_file()
        self._data: dict = {}
        self._tables: dict[str, QTableWidget] = {}
        self._build_ui()
        self._load(self._path)
        if initial_game:
            idx = self._cmb_game.findData(initial_game)
            if idx >= 0:
                self._cmb_game.setCurrentIndex(idx)
        self._apply_game_filter()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        path_row = QHBoxLayout()
        self._lbl_path = QLabel()
        self._lbl_path.setWordWrap(True)
        path_row.addWidget(self._lbl_path, 1)
        btn_open = QPushButton("Open…")
        btn_open.clicked.connect(self._on_open)
        path_row.addWidget(btn_open)
        root.addLayout(path_row)

        neg_row = QHBoxLayout()
        neg_row.addWidget(QLabel("Global Negative Prompt:"))
        self._edit_global_negative = QLineEdit()
        neg_row.addWidget(self._edit_global_negative, 1)
        btn_neg_expand = QPushButton("…")
        btn_neg_expand.setFixedWidth(30)
        btn_neg_expand.setToolTip("Edit in a bigger field")
        btn_neg_expand.clicked.connect(self._on_expand_global_negative)
        neg_row.addWidget(btn_neg_expand)
        root.addLayout(neg_row)

        game_row = QHBoxLayout()
        game_row.addWidget(QLabel("Show Tabs For Game:"))
        self._cmb_game = QComboBox()
        self._cmb_game.addItem("All Games", "")
        self._cmb_game.addItem("Snapshot", "snapshot")
        self._cmb_game.addItem("Lewd Shores", "lewdshores")
        self._cmb_game.currentIndexChanged.connect(self._apply_game_filter)
        game_row.addWidget(self._cmb_game)
        game_row.addStretch()
        root.addLayout(game_row)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)
        for key in _CATEGORY_KEYS:
            table = QTableWidget(0, len(_COLUMNS))
            table.setHorizontalHeaderLabels(_COLUMNS)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            table.cellDoubleClicked.connect(
                lambda row, col, k=key: self._on_cell_double_clicked(k, row, col)
            )
            self._tables[key] = table

            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.addWidget(table)
            row_btns = QHBoxLayout()
            btn_add = QPushButton("Add Row")
            btn_add.clicked.connect(lambda _checked=False, k=key: self._on_add_row(k))
            btn_remove = QPushButton("Remove Selected Row")
            btn_remove.clicked.connect(lambda _checked=False, k=key: self._on_remove_row(k))
            row_btns.addWidget(btn_add)
            row_btns.addWidget(btn_remove)
            row_btns.addStretch()
            tab_layout.addLayout(row_btns)
            self._tabs.addTab(tab, key)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_reload = QPushButton("Reload from File")
        btn_reload.clicked.connect(self._on_reload_from_disk)
        btn_row.addWidget(btn_reload)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)
        btn_save_as = QPushButton("Save As…")
        btn_save_as.clicked.connect(self._on_save_as)
        btn_row.addWidget(btn_save_as)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    # ── Load / populate ──────────────────────────────────────────────────

    def _apply_game_filter(self, *_args) -> None:
        game = self._cmb_game.currentData() if hasattr(self, "_cmb_game") else ""
        for i, key in enumerate(_CATEGORY_KEYS):
            cat_game = _CATEGORY_GAME.get(key)
            visible = not game or cat_game is None or cat_game == game
            self._tabs.setTabVisible(i, visible)

    def _load(self, path: str) -> None:
        self._path = path
        self._lbl_path.setText(path)
        try:
            with open(path, encoding="utf-8") as f:
                self._data = json.load(f)
        except Exception as exc:
            _dlog("PromptEditorDialog._load", f"could not load {path!r}: {exc}")
            self._data = {}
        self._edit_global_negative.setText(self._data.get("NEGATIVE_PROMPT", ""))
        for key in _CATEGORY_KEYS:
            self._populate_table(key, self._data.get(key, {}))

    def _populate_table(self, category: str, entries: dict) -> None:
        table = self._tables[category]
        table.setRowCount(0)
        for row_key, info in entries.items():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(row_key))
            table.setItem(row, 1, QTableWidgetItem(info.get("label", "")))
            table.setItem(row, 2, QTableWidgetItem(info.get("prompt_enhancement", "")))
            table.setItem(row, 3, QTableWidgetItem(info.get("negative_prompt", "")))

    def _collect_table(self, category: str) -> dict:
        table = self._tables[category]

        def _text(row: int, col: int) -> str:
            item = table.item(row, col)
            return item.text() if item else ""

        result: dict = {}
        for row in range(table.rowCount()):
            key = _text(row, 0).strip()
            if not key:
                continue
            result[key] = {
                "label": _text(row, 1),
                "prompt_enhancement": _text(row, 2),
                "negative_prompt": _text(row, 3),
            }
        return result

    def _collect_all(self) -> dict:
        data = {"NEGATIVE_PROMPT": self._edit_global_negative.text()}
        for key in _CATEGORY_KEYS:
            data[key] = self._collect_table(key)
        return data

    # ── Big-field editing (double-click) ────────────────────────────────

    def _edit_text_dialog(self, title: str, initial_text: str) -> str | None:
        """Show a resizable multi-line editor; returns the new text or None if cancelled."""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(640, 320)
        layout = QVBoxLayout(dlg)
        editor = QPlainTextEdit(initial_text)
        layout.addWidget(editor)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return editor.toPlainText()
        return None

    def _on_cell_double_clicked(self, category: str, row: int, col: int) -> None:
        if col == 0:
            return  # Key column stays a plain inline edit
        table = self._tables[category]
        item = table.item(row, col)
        current_text = item.text() if item else ""
        new_text = self._edit_text_dialog(f"{category} \u2014 {_COLUMNS[col]}", current_text)
        if new_text is not None:
            if item is None:
                item = QTableWidgetItem()
                table.setItem(row, col, item)
            item.setText(new_text)

    def _on_expand_global_negative(self) -> None:
        new_text = self._edit_text_dialog(
            "Global Negative Prompt", self._edit_global_negative.text()
        )
        if new_text is not None:
            self._edit_global_negative.setText(new_text)

    # ── Button handlers ──────────────────────────────────────────────────

    def _on_add_row(self, category: str) -> None:
        table = self._tables[category]
        row = table.rowCount()
        table.insertRow(row)
        for col in range(len(_COLUMNS)):
            table.setItem(row, col, QTableWidgetItem(""))

    def _on_remove_row(self, category: str) -> None:
        table = self._tables[category]
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for row in rows:
            table.removeRow(row)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Prompts File", os.path.dirname(self._path), "JSON (*.json);;All files (*)"
        )
        if path:
            self._load(path)

    def _on_reload_from_disk(self) -> None:
        if not show_confirm(self, "Reload from File",
                            "Discard unsaved edits and reload from the current file?",
                            tag="PromptEditorDialog._on_reload_from_disk"):
            return
        self._load(self._path)

    def _on_save(self) -> None:
        self._save_to(self._path)

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Prompts File", self._path, "JSON (*.json);;All files (*)"
        )
        if path:
            self._save_to(path)

    def _save_to(self, path: str) -> None:
        data = self._collect_all()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            show_error(self, "Save Failed", str(exc), exc=exc, tag="PromptEditorDialog._save_to")
            return
        self._path = path
        self._lbl_path.setText(path)
        ai_image_gen.reload_prompts(path)
        _dlog("PromptEditorDialog._save_to", f"saved and reloaded prompts from {path!r}")
        show_info(self, "Prompts Saved", f"Saved and reloaded prompts from:\n{path}",
                  tag="PromptEditorDialog._save_to")
