"""Dialog graph canvas — visual node editor for event dialog scenes.

Each dialog node is a draggable box.  Arrows show the three flow connections
(oNPC = Next blue, oSet = Branch yellow, oAct = Action orange).  Dragging a
node updates its rect in the shared nodes list; the existing list/form panel
stays in sync because both views share the same list object.
"""

import math

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal  # type: ignore
from PyQt6.QtGui import (  # type: ignore
    QColor, QPen, QBrush, QPainter, QPainterPath, QPolygonF, QFont,
    QTransform, QWheelEvent, QKeyEvent,
)
from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsScene,
    QGraphicsView, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsSimpleTextItem, QDialog, QLabel,
    QToolBar, QSizePolicy,
)

from app_debug import dlog as _dlog

# ── Visual constants ─────────────────────────────────────────────────────────

_NODE_W   = 210
_NODE_H   = 90
_PORT_R   = 5          # port circle radius
_ARROW_SZ = 8          # arrowhead size

# Output port layout (right edge): oNPC, oSet, oAct
_PORTS = [
    ("oNPC", "#5599ff", "N"),
    ("oSet", "#ffcc44", "B"),
    ("oAct", "#ff8844", "A"),
]

# Header color by speaker tag
_TAG_COLORS: dict[str, str] = {
    "":           "#3a3a3a",
    "You":        "#1e4d7a",
    "SKIP":       "#444444",
    "Schoolgirl": "#7a2a4a",
    "Teacher":    "#4a2a7a",
    "Trio":       "#2a5a3a",
    "Aya":        "#5a3a7a",
    "Boy":        "#2a4a5a",
    "Girl":       "#5a2a4a",
    "Guy":        "#3a4a2a",
    "Old Man":    "#4a3a2a",
    "Punk Guy":   "#3a2a4a",
    "Store Owner":"#2a4a4a",
}
_TAG_DEFAULT = "#2a4a2a"


def _tag_color(tag: str) -> QColor:
    return QColor(_TAG_COLORS.get(tag, _TAG_DEFAULT))


def _arrow_head(path: QPainterPath, tip: QPointF, dx: float, dy: float) -> None:
    """Append a filled triangle arrowhead at *tip* pointing toward (dx, dy)."""
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    b = _ARROW_SZ * 0.4
    p1 = QPointF(tip.x() - ux * _ARROW_SZ + px * b,
                 tip.y() - uy * _ARROW_SZ + py * b)
    p2 = QPointF(tip.x() - ux * _ARROW_SZ - px * b,
                 tip.y() - uy * _ARROW_SZ - py * b)
    path.moveTo(tip)
    path.lineTo(p1)
    path.lineTo(p2)
    path.closeSubpath()


# ── NodeItem ─────────────────────────────────────────────────────────────────

