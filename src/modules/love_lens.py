"""Love Lens Widget — model, hair, accessories, overlay slots, texture slots."""

import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import ( #type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QFormLayout, QPushButton, QSplitter,
    QListWidget, QListWidgetItem, QFileDialog, QLineEdit, QTabWidget,
)
from PyQt6.QtGui import QPixmap  # type: ignore
from PyQt6.QtCore import Qt #type: ignore

from app_debug import dlog as _dlog
from modules.image_utils import ASSET_FILTER, load_pixmap
from modules.tooltips import set_tip
from ui.image_viewer import attach_viewer
from modules.ai_image_gen import open_ai_generate_dialog

if TYPE_CHECKING:
    from modules.pack_manager import PackManager

MODELS = ["Normal", "Slim", "Busty", "Police"]
HAIR_STYLES = ["Default", "Short", "Long", "Pigtails"]
ACCESSORIES = ["None", "Elven Ears"]

OVERLAY_SLOTS = [
    ("overlayStart", "Overlay – Start"),
    ("overlayBoob", "Overlay – Grabbing Breasts"),
    ("overlayPussy", "Overlay – Grabbing Vagina"),
    ("overlayButt", "Overlay – Grabbing Butt"),
    ("overlayVaginalStart", "Overlay – Starting vaginal penetration"),
    ("overlayVaginalPenetration", "Overlay – During vaginal penetration"),
    ("overlayVaginalCum", "Overlay – Cum during vaginal penetration"),
    ("overlayAnalStart", "Overlay – Starting anal penetration"),
    ("overlayAnalPenetration", "Overlay – During anal penetration"),
    ("overlayAnalCum", "Overlay – Cum during anal penetration"),
]

TEXTURE_SLOTS = [
    ("body", "Body / skin", False),
    ("bodyVagCum", "Body with cum (vagina)", False),
    ("bodyAnalCum", "Body with cum (anus)", False),
    ("bodyButtCum", "Body with cum (butt)", False),
    ("face", "Face", False),
    ("faceCumOnFace", "Face with cum (on face)", False),
    ("faceCumInMouth", "Face with cum (in mouth)", False),
    ("droppedClothTexture", "Dropped Ground Clothes (optional)", False),
    ("bodyBraTextures", "Body wearing bra", True),
    ("droppedBraTextures", "Bra dropped on ground", True),
    ("pantyTexture", "Panty", True),
]

PHOTO_TYPES = [
    ("standing_topless", "Photo – Standing topless"),
    ("standing_nude", "Photo – Standing nude"),
    ("kneeling_cum_mouth", "Photo – Kneeling with cum in mouth"),
    ("kneeling_cum_face", "Photo – Kneeling with cum on face"),
    ("leaning_cum_butt", "Photo – Leaning with cum on butt"),
    ("leaning_cum_vagina", "Photo – Leaning with cum in vagina"),
    ("leaning_cum_anus", "Photo – Leaning with cum in anus"),
]


