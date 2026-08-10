"""Event Widget — city-event backgrounds, overlays, and dialog editors."""

import json
import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QFormLayout,
    QComboBox, QTabWidget, QSplitter, QPlainTextEdit, QLineEdit,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate,
)
from PyQt6.QtGui import QPalette  # type: ignore
from PyQt6.QtCore import Qt  # type: ignore

from app_debug import dlog as _dlog
from modules.image_utils import ASSET_FILTER, load_pixmap, resolve_asset
from modules.tooltips import set_tip, tip
from ui.image_viewer import attach_viewer

if TYPE_CHECKING:
    from modules.pack_manager import PackManager

_KNOWN_TAGS = ["", "SKIP", "You", "Aya", "Boy", "Girl", "Guy", "Old Man", "Punk Guy", "Store Owner"]
_KNOWN_CMDS = [
    "", "showImage", "noImage", "showEventPhoto", "noPhoto",
    "noOverlayImage", "mod_overlayImage3", "endEvent",
    "playSound", "stopLoopedSound", "pulseBackground",
    "mascotMoan1", "mascotMoan2", "suckLoop", "mod_addEventSellablePhoto",
]
# Commands whose Argument is an image asset name
_IMAGE_CMDS = {"showImage", "showEventPhoto", "mod_overlayImage3", "mod_addEventSellablePhoto"}


def _paint_as_combo(delegate, painter, option, index):
    """Paint cell using QSS-styled colours, then overlay a ▾ arrow at the right edge."""
    QStyledItemDelegate.paint(delegate, painter, option, index)
    painter.save()
    painter.setPen(option.palette.color(QPalette.ColorRole.Text))
    r = option.rect
    painter.drawText(r.right() - 18, r.top(), 18, r.height(),
                     Qt.AlignmentFlag.AlignCenter, "\u25be")
    painter.restore()


class _ArgDelegate(QStyledItemDelegate):
    """Dropdown editor for the Argument column; options depend on the Command cell."""

    def __init__(self, parent, get_options):
        super().__init__(parent)
        self._get_options = get_options

    def createEditor(self, parent, option, index):
        cmd = index.sibling(index.row(), 0).data() or ""
        c = QComboBox(parent)
        c.setEditable(True)
        c.addItems(self._get_options(cmd))
        return c

    def setEditorData(self, editor, index):
        editor.setCurrentText(index.data() or "")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())

    def paint(self, painter, option, index):
        _paint_as_combo(self, painter, option, index)


class _CmdDelegate(QStyledItemDelegate):
    """Dropdown editor for the Command column of the variables table."""

    def createEditor(self, parent, option, index):
        c = QComboBox(parent)
        c.setEditable(True)
        c.addItems(_KNOWN_CMDS)
        return c

    def setEditorData(self, editor, index):
        editor.setCurrentText(index.data() or "")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())

    def paint(self, painter, option, index):
        _paint_as_combo(self, painter, option, index)


def _extract_nodes(data: dict) -> list:
    """Parse flat nd_* keys from a dialog JSON dict into a list of node dicts."""
    nodes = []
    i = 0
    while f"nd_ID_{i}" in data:
        n_vars = data.get(f"nd_vars{i}", 0)
        variables = [
            {"key": data.get(f"nd_varKey_{i}_{k}", ""), "val": data.get(f"nd_var_{i}_{k}", "")}
            for k in range(n_vars)
        ]
        nodes.append({
            "tag":       data.get(f"nd_tag_{i}", ""),
            "text":      data.get(f"nd_text_{i}", ""),
            "extraData": data.get(f"nd_extraData_{i}", ""),
            "oNPC":      data.get(f"nd_oNPC_{i}", -1),
            "oSet":      data.get(f"nd_oSet_{i}", -1),
            "oAct":      data.get(f"nd_oAct_{i}", -1),
            "expand":    data.get(f"nd_expand_{i}", True),
            "rect":      data.get(f"nd_rect_{i}", [0, 0]),
            "vars":      variables,
        })
        i += 1
    return nodes


