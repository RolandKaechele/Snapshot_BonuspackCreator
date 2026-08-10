"""Pack Info Widget — pack-level metadata, defaults, and special traits."""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QGroupBox, QFormLayout, QScrollArea,
    QPushButton, QListWidget, QTabWidget, QSizePolicy,
)
from PyQt6.QtGui import QColor, QDesktopServices  # type: ignore
from PyQt6.QtCore import Qt, QUrl, pyqtSignal  # type: ignore

from app_debug import dlog as _dlog
from modules.tooltips import set_tip

if TYPE_CHECKING:
    from modules.pack_manager import PackManager

# Snapshot!-specific value lists
_POSITIONS = [
    "upskirt", "jogger", "xray", "xJogger", "xBench", "xBar",
    "bench", "bar", "yoga", "hole", "bicycle", "photobooth",
    "wc", "gym", "flasher", "window", "angry", "police", "xPolice",
    "remote", "rPolice", "rJogger", "rBench", "event", "hypno",
]
_TYPES = [
    "plain", "stripes", "dots", "frill", "kinky", "shorts", "thong",
    "kimono", "pantyhose", "none", "plug", "piercing", "cum", "nude",
    "flashing", "sex", "topless", "dildo", "mastubrate", "front",
    "back", "goth", "cumMouth", "cumFace", "cumButt", "cumVag", "cumAnal",
]
_COLORS = [
    "white", "pink", "blue", "black", "red", "green", "yellow", "orange",
    "purple", "gray", "brown", "cyan", "none", "wet", "rare", "police", "mod",
]

# Lewd Shores-specific value lists
_LS_POSITIONS = [
    "beachFront", "beachBack", "exposedFront", "exposedBack",
    "wc", "shower", "yoga", "mermaid", "police", "sPolice",
    "angry", "booth", "underwater",
]
_LS_TYPES = [
    "butt view", "back view", "front view", "changing",
    "cameltoe", "flashing", "yoga", "mermaid", "booth", "none",
]
_LS_SPECIALS = [
    "none", "side boob", "loose top", "topless", "nipple slip",
    "nipple view", "nipple exposed", "plug", "wet fabric", "kinky",
    "pussy exposed", "pussy view", "insert finger", "grabbing",
]

_DISCORD_URL = "https://discord.com/invite/KtRr4WSyks"