class NodeItem(QGraphicsRectItem):
    """A draggable node box in the dialog graph."""

    def __init__(self, idx: int, node: dict, on_click, on_moved) -> None:
        super().__init__(0, 0, _NODE_W, _NODE_H)
        self._idx     = idx
        self._node    = node
        self._on_click = on_click
        self._on_moved = on_moved

        x, y = node.get("rect", [idx * 240, 0])
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
        )
        self.setPen(QPen(QColor("#555555"), 1))
        self.setBrush(QColor("#2c2c2c"))
        self.setZValue(1)

    # ── Ports ─────────────────────────────────────────────────────────────

    def output_port_scene_pos(self, field: str) -> QPointF:
        i = [p[0] for p in _PORTS].index(field)
        return self.mapToScene(QPointF(_NODE_W, 28 + i * 20))

    def input_port_scene_pos(self) -> QPointF:
        return self.mapToScene(QPointF(0, _NODE_H / 2))

    # ── Painting ──────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget) -> None:
        selected = self.isSelected()
        border = QColor("#3a7bd5") if selected else QColor("#555555")
        painter.setBrush(QColor("#252525"))
        painter.setPen(QPen(border, 2 if selected else 1))
        painter.drawRoundedRect(self.rect(), 5, 5)

        tag = self._node.get("tag", "")
        # Header bar
        hdr = QRectF(1, 1, _NODE_W - 2, 22)
        painter.setBrush(_tag_color(tag))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(hdr, 4, 4)
        # Cover bottom-rounded corners of header
        painter.drawRect(QRectF(1, 12, _NODE_W - 2, 11))

        # Index badge
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(5, 3, 30, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"#{self._idx}")

        # Tag label
        painter.setPen(QColor("#dddddd"))
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(28, 3, _NODE_W - 36, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         tag or "—")

        # Text preview
        text = self._node.get("text", "")
        preview = text[:100].replace("\n", " ")
        font.setPointSize(7)
        painter.setFont(font)
        painter.setPen(QColor("#b0b0b0"))
        painter.drawText(
            QRectF(6, 26, _NODE_W - 16, _NODE_H - 36),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop |
            Qt.TextFlag.TextWordWrap,
            preview,
        )

        # Command count footer
        n_cmds = len(self._node.get("vars", []))
        if n_cmds:
            font.setPointSize(6)
            painter.setFont(font)
            painter.setPen(QColor("#666666"))
            painter.drawText(
                QRectF(6, _NODE_H - 14, _NODE_W - 14, 12),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{n_cmds} cmd{'s' if n_cmds > 1 else ''}",
            )

        # Output port circles
        painter.setPen(QPen(QColor("#ffffff"), 0.5))
        for i, (field, color, label) in enumerate(_PORTS):
            ref = self._node.get(field, -1)
            cy = 28 + i * 20
            if ref >= 0:
                painter.setBrush(QColor(color))
            else:
                painter.setBrush(QColor("#404040"))
            painter.drawEllipse(QPointF(_NODE_W - _PORT_R, cy), _PORT_R, _PORT_R)
            if ref >= 0:
                painter.setPen(QColor(color))
                font.setPointSize(6)
                painter.setFont(font)
                painter.drawText(
                    QRectF(_NODE_W - 22, cy - 5, 12, 10),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )
                painter.setPen(QPen(QColor("#ffffff"), 0.5))

        # Input port (left centre)
        painter.setBrush(QColor("#606060"))
        painter.setPen(QPen(QColor("#ffffff"), 0.5))
        painter.drawEllipse(QPointF(_PORT_R, _NODE_H / 2), _PORT_R, _PORT_R)

    # ── Interaction ───────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self._on_click(self._idx)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._node["rect"] = [int(value.x()), int(value.y())]
            self._on_moved()
        return super().itemChange(change, value)


# ── EdgeItem ─────────────────────────────────────────────────────────────────

class EdgeItem(QGraphicsPathItem):
    """A bezier arrow from one node's output port to another node's input port."""

    def __init__(self, src: NodeItem, dst: NodeItem, field: str) -> None:
        super().__init__()
        self._src   = src
        self._dst   = dst
        self._field = field
        color_str   = next(c for f, c, _ in _PORTS if f == field)
        self._color = QColor(color_str)
        self.setPen(QPen(self._color, 1.5,
                         Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap,
                         Qt.PenJoinStyle.RoundJoin))
        self.setBrush(self._color)
        self.setZValue(0)
        self.update_path()

    def update_path(self) -> None:
        p1 = self._src.output_port_scene_pos(self._field)
        p2 = self._dst.input_port_scene_pos()
        dx = max(abs(p2.x() - p1.x()) * 0.55, 60.0)
        cp1 = QPointF(p1.x() + dx, p1.y())
        cp2 = QPointF(p2.x() - dx, p2.y())

        path = QPainterPath(p1)
        path.cubicTo(cp1, cp2, p2)

        # Arrowhead at destination (tangent = p2 - cp2)
        adx = p2.x() - cp2.x()
        ady = p2.y() - cp2.y()
        _arrow_head(path, p2, adx, ady)

        self.setPath(path)


# ── Graph View ────────────────────────────────────────────────────────────────

class _GraphView(QGraphicsView):
    zoom_changed = pyqtSignal(float)  # emits current scale factor

    def __init__(self, scene: QGraphicsScene) -> None:
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#1a1a1a"))
        self.setStyleSheet("border:0;")
        self._zoom_level = 1.0

    @property
    def zoom_level(self) -> float:
        return self._zoom_level

    def apply_zoom(self, factor: float) -> None:
        """Multiply current zoom by *factor* and emit zoom_changed."""
        self._zoom_level = max(0.1, min(self._zoom_level * factor, 5.0))
        self.setTransform(QTransform().scale(self._zoom_level, self._zoom_level))
        self.zoom_changed.emit(self._zoom_level)

    def reset_zoom(self) -> None:
        self._zoom_level = 1.0
        self.setTransform(QTransform())
        self.zoom_changed.emit(self._zoom_level)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.apply_zoom(factor)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_F:
            self.fitInView(self.scene().itemsBoundingRect(),
                           Qt.AspectRatioMode.KeepAspectRatio)
        else:
            super().keyPressEvent(event)