def _write_nodes(data: dict, nodes: list) -> None:
    """Replace all nd_* keys in *data* with a freshly serialised node list."""
    for k in [k for k in list(data.keys()) if k.startswith("nd_")]:
        del data[k]
    for i, node in enumerate(nodes):
        data[f"nd_ID_{i}"]        = i
        data[f"nd_tag_{i}"]       = node.get("tag", "")
        data[f"nd_text_{i}"]      = node.get("text", "")
        data[f"nd_extraData_{i}"] = node.get("extraData", "")
        data[f"nd_oNPC_{i}"]      = node.get("oNPC", -1)
        data[f"nd_oSet_{i}"]      = node.get("oSet", -1)
        data[f"nd_oAct_{i}"]      = node.get("oAct", -1)
        data[f"nd_expand_{i}"]    = node.get("expand", True)
        data[f"nd_rect_{i}"]      = node.get("rect", [0, 0])
        vs = node.get("vars", [])
        data[f"nd_vars{i}"] = len(vs)
        for k, v in enumerate(vs):
            data[f"nd_varKey_{i}_{k}"] = v.get("key", "")
            data[f"nd_var_{i}_{k}"]    = v.get("val", "")
    data["npcDiags"]    = sum(1 for n in nodes if n.get("tag", "") != "You")
    data["playerDiags"] = sum(1 for n in nodes if n.get("tag", "") == "You")


def _remap_refs(nodes: list, remap: dict) -> None:
    """Apply an old→new index mapping to all oNPC/oSet/oAct flow references."""
    for node in nodes:
        for field in ("oNPC", "oSet", "oAct"):
            ref = node.get(field, -1)
            if ref in remap:
                node[field] = remap[ref]


def _node_label(idx: int, node: dict) -> str:
    tag  = node.get("tag", "")
    text = node.get("text", "")
    preview = text[:48].replace("\n", " ") + ("…" if len(text) > 48 else "")
    label = f"#{idx}"
    if tag:
        label += f" [{tag}]"
    if preview:
        label += f"  {preview}"
    return label

def validate_events(events: list) -> list:
    """Return [(severity, scene_name, node_idx_or_None, message), ...] for all dialog scenes."""
    import json as _json
    issues = []
    for ev in events:
        if ev.get("type") != "dialog":
            continue
        name = ev.get("name", "?")
        content = ev.get("content", "")
        if not content or not content.strip():
            continue
        try:
            data = _json.loads(content)
        except (_json.JSONDecodeError, ValueError):
            issues.append(("error", name, None, "Invalid JSON content"))
            continue
        nodes = _extract_nodes(data)
        count = len(nodes)
        if count == 0:
            continue
        # Last node must trigger endEvent
        if not any(v.get("key") == "endEvent" for v in nodes[-1].get("vars", [])):
            issues.append(("warning", name, count - 1,
                           "Last node has no endEvent command — the event will not close"))
        for i, node in enumerate(nodes):
            # Flow refs must be -1 or within [0, count-1]
            for field in ("oNPC", "oSet", "oAct"):
                ref = node.get(field, -1)
                if ref != -1 and not (0 <= ref < count):
                    issues.append(("error", name, i,
                                   f"{field}={ref} is out of range (valid: 0–{count - 1})"))

    return issues