class LoveLensWidget(QWidget):
    """Love Lens editor: character setup, overlays, textures, result photos."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._slot_panels: dict = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        tabs = QTabWidget()
        tabs.addTab(self._build_character_tab(), "Character Setup")
        tabs.addTab(self._build_overlays_tab(), "2D Overlay Slots")
        tabs.addTab(self._build_textures_tab(), "Texture Slots")
        tabs.addTab(self._build_photos_tab(), "Result Photos")
        root.addWidget(tabs)

    def _build_character_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 8, 8, 8)

        char_group = QGroupBox("Character Setup")
        char_form = QFormLayout(char_group)

        self._cmb_model = QComboBox()
        self._cmb_model.addItems(MODELS)
        set_tip(self._cmb_model, "lovelens_model")
        self._cmb_hair = QComboBox()
        self._cmb_hair.addItems(HAIR_STYLES)
        set_tip(self._cmb_hair, "lovelens_hair")
        self._cmb_accessories = QComboBox()
        self._cmb_accessories.addItems(ACCESSORIES)
        set_tip(self._cmb_accessories, "lovelens_accessories")
        self._edit_hair_color = QLineEdit()
        self._edit_hair_color.setPlaceholderText("#ffa6c6")
        set_tip(self._edit_hair_color, "lovelens_hair_color")
        self._edit_eye_color = QLineEdit()
        self._edit_eye_color.setPlaceholderText("#89b4fa")
        set_tip(self._edit_eye_color, "lovelens_eye_color")

        char_form.addRow("Model:", self._cmb_model)
        char_form.addRow("Hair Style:", self._cmb_hair)
        char_form.addRow("Accessories:", self._cmb_accessories)
        char_form.addRow("Hair Color (hex):", self._edit_hair_color)
        char_form.addRow("Eye Color (hex):", self._edit_eye_color)

        for w in (self._cmb_model, self._cmb_hair, self._cmb_accessories,
                  self._edit_hair_color, self._edit_eye_color):
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._save_character)
            else:
                w.textChanged.connect(self._save_character)

        outer.addWidget(char_group)
        outer.addStretch()
        return page

    def _build_slot_tab(self, slots: list, data_key: str, ai_widget_type: str = "") -> QWidget:
        """Master-detail: slot list left | file toolbar + list + preview right."""
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        outer_split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(outer_split, 1)

        # Left: static slot list
        slot_list = QListWidget()
        slot_list.setMinimumWidth(140)
        slot_list.setMaximumWidth(320)
        for s in slots:
            slot_list.addItem(s[1])
        outer_split.addWidget(slot_list)

        # Right: file toolbar + inner splitter (file list | preview)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(4)
        outer_split.addWidget(right)

        file_toolbar = QHBoxLayout()
        file_toolbar.setSpacing(4)
        btn_add = QPushButton("Add…")
        btn_add.setFixedWidth(70)
        btn_rem = QPushButton("Remove")
        btn_rem.setFixedWidth(70)
        btn_up = QPushButton("▲")
        btn_up.setFixedWidth(32)
        btn_dn = QPushButton("▼")
        btn_dn.setFixedWidth(32)
        file_toolbar.addWidget(btn_add)
        file_toolbar.addWidget(btn_rem)
        file_toolbar.addSpacing(8)
        file_toolbar.addWidget(btn_up)
        file_toolbar.addWidget(btn_dn)
        if ai_widget_type:
            btn_ai = QPushButton("AI Generate…")
            btn_ai.setFixedWidth(100)
            file_toolbar.addSpacing(8)
            file_toolbar.addWidget(btn_ai)
        file_toolbar.addStretch()
        right_layout.addLayout(file_toolbar)

        inner_split = QSplitter(Qt.Orientation.Horizontal)
        right_layout.addWidget(inner_split, 1)

        files_list = QListWidget()
        inner_split.addWidget(files_list)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumWidth(120)
        preview.setText("No preview")
        preview.setStyleSheet("background:#1a1a1a;")
        inner_split.addWidget(preview)
        inner_split.setSizes([200, 240])

        def _multi(row: int) -> bool:
            s = slots[row]
            return bool(s[2]) if len(s) > 2 else True

        _cur_path: list[str] = [""]

        attach_viewer(preview, lambda: _cur_path[0])  # mutable cell so resize can reload

        def _load_preview(path: str) -> None:
            _cur_path[0] = path
            px = load_pixmap(path)
            if px.isNull():
                preview.clear()
                preview.setText(
                    f"Cannot preview:\n{os.path.basename(path)}"
                    if os.path.exists(path) else "No preview"
                )
                return
            w = max(preview.width(), 240)
            h = max(preview.height(), 240)
            preview.setText("")
            preview.setPixmap(
                px.scaled(w, h,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
            )

        _orig_resize = preview.resizeEvent

        def _preview_resize(ev):
            _orig_resize(ev)
            if _cur_path[0]:
                _load_preview(_cur_path[0])

        preview.resizeEvent = _preview_resize

        def _on_file_selected(r: int) -> None:
            if r < 0 or r >= files_list.count():
                preview.clear()
                preview.setText("No preview")
                return
            _load_preview(files_list.item(r).data(Qt.ItemDataRole.UserRole))

        def _add_file_item(path: str) -> None:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            files_list.addItem(item)

        def _on_slot(row: int) -> None:
            files_list.clear()
            preview.clear()
            preview.setText("No preview")
            if row < 0:
                return
            key = slots[row][0]
            for p in self._pm.data.get(data_key, {}).get(key, []):
                _add_file_item(p)
            if files_list.count():
                files_list.setCurrentRow(0)

        def _on_add() -> None:
            row = slot_list.currentRow()
            if row < 0:
                return
            if _multi(row):
                paths, _ = QFileDialog.getOpenFileNames(
                    page, "Select Files", "", ASSET_FILTER
                )
            else:
                path, _ = QFileDialog.getOpenFileName(
                    page, "Select File", "", ASSET_FILTER
                )
                paths = [path] if path else []
            if not paths:
                return
            if not _multi(row):
                files_list.clear()
            for p in paths:
                _add_file_item(p)
            files_list.setCurrentRow(files_list.count() - 1)
            _save(row)

        def _on_rem() -> None:
            r = files_list.currentRow()
            if r >= 0:
                files_list.takeItem(r)
                _save(slot_list.currentRow())

        def _on_up() -> None:
            r = files_list.currentRow()
            if r <= 0:
                return
            item = files_list.takeItem(r)
            files_list.insertItem(r - 1, item)
            files_list.setCurrentRow(r - 1)
            _save(slot_list.currentRow())

        def _on_dn() -> None:
            r = files_list.currentRow()
            if r < 0 or r >= files_list.count() - 1:
                return
            item = files_list.takeItem(r)
            files_list.insertItem(r + 1, item)
            files_list.setCurrentRow(r + 1)
            _save(slot_list.currentRow())

        def _save(row: int) -> None:
            if row < 0 or row >= len(slots):
                return
            key = slots[row][0]
            self._pm.data.setdefault(data_key, {})[key] = [
                files_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(files_list.count())
            ]

        slot_list.currentRowChanged.connect(_on_slot)
        files_list.currentRowChanged.connect(_on_file_selected)
        btn_add.clicked.connect(_on_add)
        btn_rem.clicked.connect(_on_rem)
        btn_up.clicked.connect(_on_up)
        btn_dn.clicked.connect(_on_dn)

        if ai_widget_type:
            def _on_ai_add(type_map: dict) -> None:
                row = slot_list.currentRow()
                if row < 0:
                    return
                if not _multi(row):
                    files_list.clear()
                for p in type_map:
                    _add_file_item(p)
                files_list.setCurrentRow(files_list.count() - 1)
                _save(row)

            btn_ai.clicked.connect(
                lambda: open_ai_generate_dialog(
                    page, ai_widget_type, _on_ai_add,
                )
            )

        self._slot_panels[data_key] = (slot_list, files_list, slots)
        return page

    def _build_overlays_tab(self) -> QWidget:
        return self._build_slot_tab(OVERLAY_SLOTS, "overlays", ai_widget_type="love_lens_overlays")

    def _build_textures_tab(self) -> QWidget:
        return self._build_slot_tab(TEXTURE_SLOTS, "textures")

    def _build_photos_tab(self) -> QWidget:
        return self._build_slot_tab(PHOTO_TYPES, "love_lens_photos", ai_widget_type="love_lens")

    # ── Persistence ───────────────────────────────────────────────────────

    def _save_character(self) -> None:
        ll: dict = self._pm.data.setdefault("love_lens", {})
        ll["model"] = self._cmb_model.currentText().lower()
        ll["hairStyle"] = self._cmb_hair.currentText().lower()
        ll["accessories"] = self._cmb_accessories.currentText().lower()
        ll["hairColor"] = self._edit_hair_color.text()
        ll["eyeColor"] = self._edit_eye_color.text()

    def refresh(self) -> None:
        ll: dict = self._pm.get("love_lens", {})

        def _set_combo(cmb: QComboBox, val: str) -> None:
            for i in range(cmb.count()):
                if cmb.itemText(i).lower() == val.lower():
                    cmb.setCurrentIndex(i)
                    return

        _set_combo(self._cmb_model, ll.get("model", "normal"))
        _set_combo(self._cmb_hair, ll.get("hairStyle", "default"))
        _set_combo(self._cmb_accessories, ll.get("accessories", "none"))
        self._edit_hair_color.setText(ll.get("hairColor", ""))
        self._edit_eye_color.setText(ll.get("eyeColor", ""))

        # Reload file list for each slot panel's currently selected slot
        for data_key, (slot_list, files_list, slots) in self._slot_panels.items():
            row = slot_list.currentRow()
            files_list.clear()
            if row >= 0:
                key = slots[row][0]
                for p in self._pm.data.get(data_key, {}).get(key, []):
                    item = QListWidgetItem(os.path.basename(p))
                    item.setData(Qt.ItemDataRole.UserRole, p)
                    files_list.addItem(item)