# ── DialogGraphWidget ─────────────────────────────────────────────────────────

class DialogGraphWidget(QWidget):
    """Visual graph editor for a single dialog scene's node list.

    The widget shares the same *nodes* list with the EventWidget's list/form
    view.  Dragging a node updates ``node["rect"]`` in-place; the form stays
    in sync because both views read from the same objects.

    Signals
    -------
    node_selected(int)  — emitted when the user clicks a node (passes index)
    """

    node_selected = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._nodes: list   = []
        self._node_items: dict[int, NodeItem] = {}
        self._edge_items:  list[EdgeItem]     = []
        self._scene = QGraphicsScene(self)
        self._view  = _GraphView(self._scene)
        self._selected_idx: int = -1
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._view, 1)

    # ── Public API ────────────────────────────────────────────────────────

    def load(self, nodes: list) -> None:
        """Rebuild the scene from *nodes*.  Called each time a dialog scene is selected."""
        self._nodes = nodes
        self._selected_idx = -1
        self._rebuild()

    def highlight_node(self, row: int) -> None:
        """Highlight the node at *row* (called when the list view selection changes)."""
        for idx, item in self._node_items.items():
            item.setSelected(idx == row)
        if row in self._node_items:
            self._view.ensureVisible(self._node_items[row])
        self._selected_idx = row

    def clear(self) -> None:
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._nodes = []
        self._selected_idx = -1

    def refresh_edges(self) -> None:
        """Rebuild arrows from current node dict values (call after flow ref edits)."""
        self._rebuild_edges()

    # ── Scene building ────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()

        for i, node in enumerate(self._nodes):
            item = NodeItem(i, node, self._on_node_click, self._on_node_moved)
            self._scene.addItem(item)
            self._node_items[i] = item

        self._rebuild_edges()

    def _rebuild_edges(self) -> None:
        for e in self._edge_items:
            self._scene.removeItem(e)
        self._edge_items.clear()

        for i, node in enumerate(self._nodes):
            src = self._node_items.get(i)
            if src is None:
                continue
            for field, _, _ in _PORTS:
                ref = node.get(field, -1)
                if ref < 0:
                    continue
                dst = self._node_items.get(ref)
                if dst is None:
                    continue
                edge = EdgeItem(src, dst, field)
                self._scene.addItem(edge)
                self._edge_items.append(edge)

    def _update_edges(self) -> None:
        for edge in self._edge_items:
            edge.update_path()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_node_click(self, idx: int) -> None:
        self._selected_idx = idx
        self.node_selected.emit(idx)

    def _on_node_moved(self) -> None:
        self._update_edges()

    def _fit(self) -> None:
        if self._node_items:
            self._view.fitInView(self._scene.itemsBoundingRect(),
                                 Qt.AspectRatioMode.KeepAspectRatio)

    def _zoom(self, factor: float) -> None:
        self._view.apply_zoom(factor)

    # ── Auto-layout ───────────────────────────────────────────────────────

    def _auto_layout(self) -> None:
        """Arrange nodes in a top-down flow order using BFS from root nodes."""
        if not self._nodes:
            return

        n = len(self._nodes)
        # Find nodes that are not the target of any flow reference → roots
        targets: set[int] = set()
        for node in self._nodes:
            for field, _, _ in _PORTS:
                ref = node.get(field, -1)
                if 0 <= ref < n:
                    targets.add(ref)
        roots = [i for i in range(n) if i not in targets]
        if not roots:
            roots = [0]

        col_w = _NODE_W + 40
        row_h = _NODE_H + 30
        placed: dict[int, tuple[int, int]] = {}  # idx -> (col, row)
        queue = [(r, r, 0) for r in roots]      # (idx, col, row)
        visited: set[int] = set()
        max_row: dict[int, int] = {}             # col -> max row used

        for start_idx, col_seed, _ in queue:
            bfs = [(start_idx, col_seed, 0)]
            while bfs:
                idx, col, row = bfs.pop(0)
                if idx in visited:
                    continue
                visited.add(idx)
                cur_row = max(row, max_row.get(col, 0))
                placed[idx] = (col, cur_row)
                max_row[col] = cur_row + 1

                node = self._nodes[idx]
                child_col = col
                for field, _, _ in _PORTS:
                    ref = node.get(field, -1)
                    if 0 <= ref < n and ref not in visited:
                        bfs.append((ref, child_col, cur_row + 1))
                        child_col += 1

        # Lay out remaining unvisited nodes at the end
        unvisited = [i for i in range(n) if i not in placed]
        extra_col = max((c for c, _ in placed.values()), default=0) + 1
        for i, idx in enumerate(unvisited):
            placed[idx] = (extra_col, i)

        # Apply positions
        for idx, (col, row) in placed.items():
            x = col * col_w
            y = row * row_h
            self._nodes[idx]["rect"] = [x, y]
            item = self._node_items.get(idx)
            if item:
                item.setPos(x, y)

        self._update_edges()
        self._fit()
        _dlog("DialogGraphWidget._auto_layout", f"laid out {n} nodes")


