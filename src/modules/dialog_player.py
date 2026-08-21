"""Dialog playback window — step through a dialog scene node by node."""

import os

from PyQt6.QtCore import Qt, QRect  # type: ignore
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor  # type: ignore
from PyQt6.QtWidgets import (  # type: ignore
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QWidget, QSizePolicy,
)

from app_debug import dlog as _dlog

# Forward-flow port colours (same as graph)
_COLOR_NEXT   = "#5599ff"
_COLOR_BRANCH = "#ffcc44"
_COLOR_ACTION = "#ff8844"

# Image-command keys whose value is an asset stem to preview
_IMAGE_CMDS = frozenset({
    "showImage", "mod_showImage", "showEventPhoto",
    "mod_overlayImage3", "mod_addEventSellablePhoto",
})

# Speaker-header background colours (same palette as dialog_graph)
_TAG_COLORS: dict[str, str] = {
    "":            "#3a3a3a",
    "You":         "#1e4d7a",
    "SKIP":        "#444444",
    "Schoolgirl":  "#7a2a4a",
    "Teacher":     "#4a2a7a",
    "Trio":        "#2a5a3a",
    "Aya":         "#5a3a7a",
    "Boy":         "#2a4a5a",
    "Girl":        "#5a2a4a",
    "Guy":         "#3a4a2a",
    "Old Man":     "#4a3a2a",
    "Punk Guy":    "#3a2a4a",
    "Store Owner": "#2a4a4a",
}
_TAG_DEFAULT = "#2a4a2a"


def _tag_bg(tag: str) -> str:
    return _TAG_COLORS.get(tag, _TAG_DEFAULT)


def _colored_btn(text: str, color: str, width: int) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedWidth(width)
    btn.setStyleSheet(
        f"QPushButton {{ border: 1px solid {color}; color: {color}; }}"
        f"QPushButton:disabled {{ border: 1px solid #444; color: #444; }}"
        f"QPushButton:hover {{ background: {color}22; }}"
    )
    return btn


def _resolve_image(stem: str, pack_dir: str) -> str:
    """Return the first file matching *stem* (any image/video ext) inside pack_dir."""
    if not stem or not pack_dir:
        return ""
    for ext in (".png", ".jpg", ".jpeg", ".dat", ".jpa", ".pna", ".bytes", ".byte"):
        p = os.path.join(pack_dir, stem + ext)
        if os.path.isfile(p):
            return p
    # Scan all sub-dirs one level deep
    for entry in os.scandir(pack_dir):
        if entry.is_dir():
            for ext in (".png", ".jpg", ".jpeg", ".dat", ".jpa", ".pna", ".bytes", ".byte"):
                p = os.path.join(entry.path, stem + ext)
                if os.path.isfile(p):
                    return p
    return ""


