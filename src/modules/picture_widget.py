"""Picture Widget — add, remove, preview, manage overlay and texture slots."""

import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import ( #type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QListWidget, QListWidgetItem, QComboBox,
    QCheckBox, QFileDialog, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QSizePolicy,
)
from PyQt6.QtGui import QPixmap, QIcon #type: ignore
from PyQt6.QtCore import Qt, QSize #type: ignore

from app_debug import dlog as _dlog
from modules.image_utils import ASSET_FILTER, load_pixmap
from modules.tooltips import set_tip
from ui.image_viewer import attach_viewer

if TYPE_CHECKING:
    from modules.pack_manager import PackManager

# ── Value tables ─────────────────────────────────────────────────────────────

SNAPSHOT_POSITIONS = [
    ("upskirt", "Upskirt Shot"), ("jogger", "Jogger Photo"), ("xray", "X-Ray Upskirt"),
    ("xJogger", "X-Ray Jogger"), ("xBench", "X-Ray Bench"),
    ("xBar", "X-Ray Bar Photo (X-Ray Barstool)"),
    ("bench", "Bench Photo"), ("bar", "Bar Photo (Barstool)"),
    ("photoBooth", "Photo Booth"),
    ("flasher", "Flasher (Yoruko Task)"), ("window", "Window (Yoruko Task)"),
    ("angry", "Busted Photo"), ("police", "Police Upskirt"),
    ("xPolice", "Police X-ray Shot"), ("remote", "Signal Hijacker Upskirt"),
    ("rPolice", "Signal Hijacker Police"), ("rJogger", "Signal Hijacker Jogger"),
    ("rBench", "Signal Hijacker Bench"), ("event", "City Event Photo"),
    ("hypno", "Love Lens Photo"),
]

_DISPLAY_SIZES = [("Standard", 48), ("Large", 80), ("Very Large", 120)]

LEWD_POSITIONS = [
    ("beachBack", "Beach Back"), ("beachFront", "Beach Front"),
    ("exposedBack", "Exposed Back"), ("exposedFront", "Exposed Front"),
    ("wc", "WC"), ("shower", "Shower"), ("yoga", "Yoga"),
    ("mermaid", "Mermaid"), ("police", "Lifeguard"), ("sPolice", "Sitting Lifeguard"),
    ("angry", "Busted"), ("booth", "Booth"), ("underwater", "Underwater"),
]

SNAPSHOT_TYPES = [
    "plain", "stripes", "dots", "frill", "kinky", "none", "plug", "piercing",
    "cum", "nude", "flashing", "sex", "topless", "dildo", "mastubrate",
    "front", "back", "goth",
]

LEWD_TYPES = [
    "butt view", "back view", "front view", "changing", "cameltoe", "flashing",
    "yoga", "mermaid", "booth", "none",
]

SNAPSHOT_COLORS = [
    "pink", "blue", "black", "white", "red", "green", "yellow", "orange",
    "purple", "gray", "brown", "cyan", "none", "wet", "rare", "police",
]

LEWD_SPECIALS = [
    "none", "side boob", "loose top", "topless", "nipple slip", "nipple view",
    "nipple exposed", "plug", "wet fabric", "kinky", "pussy exposed",
    "pussy view", "insert finger", "grabbing",
]

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
    ("body", "Body / skin"),
    ("bodyVagCum", "Body with cum (vagina)"),
    ("bodyAnalCum", "Body with cum (anus)"),
    ("bodyButtCum", "Body with cum (butt)"),
    ("face", "Face"),
    ("faceCumOnFace", "Face with cum (on face)"),
    ("faceCumInMouth", "Face with cum (in mouth)"),
    ("droppedClothTexture", "Dropped Ground Clothes (optional)"),
    ("bodyBraTextures", "Body wearing bra (multi)"),
    ("droppedBraTextures", "Bra dropped on ground (multi)"),
    ("pantyTexture", "Panty (multi)"),
]