# ── DialogGraphWindow ─────────────────────────────────────────────────────────

class DialogGraphWindow(QDialog):
    """Non-modal window containing the graph canvas with a full toolbar.

    Open via ``show()``; the parent EventWidget connects ``node_selected``
    to keep the form panel in sync.
    """

    node_selected = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dialog Graph")
        self.resize(1280, 820)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint,
        )
        self._graph = DialogGraphWidget(self)
        self._graph.node_selected.connect(self.node_selected)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        btn_fit = QPushButton("Fit  F")
        btn_fit.setFixedWidth(72)
        btn_fit.setToolTip("Fit all nodes into view  (shortcut: F)")
        btn_fit.clicked.connect(self._graph._fit)

        btn_layout = QPushButton("Auto-layout")
        btn_layout.setFixedWidth(96)
        btn_layout.setToolTip("Arrange nodes by flow order")
        btn_layout.clicked.connect(self._graph._auto_layout)

        btn_zo = QPushButton("−")
        btn_zo.setFixedSize(26, 26)
        btn_zo.setToolTip("Zoom out  (or scroll wheel)")
        btn_zo.clicked.connect(lambda: self._graph._view.apply_zoom(1 / 1.2))

        self._lbl_zoom = QLabel("100 %")
        self._lbl_zoom.setFixedWidth(52)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_zi = QPushButton("+")
        btn_zi.setFixedSize(26, 26)
        btn_zi.setToolTip("Zoom in  (or scroll wheel)")
        btn_zi.clicked.connect(lambda: self._graph._view.apply_zoom(1.2))

        btn_reset = QPushButton("100 %")
        btn_reset.setFixedWidth(54)
        btn_reset.setToolTip("Reset zoom to 100 %")
        btn_reset.clicked.connect(self._graph._view.reset_zoom)

        btn_25 = QPushButton("25 %")
        btn_25.setFixedWidth(46)
        btn_25.setToolTip("Zoom to 25 %")
        btn_25.clicked.connect(lambda: self._set_absolute_zoom(0.25))

        btn_50 = QPushButton("50 %")
        btn_50.setFixedWidth(46)
        btn_50.setToolTip("Zoom to 50 %")
        btn_50.clicked.connect(lambda: self._set_absolute_zoom(0.50))

        btn_200 = QPushButton("200 %")
        btn_200.setFixedWidth(54)
        btn_200.setToolTip("Zoom to 200 %")
        btn_200.clicked.connect(lambda: self._set_absolute_zoom(2.0))

        toolbar.addWidget(btn_fit)
        toolbar.addWidget(btn_layout)
        toolbar.addSpacing(12)
        toolbar.addWidget(btn_zo)
        toolbar.addWidget(self._lbl_zoom)
        toolbar.addWidget(btn_zi)
        toolbar.addSpacing(4)
        toolbar.addWidget(btn_reset)
        toolbar.addWidget(btn_25)
        toolbar.addWidget(btn_50)
        toolbar.addWidget(btn_200)
        toolbar.addStretch()

        layout.addLayout(toolbar)
        layout.addWidget(self._graph, 1)

        self._graph._view.zoom_changed.connect(self._on_zoom_changed)

    # ── Public API ────────────────────────────────────────────────────────

    def load(self, nodes: list, scene_name: str = "") -> None:
        title = f"Dialog Graph — {scene_name}" if scene_name else "Dialog Graph"
        self.setWindowTitle(title)
        self._graph.load(nodes)

    def highlight_node(self, row: int) -> None:
        self._graph.highlight_node(row)

    def refresh_edges(self) -> None:
        self._graph.refresh_edges()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_zoom_changed(self, level: float) -> None:
        self._lbl_zoom.setText(f"{round(level * 100)} %")

    def _set_absolute_zoom(self, level: float) -> None:
        view = self._graph._view
        view._zoom_level = level
        view.setTransform(QTransform().scale(level, level))
        view.zoom_changed.emit(level)