class _CompositePanel(QWidget):
    """Single canvas: background, overlay, and dialog text box painted together."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(260, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._bg_pix:   QPixmap | None = None
        self._ov_pix:   QPixmap | None = None
        self._bg_label  = ""
        self._ov_label  = ""
        self._dlg_tag   = ""
        self._dlg_text  = ""
        self._dlg_bg    = "#3a3a3a"

    def set_background(self, path: str, stem: str = "") -> None:
        self._bg_pix = QPixmap(path) if (path and os.path.isfile(path)) else None
        self._bg_label = stem
        self.update()

    def set_overlay(self, path: str, stem: str = "") -> None:
        self._ov_pix = QPixmap(path) if (path and os.path.isfile(path)) else None
        self._ov_label = stem
        self.update()

    def set_dialog(self, tag: str, text: str, tag_bg: str) -> None:
        self._dlg_tag  = tag
        self._dlg_text = text
        self._dlg_bg   = tag_bg
        self.update()

    def clear(self) -> None:
        self._bg_pix = self._ov_pix = None
        self._bg_label = self._ov_label = ""
        self._dlg_tag = self._dlg_text = ""
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        p.fillRect(rect, QColor("#111111"))

        # Background image
        if self._bg_pix and not self._bg_pix.isNull():
            scaled = self._bg_pix.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (rect.width()  - scaled.width())  // 2
            y = (rect.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        elif self._bg_label:
            p.setPen(QColor("#555"))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                       f"bg: {self._bg_label}\n(not found)")

        # Overlay image
        if self._ov_pix and not self._ov_pix.isNull():
            scaled = self._ov_pix.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (rect.width()  - scaled.width())  // 2
            y = (rect.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        elif self._ov_label:
            p.setPen(QColor("#887755"))
            p.drawText(
                QRect(0, rect.height() - 24, rect.width(), 22),
                Qt.AlignmentFlag.AlignCenter,
                f"overlay: {self._ov_label} (not found)",
            )

        p.end()


class DialogPlayerWindow(QDialog):
    """Non-modal dialog playback window.

    Walks through nodes one at a time using their oNPC/oSet/oAct flow
    references.  A history stack enables going back.
    Left panel: speaker/text/commands + navigation.
    Right panel: live background/overlay image preview.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dialog Test")
        self.resize(920, 560)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint,
        )
        self._nodes: list = []
        self._pd_choices: list = []   # player-dialog choice containers
        self._current: int = 0
        self._history: list[int] = []
        self._pack_dir: str = ""
        self._current_bg: str = ""
        self._current_ov: str = ""
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # Status bar
        self._lbl_status = QLabel()
        self._lbl_status.setStyleSheet("color:#888; font-size:11px;")
        root.addWidget(self._lbl_status)

        # Composite image — fills main area
        self._composite = _CompositePanel()
        root.addWidget(self._composite, 1)

        # Choices overlay at top of the composite image
        _overlay = QVBoxLayout(self._composite)
        _overlay.setContentsMargins(0, 0, 0, 0)
        _overlay.setSpacing(0)
        self._frm_choices = QFrame()
        self._frm_choices.setStyleSheet(
            "QFrame { background:rgba(15,15,30,210); border-bottom:1px solid #446; }")
        self._choices_layout = QVBoxLayout(self._frm_choices)
        self._choices_layout.setContentsMargins(8, 6, 8, 6)
        self._choices_layout.setSpacing(4)
        lbl_choose = QLabel("Player choices:")
        lbl_choose.setStyleSheet("color:#aac; font-size:10px; border:none;")
        self._choices_layout.addWidget(lbl_choose)
        self._frm_choices.hide()
        _overlay.addWidget(self._frm_choices)
        _overlay.addStretch()

        # Speaker header
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        self._lbl_speaker = QLabel()
        self._lbl_speaker.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_speaker.setFixedHeight(28)
        self._lbl_speaker.setContentsMargins(10, 0, 10, 0)
        self._lbl_speaker.setFont(font)
        root.addWidget(self._lbl_speaker)

        # Dialog text
        self._lbl_text = QLabel()
        self._lbl_text.setWordWrap(True)
        self._lbl_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._lbl_text.setContentsMargins(10, 8, 10, 8)
        self._lbl_text.setStyleSheet(
            "background:#1e1e1e; border:1px solid #3a3a3a; "
            "border-top:none; font-size:12px; color:#e0e0e0;")
        self._lbl_text.setMinimumHeight(60)
        root.addWidget(self._lbl_text)

        # Commands panel (collapsed by default when empty)
        self._frm_cmds = QFrame()
        self._frm_cmds.setStyleSheet("background:#181818; border:1px solid #333;")
        cmds_layout = QVBoxLayout(self._frm_cmds)
        cmds_layout.setContentsMargins(8, 4, 8, 4)
        cmds_layout.setSpacing(2)
        lbl_ct = QLabel("Commands:")
        lbl_ct.setStyleSheet("color:#666; font-size:10px; border:none;")
        cmds_layout.addWidget(lbl_ct)
        self._lbl_cmds = QLabel()
        self._lbl_cmds.setWordWrap(True)
        self._lbl_cmds.setStyleSheet("color:#aaa; font-size:10px; border:none;")
        cmds_layout.addWidget(self._lbl_cmds)
        root.addWidget(self._frm_cmds)

        # Branch destination previews
        branches_box = QGroupBox("Flow")
        branches_box.setStyleSheet(
            "QGroupBox { color:#888; font-size:10px; border:1px solid #333; margin-top:6px; }"
            "QGroupBox::title { subcontrol-origin:margin; left:8px; }"
        )
        branches_layout = QVBoxLayout(branches_box)
        branches_layout.setContentsMargins(6, 10, 6, 4)
        branches_layout.setSpacing(3)
        self._lbl_next_preview   = self._make_branch_lbl(_COLOR_NEXT)
        self._lbl_action_preview = self._make_branch_lbl(_COLOR_ACTION)
        branches_layout.addWidget(self._lbl_next_preview)
        branches_layout.addWidget(self._lbl_action_preview)
        root.addWidget(branches_box)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.setSpacing(6)

        self._btn_first = QPushButton("⏮ First")
        self._btn_first.setFixedWidth(80)
        self._btn_first.setToolTip("Jump back to node #0")
        self._btn_first.clicked.connect(self._go_first)

        self._btn_back = QPushButton("◀ Back")
        self._btn_back.setFixedWidth(80)
        self._btn_back.setToolTip("Step back through history")
        self._btn_back.clicked.connect(self._go_back)

        self._btn_next   = _colored_btn("Next ▶",   _COLOR_NEXT,   90)
        self._btn_action = _colored_btn("Action ⚡", _COLOR_ACTION, 98)

        self._btn_next.clicked.connect(lambda: self._follow("oNPC"))
        self._btn_action.clicked.connect(lambda: self._follow("oAct"))

        self._lbl_end = QLabel("— end of scene —")
        self._lbl_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_end.setStyleSheet("color:#666; font-size:10px;")
        self._lbl_end.hide()

        nav.addWidget(self._btn_first)
        nav.addWidget(self._btn_back)
        nav.addStretch()
        nav.addWidget(self._btn_next)
        nav.addWidget(self._btn_action)
        root.addLayout(nav)
        root.addWidget(self._lbl_end)

    @staticmethod
    def _make_branch_lbl(color: str) -> QLabel:
        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color:{color}; font-size:10px; "
            f"border-left:2px solid {color}; padding-left:4px;")
        lbl.hide()
        return lbl

    # ── Public API ────────────────────────────────────────────────────────

    def load(self, nodes: list, scene_name: str = "",
             start_index: int = 0, pack_dir: str = "",
             pd_choices: list | None = None) -> None:
        """Load *nodes* and player-dialog choices, begin playback at *start_index*."""
        self._nodes = nodes
        self._pd_choices = pd_choices or []
        self._history = []
        self._pack_dir = pack_dir
        self._current_bg = ""
        self._current_ov = ""
        self._current = max(0, min(start_index, len(nodes) - 1)) if nodes else 0
        title = f"Dialog Test — {scene_name}" if scene_name else "Dialog Test"
        self.setWindowTitle(title)
        self._show_node()

    def jump_to(self, idx: int) -> None:
        """Jump to a specific node without clearing history."""
        if not self._nodes or idx < 0 or idx >= len(self._nodes):
            return
        self._history.append(self._current)
        self._current = idx
        self._show_node()

    # ── Navigation ────────────────────────────────────────────────────────

    def _follow(self, field: str) -> None:
        if not self._nodes:
            return
        ref = self._nodes[self._current].get(field, -1)
        if ref < 0 or ref >= len(self._nodes):
            return
        self._history.append(self._current)
        self._current = ref
        self._show_node()

    def _go_back(self) -> None:
        if not self._history:
            return
        self._current = self._history.pop()
        self._replay_image_state_to(self._current)
        self._show_node()

    def _go_first(self) -> None:
        self._history.clear()
        self._current = 0
        self._current_bg = ""
        self._current_ov = ""
        self._show_node()

    def _replay_image_state_to(self, target_idx: int) -> None:
        """Rebuild _current_bg/_current_ov by replaying the history path up to target."""
        self._current_bg = ""
        self._current_ov = ""
        for idx in list(self._history) + [target_idx]:
            if 0 <= idx < len(self._nodes):
                for v in self._nodes[idx].get("vars", []):
                    k, val = v.get("key", ""), v.get("val", "")
                    if k in ("showImage", "mod_showImage", "showEventPhoto",
                             "mod_addEventSellablePhoto"):
                        self._current_bg = val
                    elif k in ("noImage", "endEvent"):
                        self._current_bg = ""
                    elif k == "mod_overlayImage3":
                        self._current_ov = val
                    elif k == "noOverlayImage":
                        self._current_ov = ""

    # ── Rendering ─────────────────────────────────────────────────────────

    def _show_node(self) -> None:
        n = len(self._nodes)
        if n == 0:
            self._lbl_status.setText("No nodes")
            self._lbl_speaker.setText("")
            self._lbl_speaker.setStyleSheet("")
            self._lbl_text.setText("")
            self._lbl_cmds.setText("")
            self._composite.clear()
            self._composite.set_dialog("", "", "#3a3a3a")
            self._frm_choices.hide()
            self._lbl_next_preview.hide()
            self._lbl_action_preview.hide()
            for btn in (self._btn_next, self._btn_action,
                        self._btn_back, self._btn_first):
                btn.setEnabled(False)
            return

        idx  = self._current
        node = self._nodes[idx]
        tag  = node.get("tag", "")
        text = node.get("text", "")
        vs   = node.get("vars", [])

        # Status
        self._lbl_status.setText(
            f"Node #{idx} of {n - 1}  ·  history depth: {len(self._history)}")

        # Speaker header
        bg = _tag_bg(tag)
        self._lbl_speaker.setStyleSheet(
            f"background:{bg}; color:#ffffff; font-size:9pt; "
            f"font-weight:bold; padding:0 10px; border:1px solid #555;")
        self._lbl_speaker.setText(tag or "— narrator —")

        # Dialog text
        self._lbl_text.setText(text or "(no text)")

        # Commands + image extraction — only update images when node explicitly sets/clears them
        cmd_lines = []
        for v in vs:
            k   = v.get("key", "")
            val = v.get("val", "")
            cmd_lines.append(f"• {k}  =  {val}" if val else f"• {k}")
            if k in ("showImage", "mod_showImage", "showEventPhoto",
                     "mod_addEventSellablePhoto"):
                self._current_bg = val
            elif k in ("noImage", "endEvent"):
                self._current_bg = ""
            elif k == "mod_overlayImage3":
                self._current_ov = val
            elif k == "noOverlayImage":
                self._current_ov = ""

        if cmd_lines:
            self._lbl_cmds.setText("\n".join(cmd_lines))
            self._frm_cmds.show()
        else:
            self._frm_cmds.hide()

        # Refresh composite with current (possibly persisted) image state
        self._composite.set_background(
            _resolve_image(self._current_bg, self._pack_dir), self._current_bg)
        self._composite.set_overlay(
            _resolve_image(self._current_ov, self._pack_dir), self._current_ov)
        self._composite.set_dialog(tag, text, _tag_bg(tag))

        # Flow buttons + player choice buttons
        oNPC = node.get("oNPC", -1)
        oSet = node.get("oSet", -1)  # index into _pd_choices, NOT an nd_ index
        oAct = node.get("oAct", -1)

        self._update_flow_btn(self._btn_next, self._lbl_next_preview,
                              "Next ▶", oNPC, n, "oNPC")
        self._update_flow_btn(self._btn_action, self._lbl_action_preview,
                              "Action ⚡", oAct, n, "oAct")
        self._rebuild_choice_buttons(oSet)

        self._btn_back.setEnabled(bool(self._history))
        self._btn_first.setEnabled(idx != 0 or bool(self._history))

        at_end = oNPC < 0 and oSet < 0 and oAct < 0
        self._lbl_end.setVisible(at_end)

        _dlog("DialogPlayerWindow._show_node",
              f"node={idx} tag={tag!r} bg={self._current_bg!r} ov={self._current_ov!r}")

    def _rebuild_choice_buttons(self, oSet: int) -> None:
        """Populate self._frm_choices with buttons for each pd_ choice."""
        # Remove old choice buttons (keep index 0 = the title label)
        while self._choices_layout.count() > 1:
            item = self._choices_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if oSet < 0 or oSet >= len(self._pd_choices):
            self._frm_choices.hide()
            return

        container = self._pd_choices[oSet]
        coms = container.get("coms", [])
        if not coms:
            self._frm_choices.hide()
            return

        n = len(self._nodes)
        for j, com in enumerate(coms):
            text = com.get("text", "") or f"(choice {j})"
            oAns = com.get("oAns", -1)
            btn = QPushButton(text)
            btn.setStyleSheet(
                f"QPushButton {{ text-align:left; padding:4px 8px; "
                f"border:1px solid {_COLOR_BRANCH}; color:#ddd; background:#222; }}"
                f"QPushButton:hover {{ background:{_COLOR_BRANCH}22; }}"
                f"QPushButton:disabled {{ border:1px solid #444; color:#555; }}"
            )
            active = 0 <= oAns < n
            btn.setEnabled(active)
            tip = f"→ #{oAns}" if active else "(no destination)"
            if active:
                t = self._nodes[oAns]
                t_text = (t.get("text") or "").strip()[:50]
                tip += f"  [{t.get('tag') or 'narrator'}]  {t_text}"
            btn.setToolTip(tip)
            if active:
                btn.clicked.connect(lambda _=False, dest=oAns: self._choose(dest))
            self._choices_layout.addWidget(btn)

        self._frm_choices.show()

    def _choose(self, dest: int) -> None:
        """Follow a player dialog choice to *dest* nd_ array index."""
        if dest < 0 or dest >= len(self._nodes):
            return
        self._history.append(self._current)
        self._current = dest
        self._show_node()

    def _update_flow_btn(self, btn: QPushButton, preview_lbl: QLabel,
                         label: str, ref: int, n: int, field: str) -> None:
        active = 0 <= ref < n
        btn.setEnabled(active)
        if active:
            target = self._nodes[ref]
            t_tag  = target.get("tag", "")
            t_text = (target.get("text") or "").strip()
            t_text = t_text[:60] + "…" if len(t_text) > 60 else t_text
            btn.setToolTip(f"{field} → #{ref}")
            preview_lbl.setText(
                f"#{ref}  [{t_tag or 'narrator'}]  {t_text}")
            preview_lbl.show()
        else:
            btn.setToolTip(label)
            preview_lbl.hide()