class PictureWidget(QWidget):
    """Main photos tab — list of images with per-image trait assignment."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Compact toolbar — buttons sit left, size selector and count sit right
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        self._btn_add = QPushButton("Add…")
        self._btn_add.setFixedWidth(80)
        self._btn_add.clicked.connect(self._on_add_images)
        set_tip(self._btn_add, "photo_add")
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.setFixedWidth(70)
        self._btn_remove.clicked.connect(self._on_remove_selected)
        set_tip(self._btn_remove, "photo_remove")
        self._lbl_count = QLabel("0 images")
        self._cmb_display_size = QComboBox()
        for label, _ in _DISPLAY_SIZES:
            self._cmb_display_size.addItem(label)
        self._cmb_display_size.currentIndexChanged.connect(self._on_display_size_changed)
        toolbar.addWidget(self._btn_add)
        toolbar.addWidget(self._btn_remove)
        toolbar.addStretch()
        toolbar.addWidget(QLabel("Size:"))
        toolbar.addWidget(self._cmb_display_size)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._lbl_count)
        root.addLayout(toolbar)

        # Splitter: list left, detail + preview right
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # Photo list — narrow column; supports multi-selection
        self._list = QListWidget()
        self._list.setMinimumWidth(160)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list)

        # Right panel
        right = QWidget()
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(6)

        # Detail form
        detail_group = QGroupBox("Image Properties")
        form = QFormLayout(detail_group)

        self._cmb_position = QComboBox()
        set_tip(self._cmb_position, "photo_position")
        self._cmb_type = QComboBox()
        set_tip(self._cmb_type, "photo_type")
        self._cmb_color_special = QComboBox()
        set_tip(self._cmb_color_special, "photo_color")

        self._chk_overwrite_type = QCheckBox("Overwrite Type")
        self._edit_overwrite_type = QLineEdit()
        self._edit_overwrite_type.setPlaceholderText("Custom label…")
        self._chk_overwrite_color = QCheckBox("Overwrite Color/Special")
        self._edit_overwrite_color = QLineEdit()
        self._edit_overwrite_color.setPlaceholderText("Custom label…")
        self._chk_thumbnail = QCheckBox("Use as Thumbnail")

        # hypnoType — only meaningful when position=hypno
        self._lbl_hypno_type = QLabel("Love Lens Type:")
        self._cmb_hypno_type = QComboBox()
        self._cmb_hypno_type.addItems([
            "", "topless", "nude", "cumMouth", "cumFace", "cumButt", "cumVag", "cumAnal",
        ])
        set_tip(self._cmb_hypno_type, "photo_hypno_type")
        set_tip(self._lbl_hypno_type, "photo_hypno_type")

        form.addRow("Position:", self._cmb_position)
        form.addRow("Type:", self._cmb_type)
        form.addRow(self._chk_overwrite_type, self._edit_overwrite_type)
        form.addRow("Color / Special:", self._cmb_color_special)
        form.addRow(self._chk_overwrite_color, self._edit_overwrite_color)
        form.addRow(self._lbl_hypno_type, self._cmb_hypno_type)
        form.addRow("", self._chk_thumbnail)

        self._lbl_multi = QLabel("Thumbnail cannot be set for multiple images.")
        self._lbl_multi.setVisible(False)
        form.addRow("", self._lbl_multi)

        self._cmb_position.currentIndexChanged.connect(self._on_position_changed)
        self._cmb_position.currentIndexChanged.connect(self._on_trait_changed)
        self._cmb_type.currentIndexChanged.connect(self._on_trait_changed)
        self._cmb_color_special.currentIndexChanged.connect(self._on_trait_changed)
        self._cmb_hypno_type.currentIndexChanged.connect(self._on_trait_changed)
        self._chk_overwrite_type.toggled.connect(self._on_trait_changed)
        self._edit_overwrite_type.textChanged.connect(self._on_trait_changed)
        self._chk_overwrite_color.toggled.connect(self._on_trait_changed)
        self._edit_overwrite_color.textChanged.connect(self._on_trait_changed)
        self._chk_thumbnail.toggled.connect(self._on_trait_changed)

        right_layout.addWidget(detail_group, 1)

        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_label = QLabel()
        self._preview_label.setObjectName("imagePlaceholder")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(256, 256)
        self._preview_label.setText("No image selected")
        preview_layout.addWidget(self._preview_label)
        self._preview_path: str = ""
        attach_viewer(self._preview_label, lambda: self._preview_path)
        right_layout.addWidget(preview_group, 1)

        splitter.addWidget(right)
        splitter.setSizes([200, 800])

        self._set_detail_enabled(False)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_add_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", ASSET_FILTER
        )
        if not paths:
            return
        existing_sources = {p.get("source") for p in self._pm.data.get("photos", [])}
        for path in paths:
            if path in existing_sources:
                continue
            photos: list = self._pm.data.setdefault("photos", [])
            pack_id = self._pm.get("id") or "photo"
            name = f"{pack_id}{len(photos) + 1}"
            photos.append({
                "name": name,
                "source": path,
                "position": "upskirt",
                "type": "plain",
                "color": "white",
                "overwrite_type": "",
                "overwrite_color": "",
                "thumbnail": False,
            })
        self._rebuild_list()
        _dlog("PictureWidget._on_add_images", f"Added {len(paths)} images")

    def _on_remove_selected(self) -> None:
        rows = sorted(
            [self._list.row(item) for item in self._list.selectedItems()],
            reverse=True,
        )
        if not rows:
            return
        for row in rows:
            self._pm.remove_photo(row)
        self._rebuild_list()

    def _on_selection_changed(self) -> None:
        selected = self._list.selectedItems()
        photos: list = self._pm.data.get("photos", [])
        if not selected:
            self._set_detail_enabled(False)
            self._preview_label.setText("No image selected")
            self._preview_label.setPixmap(QPixmap())
            return
        row = self._list.row(selected[0])
        if row < 0 or row >= len(photos):
            self._set_detail_enabled(False)
            return
        multi = len(selected) > 1
        self._set_detail_enabled(True, multi)
        self._load_detail(photos[row])
        self._load_preview(photos[row].get("source") if not multi else None)

    def _on_position_changed(self) -> None:
        """Show/hide hypnoType row based on whether position==hypno."""
        positions = self._current_positions()
        idx = self._cmb_position.currentIndex()
        is_hypno = (0 <= idx < len(positions) and positions[idx][0] == "hypno")
        self._lbl_hypno_type.setVisible(is_hypno)
        self._cmb_hypno_type.setVisible(is_hypno)

    def _on_trait_changed(self) -> None:
        selected_rows = [self._list.row(item) for item in self._list.selectedItems()]
        photos: list = self._pm.data.get("photos", [])
        if not selected_rows:
            return

        positions = self._current_positions()
        pos_idx = self._cmb_position.currentIndex()
        new_pos = positions[pos_idx][0] if 0 <= pos_idx < len(positions) else None

        types = self._current_types()
        t_idx = self._cmb_type.currentIndex()
        new_type = types[t_idx] if 0 <= t_idx < len(types) else None

        specials = self._current_specials()
        s_idx = self._cmb_color_special.currentIndex()
        new_special = specials[s_idx] if 0 <= s_idx < len(specials) else None

        ht = self._cmb_hypno_type.currentText()
        ow_type = self._edit_overwrite_type.text() if self._chk_overwrite_type.isChecked() else ""
        ow_color = self._edit_overwrite_color.text() if self._chk_overwrite_color.isChecked() else ""

        for row in selected_rows:
            if row < 0 or row >= len(photos):
                continue
            photo = photos[row]
            if new_pos is not None:
                photo["position"] = new_pos
            if new_type is not None:
                photo["type"] = new_type
            if new_special is not None:
                photo["color"] = new_special
            if ht:
                photo["hypnoType"] = ht
            elif "hypnoType" in photo:
                del photo["hypnoType"]
            photo["overwrite_type"] = ow_type
            photo["overwrite_color"] = ow_color

        # Thumbnail only applies when exactly one photo is selected
        if len(selected_rows) == 1:
            photos[selected_rows[0]]["thumbnail"] = self._chk_thumbnail.isChecked()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _current_positions(self):
        return LEWD_POSITIONS if self._pm.get("game") == "lewdshores" else SNAPSHOT_POSITIONS

    def _current_types(self):
        return LEWD_TYPES if self._pm.get("game") == "lewdshores" else SNAPSHOT_TYPES

    def _current_specials(self):
        return LEWD_SPECIALS if self._pm.get("game") == "lewdshores" else SNAPSHOT_COLORS

    def _load_detail(self, photo: dict) -> None:
        positions = self._current_positions()
        types = self._current_types()
        specials = self._current_specials()

        self._cmb_position.blockSignals(True)
        self._cmb_type.blockSignals(True)
        self._cmb_color_special.blockSignals(True)

        self._cmb_position.clear()
        for val, label in positions:
            self._cmb_position.addItem(label, val)
        cur_pos = photo.get("position", "upskirt")
        idx = next((i for i, (v, _) in enumerate(positions) if v == cur_pos), 0)
        self._cmb_position.setCurrentIndex(idx)

        self._cmb_type.clear()
        for t in types:
            self._cmb_type.addItem(t)
        cur_type = photo.get("type", "plain")
        t_idx = types.index(cur_type) if cur_type in types else 0
        self._cmb_type.setCurrentIndex(t_idx)

        self._cmb_color_special.clear()
        for s in specials:
            self._cmb_color_special.addItem(s)
        cur_special = photo.get("color", specials[0])
        s_idx = specials.index(cur_special) if cur_special in specials else 0
        self._cmb_color_special.setCurrentIndex(s_idx)

        ow_type = photo.get("overwrite_type", "")
        self._chk_overwrite_type.setChecked(bool(ow_type))
        self._edit_overwrite_type.setText(ow_type)

        ow_color = photo.get("overwrite_color", "")
        self._chk_overwrite_color.setChecked(bool(ow_color))
        self._edit_overwrite_color.setText(ow_color)

        self._chk_thumbnail.setChecked(bool(photo.get("thumbnail", False)))

        self._cmb_hypno_type.blockSignals(True)
        cur_ht = photo.get("hypnoType", "")
        ht_idx = self._cmb_hypno_type.findText(cur_ht)
        self._cmb_hypno_type.setCurrentIndex(ht_idx if ht_idx >= 0 else 0)
        self._cmb_hypno_type.blockSignals(False)

        self._cmb_position.blockSignals(False)
        self._cmb_type.blockSignals(False)
        self._cmb_color_special.blockSignals(False)

        self._on_position_changed()

    def _load_preview(self, path: str | None) -> None:
        self._preview_path = path or ""
        pix = load_pixmap(path) if path else QPixmap()
        if not pix.isNull():
            self._preview_label.setPixmap(
                pix.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self._preview_label.setPixmap(QPixmap())
            self._preview_label.setText(
                f"Cannot preview:\n{os.path.basename(path)}" if path else "No preview"
            )

    def _on_display_size_changed(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        size_idx = self._cmb_display_size.currentIndex()
        _, icon_px = _DISPLAY_SIZES[size_idx]
        icon_size = QSize(icon_px, icon_px)
        self._list.setIconSize(icon_size)
        if size_idx > 0:
            self._list.setViewMode(QListWidget.ViewMode.IconMode)
            self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
            self._list.setWrapping(True)
            self._list.setWordWrap(True)
            self._list.setSpacing(4)
        else:
            self._list.setViewMode(QListWidget.ViewMode.ListMode)
            self._list.setWrapping(False)
        photos: list = self._pm.data.get("photos", [])
        self._list.clear()
        for photo in photos:
            label = os.path.basename(photo.get("source") or photo.get("name", ""))
            item = QListWidgetItem(label)
            pix = load_pixmap(photo.get("source")) if photo.get("source") else QPixmap()
            if not pix.isNull():
                item.setIcon(QIcon(pix.scaled(
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )))
            self._list.addItem(item)
        self._lbl_count.setText(f"{len(photos)} images")

    def _set_detail_enabled(self, enabled: bool, multi: bool = False) -> None:
        for w in (self._cmb_position, self._cmb_type, self._cmb_color_special,
                  self._chk_overwrite_type, self._edit_overwrite_type,
                  self._chk_overwrite_color, self._edit_overwrite_color,
                  self._cmb_hypno_type):
            w.setEnabled(enabled)
        if not enabled:
            self._lbl_hypno_type.setVisible(False)
            self._cmb_hypno_type.setVisible(False)
        self._chk_thumbnail.setEnabled(enabled and not multi)
        self._lbl_multi.setVisible(enabled and multi)

    def refresh(self) -> None:
        self._rebuild_list()
        self._set_detail_enabled(False)
        self._preview_label.setText("No image selected")
        self._preview_label.setPixmap(QPixmap())