class EventWidget(QWidget):
    """Manages city-event backgrounds, overlays, and dialog trees."""

    def __init__(self, pack_manager: "PackManager") -> None:
        super().__init__()
        self._pm = pack_manager
        self._loading = False
        self._current_nodes: list = []
        self._current_dlg_row: int = -1
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        top_row = QHBoxLayout()
        lbl_type = QLabel("Event Type:")
        set_tip(lbl_type, "event_type")
        self._cmb_event_type = QComboBox()
        self._cmb_event_type.addItems(["normal", "explosion"])
        set_tip(self._cmb_event_type, "event_type")
        self._cmb_event_type.currentIndexChanged.connect(self._save_event_type)
        top_row.addWidget(lbl_type)
        top_row.addWidget(self._cmb_event_type)
        top_row.addStretch()
        root.addLayout(top_row)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_image_tab("background"), "Backgrounds")
        self._tabs.addTab(self._build_image_tab("overlay"), "Overlays")
        self._tabs.addTab(self._build_dlg_tab(), "Dialogs")
        root.addWidget(self._tabs)

    def _build_image_tab(self, ev_type: str) -> QWidget:
        """Shared layout for backgrounds/overlays: toolbar + list + preview."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        btn_add = QPushButton("Add…")
        btn_add.setFixedWidth(70)
        btn_rem = QPushButton("Remove")
        btn_rem.setFixedWidth(70)
        btn_up = QPushButton("▲")
        btn_up.setFixedWidth(32)
        btn_dn = QPushButton("▼")
        btn_dn.setFixedWidth(32)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_rem)
        toolbar.addSpacing(8)
        toolbar.addWidget(btn_up)
        toolbar.addWidget(btn_dn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        ev_list = QListWidget()
        ev_list.setMinimumWidth(160)
        ev_list.setMaximumWidth(320)
        splitter.addWidget(ev_list)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setText("No preview")
        preview.setStyleSheet("background:#1a1a1a;")
        splitter.addWidget(preview)
        splitter.setSizes([220, 300])

        cur_path: list = [""]

        attach_viewer(preview, lambda: cur_path[0])

        def _load_preview(path: str) -> None:
            cur_path[0] = path
            px = load_pixmap(path)
            if px.isNull():
                preview.clear()
                preview.setText(
                    f"Cannot preview:\n{os.path.basename(path)}"
                    if path and os.path.exists(path) else "No preview"
                )
                return
            w = max(preview.width(), 240)
            h = max(preview.height(), 240)
            preview.setText("")
            preview.setPixmap(px.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

        _orig_resize = preview.resizeEvent

        def _on_resize(ev):
            _orig_resize(ev)
            if cur_path[0]:
                _load_preview(cur_path[0])

        preview.resizeEvent = _on_resize

        def _on_select(row: int) -> None:
            if row < 0 or row >= ev_list.count():
                preview.clear()
                preview.setText("No preview")
                return
            _load_preview(ev_list.item(row).data(Qt.ItemDataRole.UserRole) or "")

        def _on_add() -> None:
            paths, _ = QFileDialog.getOpenFileNames(page, "Select Files", "", ASSET_FILTER)
            events: list = self._pm.data.setdefault("events", [])
            for path in paths:
                if not any(e.get("type") == ev_type and e.get("source") == path for e in events):
                    events.append({
                        "type": ev_type,
                        "source": path,
                        "name": os.path.splitext(os.path.basename(path))[0],
                    })
                    item = QListWidgetItem(os.path.basename(path))
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    ev_list.addItem(item)
            if ev_list.count():
                ev_list.setCurrentRow(ev_list.count() - 1)

        def _on_rem() -> None:
            row = ev_list.currentRow()
            if row < 0:
                return
            evs = [e for e in self._pm.data.get("events", []) if e.get("type") == ev_type]
            if row < len(evs):
                self._pm.data["events"].remove(evs[row])
            ev_list.takeItem(row)

        def _move(delta: int) -> None:
            row = ev_list.currentRow()
            target = row + delta
            if row < 0 or target < 0 or target >= ev_list.count():
                return
            evs = self._pm.data.get("events", [])
            indices = [i for i, e in enumerate(evs) if e.get("type") == ev_type]
            if row < len(indices) and target < len(indices):
                ia, ib = indices[row], indices[target]
                evs[ia], evs[ib] = evs[ib], evs[ia]
            item = ev_list.takeItem(row)
            ev_list.insertItem(target, item)
            ev_list.setCurrentRow(target)

        ev_list.currentRowChanged.connect(_on_select)
        btn_add.clicked.connect(_on_add)
        btn_rem.clicked.connect(_on_rem)
        btn_up.clicked.connect(lambda: _move(-1))
        btn_dn.clicked.connect(lambda: _move(1))

        if ev_type == "background":
            self._bg_list = ev_list
        else:
            self._ov_list = ev_list

        return page

    def _build_dlg_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Scene-list toolbar
        scene_toolbar = QHBoxLayout()
        scene_toolbar.setSpacing(4)
        btn_scene_add = QPushButton("Add Scene…")
        btn_scene_add.setFixedWidth(90)
        btn_scene_rem = QPushButton("Remove")
        btn_scene_rem.setFixedWidth(70)
        scene_toolbar.addWidget(btn_scene_add)
        scene_toolbar.addWidget(btn_scene_rem)
        scene_toolbar.addStretch()
        layout.addLayout(scene_toolbar)

        outer_split = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(outer_split, 1)

        # Left: dialog scene list
        self._dlg_list = QListWidget()
        self._dlg_list.setMinimumWidth(130)
        self._dlg_list.setMaximumWidth(230)
        outer_split.addWidget(self._dlg_list)

        # Middle: node list + its own toolbar
        node_panel = QWidget()
        node_layout = QVBoxLayout(node_panel)
        node_layout.setContentsMargins(0, 0, 0, 0)
        node_layout.setSpacing(2)

        node_toolbar = QHBoxLayout()
        node_toolbar.setSpacing(4)
        btn_nd_add = QPushButton("Add Node")
        btn_nd_add.setFixedWidth(80)
        btn_nd_rem = QPushButton("Remove")
        btn_nd_rem.setFixedWidth(70)
        btn_nd_up = QPushButton("▲")
        btn_nd_up.setFixedWidth(32)
        btn_nd_dn = QPushButton("▼")
        btn_nd_dn.setFixedWidth(32)
        btn_nd_add.setToolTip("Append a blank dialog node to the end of this scene.")
        btn_nd_rem.setToolTip("Delete the selected node. Flow references to it are reset to -1.")
        btn_nd_up.setToolTip("Move node up. Flow references (Next/Branch/Action) are remapped automatically.")
        btn_nd_dn.setToolTip("Move node down. Flow references (Next/Branch/Action) are remapped automatically.")
        node_toolbar.addWidget(btn_nd_add)
        node_toolbar.addWidget(btn_nd_rem)
        node_toolbar.addSpacing(8)
        node_toolbar.addWidget(btn_nd_up)
        node_toolbar.addWidget(btn_nd_dn)
        node_toolbar.addStretch()
        node_layout.addLayout(node_toolbar)

        self._node_list = QListWidget()
        self._node_list.setMinimumWidth(160)
        self._node_list.setMaximumWidth(320)
        node_layout.addWidget(self._node_list, 1)
        outer_split.addWidget(node_panel)

        # Right: node property form
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_inner = QWidget()
        form_layout = QFormLayout(form_inner)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setSpacing(6)

        self._cmb_tag = QComboBox()
        self._cmb_tag.setEditable(True)
        self._cmb_tag.addItems(_KNOWN_TAGS)
        self._cmb_tag.setToolTip(tip("nd_tag"))
        form_layout.addRow("Speaker:", self._cmb_tag)

        self._edit_text = QPlainTextEdit()
        self._edit_text.setPlaceholderText("Dialogue text…")
        self._edit_text.setMinimumHeight(80)
        self._edit_text.setToolTip(tip("nd_text"))
        form_layout.addRow("Text:", self._edit_text)

        self._edit_extra = QLineEdit()
        self._edit_extra.setToolTip(tip("nd_extraData"))
        form_layout.addRow("Extra Data:", self._edit_extra)

        self._flow_combos: dict = {}
        for field, label, tt_key in [
            ("oNPC", "Next Node:",   "nd_oNPC"),
            ("oSet", "Branch To:",   "nd_oSet"),
            ("oAct", "Action Node:", "nd_oAct"),
        ]:
            cmb = QComboBox()
            cmb.addItem("-1  (none)", -1)
            cmb.setToolTip(tip(tt_key))
            form_layout.addRow(label, cmb)
            self._flow_combos[field] = cmb

        # Variables (command/argument pairs)
        var_hdr = QHBoxLayout()
        var_lbl = QLabel("Commands:")
        var_lbl.setToolTip(tip("nd_vars"))
        btn_var_add = QPushButton("Add")
        btn_var_add.setFixedWidth(50)
        btn_var_rem = QPushButton("Remove")
        btn_var_rem.setFixedWidth(60)
        self._btn_cmd_browse = QPushButton("Browse…")
        self._btn_cmd_browse.setFixedWidth(65)
        self._btn_cmd_browse.setEnabled(False)
        self._btn_cmd_browse.setToolTip(
            "Pick an image file for the selected image command.\n"
            "Stores the asset stem name (no path, no extension) as the game expects."
        )
        btn_var_add.setToolTip("Add a command row to this node.")
        btn_var_rem.setToolTip("Remove the selected command row.")
        var_hdr.addWidget(var_lbl)
        var_hdr.addSpacing(6)
        var_hdr.addWidget(btn_var_add)
        var_hdr.addWidget(btn_var_rem)
        var_hdr.addWidget(self._btn_cmd_browse)
        var_hdr.addStretch()
        form_layout.addRow(var_hdr)

        self._var_table = QTableWidget(0, 2)
        self._var_table.setHorizontalHeaderLabels(["Command", "Argument"])
        self._var_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._var_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._var_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._var_table.setItemDelegateForColumn(0, _CmdDelegate(self._var_table))
        self._var_table.setItemDelegateForColumn(1, _ArgDelegate(self._var_table, self._get_arg_options))
        self._var_table.setMinimumHeight(80)
        self._var_table.setToolTip(tip("nd_vars"))
        form_layout.addRow(self._var_table)

        self._cmd_preview = QLabel()
        self._cmd_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cmd_preview.setMinimumHeight(80)
        self._cmd_preview.setMaximumHeight(130)
        self._cmd_preview.setStyleSheet("background:#1a1a1a;")
        self._cmd_preview_path: str = ""
        attach_viewer(self._cmd_preview, lambda: self._cmd_preview_path)
        form_layout.addRow(self._cmd_preview)

        form_scroll.setWidget(form_inner)
        outer_split.addWidget(form_scroll)
        outer_split.setSizes([170, 240, 380])

        # Wire signals
        self._dlg_list.currentRowChanged.connect(self._on_dialog_selected)
        self._node_list.currentRowChanged.connect(self._on_node_selected)
        self._cmb_tag.currentTextChanged.connect(self._save_node_form)
        self._edit_text.textChanged.connect(self._save_node_form)
        self._edit_extra.textChanged.connect(self._save_node_form)
        for cmb in self._flow_combos.values():
            cmb.currentIndexChanged.connect(self._save_node_form)
        self._var_table.cellChanged.connect(self._save_node_form)
        self._var_table.currentCellChanged.connect(self._on_var_row_selected)

        def _on_scene_add() -> None:
            paths, _ = QFileDialog.getOpenFileNames(
                page, "Select Dialog JSON Files", "", "JSON Files (*.json)")
            events: list = self._pm.data.setdefault("events", [])
            for path in paths:
                if any(e.get("type") == "dialog" and e.get("source") == path
                       for e in events):
                    continue
                try:
                    content = open(path, encoding="utf-8").read()
                except OSError:
                    content = ""
                events.append({
                    "type": "dialog",
                    "source": path,
                    "name": os.path.splitext(os.path.basename(path))[0],
                    "content": content,
                })
                self._dlg_list.addItem(os.path.basename(path))
            if self._dlg_list.count():
                self._dlg_list.setCurrentRow(self._dlg_list.count() - 1)

        def _on_scene_rem() -> None:
            row = self._dlg_list.currentRow()
            if row < 0:
                return
            dlgs = [e for e in self._pm.data.get("events", [])
                    if e.get("type") == "dialog"]
            if row < len(dlgs):
                self._pm.data["events"].remove(dlgs[row])
            self._dlg_list.takeItem(row)
            self._current_nodes = []
            self._current_dlg_row = -1
            self._node_list.clear()

        def _on_node_add() -> None:
            if self._current_dlg_row < 0:
                return
            new_idx = len(self._current_nodes)
            self._current_nodes.append({
                "tag": "", "text": "", "extraData": "",
                "oNPC": -1, "oSet": -1, "oAct": -1,
                "expand": True, "rect": [0, 0], "vars": [],
            })
            self._serialize_dialog()
            item = QListWidgetItem(_node_label(new_idx, self._current_nodes[-1]))
            item.setData(Qt.ItemDataRole.UserRole, new_idx)
            self._node_list.addItem(item)
            self._node_list.setCurrentRow(self._node_list.count() - 1)

        def _on_node_rem() -> None:
            row = self._node_list.currentRow()
            if row < 0 or row >= len(self._current_nodes) or self._current_dlg_row < 0:
                return
            self._current_nodes.pop(row)
            # refs == removed index → -1; refs > removed → decremented
            remap = {i: i - 1 for i in range(row + 1, len(self._current_nodes) + 1)}
            remap[row] = -1
            _remap_refs(self._current_nodes, remap)
            self._serialize_dialog()
            self._rebuild_node_list(keep_row=min(row, len(self._current_nodes) - 1))

        def _on_node_move(delta: int) -> None:
            row = self._node_list.currentRow()
            target = row + delta
            if row < 0 or target < 0 or target >= len(self._current_nodes):
                return
            self._current_nodes[row], self._current_nodes[target] = (
                self._current_nodes[target], self._current_nodes[row])
            _remap_refs(self._current_nodes, {row: target, target: row})
            self._serialize_dialog()
            self._rebuild_node_list(keep_row=target)

        btn_scene_add.clicked.connect(_on_scene_add)
        btn_scene_rem.clicked.connect(_on_scene_rem)
        btn_nd_add.clicked.connect(_on_node_add)
        btn_nd_rem.clicked.connect(_on_node_rem)
        btn_nd_up.clicked.connect(lambda: _on_node_move(-1))
        btn_nd_dn.clicked.connect(lambda: _on_node_move(1))
        btn_var_add.clicked.connect(self._on_var_add)
        btn_var_rem.clicked.connect(self._on_var_rem)
        self._btn_cmd_browse.clicked.connect(lambda: self._on_cmd_browse(page))

        return page

    # ── Variable table helpers ────────────────────────────────────────────

    def _get_arg_options(self, cmd: str) -> list:
        """Return candidate argument values for the given command."""
        events = self._pm.data.get("events", [])
        if cmd == "showImage":
            return [""] + [e.get("name", "") for e in events
                           if e.get("type") == "background" and e.get("name")]
        if cmd in ("showEventPhoto", "mod_addEventSellablePhoto"):
            # Dialog stem names match the event photo files (e.g. Event_00024_)
            return [""] + [e.get("name", "") for e in events
                           if e.get("type") == "dialog" and e.get("name")]
        if cmd == "mod_overlayImage3":
            names = []
            data_dir = os.path.join(self._resolve_pack_folder(), "Data")
            if os.path.isdir(data_dir):
                for f in sorted(os.listdir(data_dir)):
                    stem, ext = os.path.splitext(f)
                    if "overlay" in stem.lower() and ext.lower() in (".dat", ".jpa", ".pna", ".png"):
                        names.append(stem)
            if not names:
                names = [e.get("name", "") for e in events
                         if e.get("type") == "overlay" and e.get("name")]
            return [""] + names
        if cmd in ("playSound", "stopLoopedSound"):
            seen = {"camera"}
            for node in self._current_nodes:
                for v in node.get("vars", []):
                    if v.get("key") in ("playSound", "stopLoopedSound") and v.get("val"):
                        seen.add(v["val"])
            return [""] + sorted(seen)
        return [""]

    def _populate_flow_combos(self) -> None:
        """Rebuild Next/Branch/Action dropdowns from the live node list."""
        for field, cmb in self._flow_combos.items():
            saved = cmb.currentData()
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("-1  (none)", -1)
            for i, node in enumerate(self._current_nodes):
                cmb.addItem(_node_label(i, node), i)
            idx = cmb.findData(saved)
            cmb.setCurrentIndex(max(idx, 0))
            cmb.blockSignals(False)

    def _on_var_row_selected(self, row: int, _col: int, _prev: int, _prev_col: int) -> None:
        if row < 0:
            self._btn_cmd_browse.setEnabled(False)
            self._cmd_preview.clear()
            return
        cmd_item = self._var_table.item(row, 0)
        cmd = cmd_item.text() if cmd_item else ""
        is_img = cmd in _IMAGE_CMDS
        self._btn_cmd_browse.setEnabled(is_img)
        if is_img:
            arg_item = self._var_table.item(row, 1)
            self._refresh_cmd_preview(arg_item.text() if arg_item else "")
        else:
            self._cmd_preview.clear()

    def _refresh_cmd_preview(self, name: str) -> None:
        pack_folder = self._resolve_pack_folder()
        path = resolve_asset(name, pack_folder) if name and pack_folder else ""
        if not path and name and os.path.isfile(name):
            path = name
        self._cmd_preview_path = path
        if not path:
            self._cmd_preview.setText(f"No preview: {name}" if name else "")
            return
        px = load_pixmap(path)
        if px.isNull():
            self._cmd_preview.setText(f"No preview: {name}")
            return
        w = max(self._cmd_preview.width(), 160)
        h = self._cmd_preview.maximumHeight()
        self._cmd_preview.setText("")
        self._cmd_preview.setPixmap(px.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def _resolve_pack_folder(self) -> str:
        """Return the pack's root folder, trying multiple sources."""
        # 1. Dialog source path (set when user adds a JSON manually)
        if self._current_dlg_row >= 0:
            dlgs = [e for e in self._pm.data.get("events", []) if e.get("type") == "dialog"]
            if self._current_dlg_row < len(dlgs):
                src = dlgs[self._current_dlg_row].get("source") or ""
                if src:
                    return os.path.dirname(os.path.dirname(src))
        # 2. Any background/overlay with a resolved source (always set on import)
        for ev in self._pm.data.get("events", []):
            src = ev.get("source") or ""
            if src and ev.get("type") in ("background", "overlay"):
                return os.path.dirname(os.path.dirname(src))
        # 3. Saved pack JSON location
        if self._pm.current_path:
            return os.path.dirname(self._pm.current_path)
        return ""

    def _on_cmd_browse(self, parent: QWidget) -> None:
        row = self._var_table.currentRow()
        if row < 0:
            return
        path, _ = QFileDialog.getOpenFileName(parent, "Select Image", "", ASSET_FILTER)
        if not path:
            return
        # Store only the stem — the game references assets by name without extension
        name = os.path.splitext(os.path.basename(path))[0]
        self._var_table.blockSignals(True)
        self._var_table.setItem(row, 1, QTableWidgetItem(name))
        self._var_table.blockSignals(False)
        self._save_node_form()
        self._refresh_cmd_preview(name)

    def _on_var_add(self) -> None:
        row = self._var_table.rowCount()
        self._var_table.blockSignals(True)
        self._var_table.insertRow(row)
        self._var_table.setItem(row, 0, QTableWidgetItem(""))
        self._var_table.setItem(row, 1, QTableWidgetItem(""))
        self._var_table.blockSignals(False)
        self._save_node_form()

    def _on_var_rem(self) -> None:
        row = self._var_table.currentRow()
        if row < 0:
            return
        self._var_table.removeRow(row)
        self._save_node_form()

    # ── Dialog / node slots ───────────────────────────────────────────────

    def _on_dialog_selected(self, row: int) -> None:
        self._current_nodes = []
        self._current_dlg_row = row
        self._node_list.clear()
        dlgs = [e for e in self._pm.data.get("events", []) if e.get("type") == "dialog"]
        if row < 0 or row >= len(dlgs):
            return
        content = dlgs[row].get("content", "")
        try:
            data = json.loads(content) if content.strip() else {}
        except json.JSONDecodeError:
            self._node_list.addItem("(invalid JSON)")
            return
        self._current_nodes = _extract_nodes(data)
        self._rebuild_node_list()

    def _rebuild_node_list(self, keep_row: int = -1) -> None:
        self._node_list.clear()
        for i, node in enumerate(self._current_nodes):
            item = QListWidgetItem(_node_label(i, node))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._node_list.addItem(item)
        # Populate combos before setCurrentRow triggers _on_node_selected
        self._populate_flow_combos()
        if keep_row >= 0 and keep_row < self._node_list.count():
            self._node_list.setCurrentRow(keep_row)

    def _on_node_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._current_nodes):
            return
        node = self._current_nodes[row]
        self._loading = True
        self._cmb_tag.setCurrentText(node.get("tag", ""))
        self._edit_text.setPlainText(node.get("text", ""))
        self._edit_extra.setText(str(node.get("extraData", "")))
        for field, cmb in self._flow_combos.items():
            val = node.get(field, -1)
            idx = cmb.findData(val)
            cmb.setCurrentIndex(max(idx, 0))
        self._var_table.setRowCount(0)
        for v in node.get("vars", []):
            r = self._var_table.rowCount()
            self._var_table.insertRow(r)
            self._var_table.setItem(r, 0, QTableWidgetItem(v.get("key", "")))
            self._var_table.setItem(r, 1, QTableWidgetItem(str(v.get("val", ""))))
        self._loading = False

    def _save_node_form(self) -> None:
        if self._loading:
            return
        row = self._node_list.currentRow()
        if row < 0 or row >= len(self._current_nodes) or self._current_dlg_row < 0:
            return
        node = self._current_nodes[row]
        node["tag"]       = self._cmb_tag.currentText()
        node["text"]      = self._edit_text.toPlainText()
        node["extraData"] = self._edit_extra.text()
        for field, cmb in self._flow_combos.items():
            data = cmb.currentData()
            node[field] = data if data is not None else -1
        node["vars"] = [
            {
                "key": (self._var_table.item(r, 0).text() if self._var_table.item(r, 0) else ""),
                "val": (self._var_table.item(r, 1).text() if self._var_table.item(r, 1) else ""),
            }
            for r in range(self._var_table.rowCount())
        ]
        self._serialize_dialog()
        self._node_list.item(row).setText(_node_label(row, node))

    def _serialize_dialog(self) -> None:
        """Flush _current_nodes back into the selected dialog event's JSON content."""
        if self._current_dlg_row < 0:
            return
        dlgs = [e for e in self._pm.data.get("events", []) if e.get("type") == "dialog"]
        if self._current_dlg_row >= len(dlgs):
            return
        ev = dlgs[self._current_dlg_row]
        try:
            data = json.loads(ev.get("content", "{}"))
        except json.JSONDecodeError:
            data = {}
        _write_nodes(data, self._current_nodes)
        ev["content"] = json.dumps(data, ensure_ascii=False, indent=2)

    # ── Other slots ───────────────────────────────────────────────────────

    def _save_event_type(self) -> None:
        self._pm.set("event_type", self._cmb_event_type.currentText())

    # ── Refresh ───────────────────────────────────────────────────────────

    def _rebuild_lists(self) -> None:
        events: list = self._pm.data.get("events", [])
        bgs  = [e for e in events if e.get("type") == "background"]
        ovs  = [e for e in events if e.get("type") == "overlay"]
        dlgs = [e for e in events if e.get("type") == "dialog"]

        self._bg_list.clear()
        for e in bgs:
            item = QListWidgetItem(e.get("name", ""))
            item.setData(Qt.ItemDataRole.UserRole, e.get("source", ""))
            self._bg_list.addItem(item)

        self._ov_list.clear()
        for e in ovs:
            item = QListWidgetItem(e.get("name", ""))
            item.setData(Qt.ItemDataRole.UserRole, e.get("source", ""))
            self._ov_list.addItem(item)

        self._dlg_list.clear()
        self._node_list.clear()
        self._current_nodes = []
        self._current_dlg_row = -1
        for e in dlgs:
            self._dlg_list.addItem(e.get("name", ""))
        # Clear stale node detail panel so previous pack's data doesn't linger
        self._cmb_tag.blockSignals(True)
        self._cmb_tag.setCurrentIndex(0)
        self._cmb_tag.blockSignals(False)
        self._edit_text.blockSignals(True)
        self._edit_text.setPlainText("")
        self._edit_text.blockSignals(False)
        self._edit_extra.blockSignals(True)
        self._edit_extra.setText("")
        self._edit_extra.blockSignals(False)
        for cmb in self._flow_combos.values():
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("-1  (none)", -1)
            cmb.blockSignals(False)
        self._var_table.blockSignals(True)
        self._var_table.setRowCount(0)
        self._var_table.blockSignals(False)
        self._cmd_preview.clear()

    def refresh(self) -> None:
        et = self._pm.get("event_type", "normal")
        idx = self._cmb_event_type.findText(et)
        self._cmb_event_type.blockSignals(True)
        self._cmb_event_type.setCurrentIndex(idx if idx >= 0 else 0)
        self._cmb_event_type.blockSignals(False)
        self._rebuild_lists()
        # Switch to first populated sub-tab
        events: list = self._pm.data.get("events", [])
        has_bg  = any(e.get("type") == "background" for e in events)
        has_ov  = any(e.get("type") == "overlay"    for e in events)
        has_dlg = any(e.get("type") == "dialog"     for e in events)
        if has_bg:
            self._tabs.setCurrentIndex(0)
        elif has_ov:
            self._tabs.setCurrentIndex(1)
        elif has_dlg:
            self._tabs.setCurrentIndex(2)