class PackInfoWidget(QWidget):
    """First tab: pack identity, defaults, special category, and special traits."""

    game_changed = pyqtSignal(str)  # emits "snapshot" or "lewdshores"

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        tabs = QTabWidget()
        tabs.addTab(self._build_identity_tab(), "Identity")
        tabs.addTab(self._build_defaults_tab(), "Defaults")
        tabs.addTab(self._build_category_traits_tab(), "Category & Traits")
        root.addWidget(tabs)

        # wire up show/hide of game-specific fields
        self.game_changed.connect(self._apply_game_visibility)

    # ── Tab builders ──────────────────────────────────────────────────────

    def _build_identity_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 8, 8, 8)

        grp = QGroupBox("Pack Identity")
        form = QFormLayout(grp)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self._edit_id = QLineEdit()
        self._edit_id.setPlaceholderText("e.g. myfirstpack")
        set_tip(self._edit_id, "pack_id")

        self._edit_title = QLineEdit()
        self._edit_title.setPlaceholderText("e.g. My First Pack")
        set_tip(self._edit_title, "pack_title")

        self._cmb_game = QComboBox()
        self._cmb_game.addItems(["Snapshot!", "Lewd Shores"])
        set_tip(self._cmb_game, "pack_game")

        self._cmb_type = QComboBox()
        self._cmb_type.addItems(["Photos", "Events", "Love Lens"])
        set_tip(self._cmb_type, "pack_type")

        # ID Range row: field + Discord button inline
        idrange_row = QHBoxLayout()
        idrange_row.setContentsMargins(0, 0, 0, 0)
        self._edit_idrange = QLineEdit()
        self._edit_idrange.setPlaceholderText("e.g. 100100-100199  (auto-assigned if empty)")
        set_tip(self._edit_idrange, "pack_idrange")
        self._btn_discord = QPushButton("🎮 Get ID on Discord")
        self._btn_discord.setToolTip(
            "Open the Snapshot! Discord server to request\n"
            "a unique ID range for your pack.\n" + _DISCORD_URL
        )
        self._btn_discord.setFixedWidth(160)
        self._btn_discord.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(_DISCORD_URL))
        )
        idrange_row.addWidget(self._edit_idrange, 1)
        idrange_row.addWidget(self._btn_discord)
        idrange_widget = QWidget()
        idrange_widget.setLayout(idrange_row)

        form.addRow("Pack ID:", self._edit_id)
        form.addRow("Title:", self._edit_title)
        form.addRow("Game:", self._cmb_game)
        form.addRow("Pack Type:", self._cmb_type)
        form.addRow("ID Range:", idrange_widget)

        self._edit_id.textChanged.connect(self._save_identity)
        self._edit_title.textChanged.connect(self._save_identity)
        self._cmb_game.currentIndexChanged.connect(self._save_identity)
        self._cmb_type.currentIndexChanged.connect(self._save_identity)
        self._edit_idrange.textChanged.connect(self._save_identity)

        outer.addWidget(grp)
        outer.addStretch()
        return page

    def _build_defaults_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 8, 8, 8)

        grp = QGroupBox("[Defaults] — Applied to photos that don't specify their own values")
        form = QFormLayout(grp)
        self._form_defaults = form

        # ── Snapshot! rows ────────────────────────────────────────────────
        self._cmb_def_pos = QComboBox()
        self._cmb_def_pos.addItems(_POSITIONS)
        set_tip(self._cmb_def_pos, "defaults_position")

        self._cmb_def_type = QComboBox()
        self._cmb_def_type.addItems(_TYPES)
        set_tip(self._cmb_def_type, "defaults_type")

        self._cmb_def_color = QComboBox()
        self._cmb_def_color.addItems(_COLORS)
        set_tip(self._cmb_def_color, "defaults_color")

        form.addRow("Default Position:", self._cmb_def_pos)
        form.addRow("Default Type:", self._cmb_def_type)
        form.addRow("Default Color:", self._cmb_def_color)

        # ── Lewd Shores rows ──────────────────────────────────────────────
        self._cmb_def_photo_pos = QComboBox()
        self._cmb_def_photo_pos.addItems(_LS_POSITIONS)
        set_tip(self._cmb_def_photo_pos, "defaults_position")

        self._cmb_def_ls_type = QComboBox()
        self._cmb_def_ls_type.addItems(_LS_TYPES)
        set_tip(self._cmb_def_ls_type, "defaults_type")

        self._cmb_def_special = QComboBox()
        self._cmb_def_special.addItems(_LS_SPECIALS)
        set_tip(self._cmb_def_special, "defaults_color")

        self._edit_def_category = QLineEdit()
        self._edit_def_category.setPlaceholderText("e.g. swimsuit, mod")
        set_tip(self._edit_def_category, "defaults_position")

        self._edit_def_pack_theme = QLineEdit()
        self._edit_def_pack_theme.setPlaceholderText("e.g. Toy With Me")
        set_tip(self._edit_def_pack_theme, "pack_title")

        # Theme color: swatch + hex + picker
        theme_color_row = QHBoxLayout()
        theme_color_row.setContentsMargins(0, 0, 0, 0)
        self._lbl_theme_color_swatch = QLabel("⬛")
        self._lbl_theme_color_swatch.setFixedWidth(22)
        self._edit_def_theme_color = QLineEdit()
        self._edit_def_theme_color.setPlaceholderText("#1bc2e6")
        self._btn_theme_color_pick = QPushButton("Pick…")
        self._btn_theme_color_pick.setFixedWidth(52)
        self._btn_theme_color_pick.clicked.connect(self._on_pick_theme_color)
        theme_color_row.addWidget(self._lbl_theme_color_swatch)
        theme_color_row.addWidget(self._edit_def_theme_color, 1)
        theme_color_row.addWidget(self._btn_theme_color_pick)
        self._theme_color_widget = QWidget()
        self._theme_color_widget.setLayout(theme_color_row)

        form.addRow("Photo Position:", self._cmb_def_photo_pos)
        form.addRow("Default Type:", self._cmb_def_ls_type)
        form.addRow("Default Special:", self._cmb_def_special)
        form.addRow("Category:", self._edit_def_category)
        form.addRow("Pack Theme:", self._edit_def_pack_theme)
        form.addRow("Theme Color (hex):", self._theme_color_widget)

        # Connect signals
        self._cmb_def_pos.currentIndexChanged.connect(self._save_defaults)
        self._cmb_def_type.currentIndexChanged.connect(self._save_defaults)
        self._cmb_def_color.currentIndexChanged.connect(self._save_defaults)
        self._cmb_def_photo_pos.currentIndexChanged.connect(self._save_defaults)
        self._cmb_def_ls_type.currentIndexChanged.connect(self._save_defaults)
        self._cmb_def_special.currentIndexChanged.connect(self._save_defaults)
        self._edit_def_category.textChanged.connect(self._save_defaults)
        self._edit_def_pack_theme.textChanged.connect(self._save_defaults)
        self._edit_def_theme_color.textChanged.connect(self._on_theme_color_changed)

        outer.addWidget(grp)
        outer.addStretch()
        return page

    def _build_category_traits_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        self._grp_special_category = self._build_special_category_group()
        layout.addWidget(self._grp_special_category)
        layout.addWidget(self._build_special_traits_group())
        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_special_category_group(self) -> QGroupBox:
        grp = QGroupBox("[Special Category] — Optional badge shown on collection cards")
        form = QFormLayout(grp)

        self._edit_cat_label = QLineEdit()
        self._edit_cat_label.setPlaceholderText("e.g. Bikini, Nurse, Fantasy  (leave empty to omit)")
        set_tip(self._edit_cat_label, "special_category")

        # Color row: swatch + hex field + picker button
        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        self._lbl_color_swatch = QLabel("⬛")
        self._lbl_color_swatch.setFixedWidth(22)
        self._edit_cat_color = QLineEdit()
        self._edit_cat_color.setPlaceholderText("#dea3a5")
        set_tip(self._edit_cat_color, "special_category_color")
        self._btn_color_pick = QPushButton("Pick…")
        self._btn_color_pick.setFixedWidth(52)
        self._btn_color_pick.setToolTip("Open colour picker")
        self._btn_color_pick.clicked.connect(self._on_pick_color)
        color_row.addWidget(self._lbl_color_swatch)
        color_row.addWidget(self._edit_cat_color, 1)
        color_row.addWidget(self._btn_color_pick)
        color_widget = QWidget()
        color_widget.setLayout(color_row)

        form.addRow("Category Label:", self._edit_cat_label)
        form.addRow("Badge Color (hex):", color_widget)

        self._edit_cat_label.textChanged.connect(self._save_special_category)
        self._edit_cat_color.textChanged.connect(self._on_color_text_changed)

        return grp

    def _build_special_traits_group(self) -> QGroupBox:
        self._grp_special_traits = QGroupBox("[Special Traits] — Custom type/color aliases")
        grp = self._grp_special_traits
        outer = QVBoxLayout(grp)

        intro = QLabel(
            "Format: Display Label, token, fallback\n"
            "Example:  Nude Beach, nudebeach, nude"
        )
        intro.setWordWrap(True)
        set_tip(intro, "special_traits_intro")
        outer.addWidget(intro)

        self._grp_type_aliases = QGroupBox("specialType aliases")
        types_grp = self._grp_type_aliases
        types_layout = QVBoxLayout(types_grp)
        set_tip(types_grp, "special_types_list")
        self._list_types = QListWidget()
        self._list_types.setMaximumHeight(110)
        types_layout.addWidget(self._list_types)
        types_btn_row = QHBoxLayout()
        self._edit_new_type = QLineEdit()
        self._edit_new_type.setPlaceholderText("Display, token, fallback")
        self._btn_add_type = QPushButton("Add")
        self._btn_add_type.clicked.connect(self._on_add_type)
        self._btn_remove_type = QPushButton("Remove")
        self._btn_remove_type.clicked.connect(self._on_remove_type)
        types_btn_row.addWidget(self._edit_new_type, 1)
        types_btn_row.addWidget(self._btn_add_type)
        types_btn_row.addWidget(self._btn_remove_type)
        types_layout.addLayout(types_btn_row)
        outer.addWidget(types_grp)

        self._grp_color_aliases = QGroupBox("specialColor aliases")
        colors_grp = self._grp_color_aliases
        colors_layout = QVBoxLayout(colors_grp)
        set_tip(colors_grp, "special_colors_list")
        self._list_colors = QListWidget()
        self._list_colors.setMaximumHeight(110)
        colors_layout.addWidget(self._list_colors)
        colors_btn_row = QHBoxLayout()
        self._edit_new_color = QLineEdit()
        self._edit_new_color.setPlaceholderText("Display, token, fallback")
        self._btn_add_color = QPushButton("Add")
        self._btn_add_color.clicked.connect(self._on_add_color)
        self._btn_remove_color = QPushButton("Remove")
        self._btn_remove_color.clicked.connect(self._on_remove_color)
        colors_btn_row.addWidget(self._edit_new_color, 1)
        colors_btn_row.addWidget(self._btn_add_color)
        colors_btn_row.addWidget(self._btn_remove_color)
        colors_layout.addLayout(colors_btn_row)
        outer.addWidget(colors_grp)

        return grp

    # ── Color helpers ─────────────────────────────────────────────────────

    def _on_pick_color(self) -> None:
        from PyQt6.QtWidgets import QColorDialog  # type: ignore
        current = self._edit_cat_color.text().strip()
        initial = QColor(current) if QColor(current).isValid() else QColor("#dea3a5")
        color = QColorDialog.getColor(initial, self, "Pick Badge Color")
        if color.isValid():
            self._edit_cat_color.setText(color.name())

    def _on_color_text_changed(self, text: str) -> None:
        color = QColor(text.strip())
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            self._lbl_color_swatch.setStyleSheet(
                f"color: rgb({r},{g},{b}); font-size: 18px;"
            )
        else:
            self._lbl_color_swatch.setStyleSheet("font-size: 18px;")
        self._save_special_category()

    def _on_pick_theme_color(self) -> None:
        from PyQt6.QtWidgets import QColorDialog  # type: ignore
        current = self._edit_def_theme_color.text().strip()
        initial = QColor(current) if QColor(current).isValid() else QColor("#1bc2e6")
        color = QColorDialog.getColor(initial, self, "Pick Theme Color")
        if color.isValid():
            self._edit_def_theme_color.setText(color.name())

    def _on_theme_color_changed(self, text: str) -> None:
        color = QColor(text.strip())
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            self._lbl_theme_color_swatch.setStyleSheet(
                f"color: rgb({r},{g},{b}); font-size: 18px;"
            )
        else:
            self._lbl_theme_color_swatch.setStyleSheet("font-size: 18px;")
        self._save_defaults()

    # ── Game visibility ───────────────────────────────────────────────────

    def _apply_game_visibility(self, game: str) -> None:
        is_snap = game == "snapshot"
        is_ls = not is_snap

        # Defaults tab rows
        self._form_defaults.setRowVisible(self._cmb_def_pos, is_snap)
        self._form_defaults.setRowVisible(self._cmb_def_type, is_snap)
        self._form_defaults.setRowVisible(self._cmb_def_color, is_snap)
        self._form_defaults.setRowVisible(self._cmb_def_photo_pos, is_ls)
        self._form_defaults.setRowVisible(self._cmb_def_ls_type, is_ls)
        self._form_defaults.setRowVisible(self._cmb_def_special, is_ls)
        self._form_defaults.setRowVisible(self._edit_def_category, is_ls)
        self._form_defaults.setRowVisible(self._edit_def_pack_theme, is_ls)
        self._form_defaults.setRowVisible(self._theme_color_widget, is_ls)

        # Category & Traits tab
        self._grp_special_category.setVisible(is_snap)

        # Update custom traits group title to reflect the ini section name used
        if is_snap:
            self._grp_special_traits.setTitle("[Special Traits] \u2014 Custom type/color aliases")
            self._grp_type_aliases.setTitle("specialType aliases")
            self._grp_color_aliases.setTitle("specialColor aliases")
        else:
            self._grp_special_traits.setTitle("[Create your own traits] \u2014 Custom type/special aliases")
            self._grp_type_aliases.setTitle("newType aliases")
            self._grp_color_aliases.setTitle("newSpecial aliases")



    def _on_add_type(self) -> None:
        val = self._edit_new_type.text().strip()
        if not val:
            return
        self._pm.data.setdefault("special_types", []).append(val)
        self._edit_new_type.clear()
        self._rebuild_traits()
        _dlog("PackInfoWidget._on_add_type", f"Added type alias: {val}")

    def _on_remove_type(self) -> None:
        row = self._list_types.currentRow()
        types: list = self._pm.data.get("special_types", [])
        if 0 <= row < len(types):
            types.pop(row)
        self._rebuild_traits()

    def _on_add_color(self) -> None:
        val = self._edit_new_color.text().strip()
        if not val:
            return
        self._pm.data.setdefault("special_colors", []).append(val)
        self._edit_new_color.clear()
        self._rebuild_traits()
        _dlog("PackInfoWidget._on_add_color", f"Added color alias: {val}")

    def _on_remove_color(self) -> None:
        row = self._list_colors.currentRow()
        colors: list = self._pm.data.get("special_colors", [])
        if 0 <= row < len(colors):
            colors.pop(row)
        self._rebuild_traits()

    # ── Save helpers ──────────────────────────────────────────────────────

    def _save_identity(self) -> None:
        self._pm.set("id", self._edit_id.text().strip())
        self._pm.set("title", self._edit_title.text())
        game = "snapshot" if self._cmb_game.currentIndex() == 0 else "lewdshores"
        self._pm.set("game", game)
        type_map = {0: "photos", 1: "events", 2: "lovelens"}
        self._pm.set("pack_type", type_map.get(self._cmb_type.currentIndex(), "photos"))
        self._pm.set("id_range", self._edit_idrange.text().strip())
        self.game_changed.emit(game)

    def _save_defaults(self) -> None:
        self._pm.set("defaults_position", self._cmb_def_pos.currentText())
        self._pm.set("defaults_type", self._cmb_def_type.currentText())
        self._pm.set("defaults_color", self._cmb_def_color.currentText())
        self._pm.set("defaults_photo_position", self._cmb_def_photo_pos.currentText())
        self._pm.set("defaults_ls_type", self._cmb_def_ls_type.currentText())
        self._pm.set("defaults_special", self._cmb_def_special.currentText())
        self._pm.set("defaults_category", self._edit_def_category.text().strip())
        self._pm.set("defaults_pack_theme", self._edit_def_pack_theme.text().strip())
        self._pm.set("defaults_theme_color", self._edit_def_theme_color.text().strip())

    def _save_special_category(self) -> None:
        self._pm.set("special_category", self._edit_cat_label.text())
        self._pm.set("special_category_color", self._edit_cat_color.text())

    def _rebuild_traits(self) -> None:
        self._list_types.clear()
        for entry in self._pm.data.get("special_types", []):
            self._list_types.addItem(entry)
        self._list_colors.clear()
        for entry in self._pm.data.get("special_colors", []):
            self._list_colors.addItem(entry)

    # ── Refresh ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        for w in (self._edit_id, self._edit_title, self._edit_idrange,
                  self._edit_cat_label, self._edit_cat_color,
                  self._edit_def_category, self._edit_def_pack_theme,
                  self._edit_def_theme_color):
            w.blockSignals(True)
        for w in (self._cmb_game, self._cmb_type,
                  self._cmb_def_pos, self._cmb_def_type, self._cmb_def_color,
                  self._cmb_def_photo_pos, self._cmb_def_ls_type, self._cmb_def_special):
            w.blockSignals(True)

        self._edit_id.setText(self._pm.get("id", ""))
        self._edit_title.setText(self._pm.get("title", ""))

        game = self._pm.get("game", "snapshot")
        self._cmb_game.setCurrentIndex(0 if game == "snapshot" else 1)

        type_map = {"photos": 0, "events": 1, "lovelens": 2}
        self._cmb_type.setCurrentIndex(type_map.get(self._pm.get("pack_type", "photos"), 0))

        self._edit_idrange.setText(self._pm.get("id_range", ""))

        def _set_combo(cmb: QComboBox, val: str) -> None:
            for i in range(cmb.count()):
                if cmb.itemText(i).lower() == val.lower():
                    cmb.setCurrentIndex(i)
                    return

        _set_combo(self._cmb_def_pos, self._pm.get("defaults_position", "upskirt"))
        _set_combo(self._cmb_def_type, self._pm.get("defaults_type", "plain"))
        _set_combo(self._cmb_def_color, self._pm.get("defaults_color", "white"))
        _set_combo(self._cmb_def_photo_pos, self._pm.get("defaults_photo_position", "beachFront"))
        _set_combo(self._cmb_def_ls_type, self._pm.get("defaults_ls_type", "front view"))
        _set_combo(self._cmb_def_special, self._pm.get("defaults_special", "none"))
        self._edit_def_category.setText(self._pm.get("defaults_category", ""))
        self._edit_def_pack_theme.setText(self._pm.get("defaults_pack_theme", ""))
        theme_color_val = self._pm.get("defaults_theme_color", "")
        self._edit_def_theme_color.setText(theme_color_val)

        self._edit_cat_label.setText(self._pm.get("special_category", ""))
        color_val = self._pm.get("special_category_color", "#dea3a5")
        self._edit_cat_color.setText(color_val)

        for w in (self._edit_id, self._edit_title, self._edit_idrange,
                  self._edit_cat_label, self._edit_cat_color,
                  self._edit_def_category, self._edit_def_pack_theme,
                  self._edit_def_theme_color):
            w.blockSignals(False)
        for w in (self._cmb_game, self._cmb_type,
                  self._cmb_def_pos, self._cmb_def_type, self._cmb_def_color,
                  self._cmb_def_photo_pos, self._cmb_def_ls_type, self._cmb_def_special):
            w.blockSignals(False)

        self._on_color_text_changed(color_val)
        self._on_theme_color_changed(theme_color_val)
        self._rebuild_traits()
        self._apply_game_visibility(game)
