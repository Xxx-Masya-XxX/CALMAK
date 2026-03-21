"""
ElementTreePanel — кастомное дерево слоёв без QTreeWidget.

Реализовано на QScrollArea + QWidget + ручная отрисовка.
Drag/drop с визуальным индикатором:
  - Синяя линия между items → reorder (переставить)
  - Синяя рамка вокруг item → reparent (сделать дочерним)
  - Нельзя дропнуть объект внутрь Canvas-строки

После drop → TreeRearrangeCommand → undo/redo работает.
Кнопки Forward/Backward → ReorderObjectCommand → дерево обновляется.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import (Qt, QPoint, QRect, QSize, QMimeData,
                             Signal, QTimer)
from PySide6.QtGui import (QColor, QFont, QPainter, QPen, QBrush,
                            QDrag, QCursor, QMouseEvent, QPaintEvent,
                            QFontMetrics)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QFrame, QSizePolicy, QApplication, QAbstractScrollArea,
)

from domain.models import ObjectType, ObjectState, CanvasState
from ui.constants import C, ICONS, OBJECT_COLORS, LAYER, menu_stylesheet

if TYPE_CHECKING:
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController


# ---------------------------------------------------------------------------
# Local aliases from ui.constants (for readability)
# ---------------------------------------------------------------------------

ITEM_H    = LAYER.ITEM_H
INDENT    = LAYER.INDENT
ICON_W    = LAYER.ICON_W
TOGGLE_W  = LAYER.TOGGLE_W
PAD_LEFT  = LAYER.PAD_LEFT


# ---------------------------------------------------------------------------
# Node — внутреннее представление строки
# ---------------------------------------------------------------------------

class Node:
    """Одна строка в дереве."""
    __slots__ = ("kind", "obj_id", "canvas_id", "depth",
                 "expanded", "parent_node", "children")

    def __init__(self, kind: str, obj_id: str, canvas_id: str,
                 depth: int, parent_node: "Node | None" = None):
        self.kind        = kind          # "canvas" | "object"
        self.obj_id      = obj_id        # canvas_id or obj_id
        self.canvas_id   = canvas_id
        self.depth       = depth
        self.expanded    = True
        self.parent_node = parent_node
        self.children: list[Node] = []

    @property
    def is_canvas(self) -> bool:
        return self.kind == "canvas"

    @property
    def is_object(self) -> bool:
        return self.kind == "object"


# ---------------------------------------------------------------------------
# DropTarget — куда дропнуть
# ---------------------------------------------------------------------------

class DropTarget:
    """Результат hit-test при drag."""
    NONE    = "none"
    BEFORE  = "before"   # вставить перед node (синяя линия сверху)
    AFTER   = "after"    # вставить после node (синяя линия снизу)
    INTO    = "into"     # сделать дочерним node (синяя рамка)

    def __init__(self, mode: str = NONE,
                 node: Node | None = None,
                 y_line: int = 0):
        self.mode   = mode
        self.node   = node
        self.y_line = y_line   # координата для линии BEFORE/AFTER

    def is_valid(self) -> bool:
        return self.mode != self.NONE and self.node is not None


# ---------------------------------------------------------------------------
# LayerTreeWidget — основной виджет
# ---------------------------------------------------------------------------

class LayerTreeWidget(QWidget):
    """
    Кастомное дерево слоёв.
    Рисует строки вручную, обрабатывает drag/drop самостоятельно.
    """

    # Сигналы
    selection_changed  = Signal(list)         # [obj_id, ...]
    drop_rearranged    = Signal()             # структура изменилась
    context_requested  = Signal(QPoint, object)  # (global_pos, node|None)

    def __init__(self, store: "EditorStore",
                 controller: "EditorController", parent=None):
        super().__init__(parent)
        self._store      = store
        self._controller = controller

        self._nodes: list[Node] = []        # плоский список видимых строк
        self._selected: set[str] = set()    # выбранные obj_id
        self._hover_idx: int = -1

        # Drag state
        self._drag_node:  Node | None = None
        self._drag_start: QPoint = QPoint()
        self._dragging    = False
        self._drop_target = DropTarget()

        # Expand state: {obj_id: bool}
        self._expanded: dict[str, bool] = {}

        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Repaint when theme changes (custom QPainter uses C.* colors)
        from ui.theme import theme_manager
        theme_manager.theme_changed.connect(lambda *_: self.update())

    # -----------------------------------------------------------------------
    # Build flat node list from DocumentState
    # -----------------------------------------------------------------------

    def rebuild(self):
        doc = self._store.document
        self._nodes.clear()

        for canvas_id, canvas in doc.canvases.items():
            active = canvas_id == doc.active_canvas_id
            cn = Node("canvas", canvas_id, canvas_id, 0)
            cn.expanded = self._expanded.get(f"canvas:{canvas_id}", True)
            self._nodes.append(cn)

            if cn.expanded:
                for obj_id in reversed(canvas.root_ids):
                    obj = canvas.objects.get(obj_id)
                    if obj:
                        self._add_object_nodes(canvas, obj, 1, cn)

        self._update_height()
        self.update()

    def _add_object_nodes(self, canvas: CanvasState,
                          obj: ObjectState, depth: int,
                          parent_node: Node):
        n = Node("object", obj.id, canvas.id, depth, parent_node)
        n.expanded = self._expanded.get(obj.id, True)
        parent_node.children.append(n)
        self._nodes.append(n)

        if n.expanded and obj.children_ids:
            for child_id in reversed(obj.children_ids):
                child = canvas.objects.get(child_id)
                if child:
                    self._add_object_nodes(canvas, child, depth + 1, n)

    def _update_height(self):
        h = max(len(self._nodes) * ITEM_H, 40)
        self.setMinimumHeight(h)
        self.resize(self.width(), h)

    # -----------------------------------------------------------------------
    # Update only labels (no structural change)
    # -----------------------------------------------------------------------

    def update_labels(self):
        self.update()

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def set_selection(self, obj_ids: list[str]):
        self._selected = set(obj_ids)
        self.update()

    def _node_at(self, y: int) -> Node | None:
        idx = y // ITEM_H
        if 0 <= idx < len(self._nodes):
            return self._nodes[idx]
        return None

    def _idx_of(self, node: Node) -> int:
        try:
            return self._nodes.index(node)
        except ValueError:
            return -1

    # -----------------------------------------------------------------------
    # Paint
    # -----------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), C.TREE_BG)

        doc = self._store.document
        font = QFont("Segoe UI", 10)
        font_bold = QFont("Segoe UI", 10)
        font_bold.setBold(True)
        fm = QFontMetrics(font)

        for i, node in enumerate(self._nodes):
            y = i * ITEM_H
            rect = QRect(0, y, self.width(), ITEM_H)

            # Background
            is_sel = node.is_object and node.obj_id in self._selected
            is_hover = i == self._hover_idx and not is_sel

            if is_sel:
                p.fillRect(rect, C.SEL_BG)
            elif is_hover:
                p.fillRect(rect, C.HOVER)

            x = PAD_LEFT + node.depth * INDENT

            if node.is_canvas:
                # Canvas header
                canvas = doc.canvases.get(node.obj_id)
                if not canvas:
                    continue
                active = node.obj_id == doc.active_canvas_id

                # Toggle arrow
                tx = x
                has_children = bool(canvas.root_ids)
                if has_children:
                    p.setPen(QPen(C.TEXT_DIM))
                    arrow = "▼" if node.expanded else "▶"
                    p.setFont(QFont("Segoe UI", 7))
                    p.drawText(QRect(tx, y, TOGGLE_W, ITEM_H),
                               Qt.AlignVCenter | Qt.AlignLeft, arrow)

                # Icon + name
                ix = tx + TOGGLE_W + 2
                p.setFont(QFont("Segoe UI", 10))
                p.setPen(QPen(C.TEXT_DIM))
                p.drawText(QRect(ix, y, ICON_W, ITEM_H),
                           Qt.AlignVCenter | Qt.AlignLeft, "🎨")

                p.setFont(font_bold if active else font)
                color = C.TEXT_CANVAS if active else C.TEXT_CANVAS_DIM
                if is_sel:
                    color = C.SEL_FG
                p.setPen(QPen(color))
                name = (canvas.name or "Canvas") + ("  ●" if active else "")
                nx = ix + ICON_W + 2
                p.drawText(QRect(nx, y, self.width() - nx - 4, ITEM_H),
                           Qt.AlignVCenter | Qt.AlignLeft,
                           fm.elidedText(name, Qt.ElideRight,
                                         self.width() - nx - 8))

                # Bottom separator
                p.setPen(QPen(C.TREE_ROW_SEP))
                p.drawLine(0, y + ITEM_H - 1, self.width(), y + ITEM_H - 1)

            else:
                # Object row
                canvas = doc.canvases.get(node.canvas_id)
                if not canvas:
                    continue
                obj = canvas.objects.get(node.obj_id)
                if not obj:
                    continue

                # Toggle (only if has children)
                tx = x
                if obj.children_ids:
                    p.setPen(QPen(C.TEXT_DIM))
                    arrow = "▼" if node.expanded else "▶"
                    p.setFont(QFont("Segoe UI", 7))
                    p.drawText(QRect(tx, y, TOGGLE_W, ITEM_H),
                               Qt.AlignVCenter | Qt.AlignLeft, arrow)

                # Type icon
                ix = tx + TOGGLE_W + 2
                icon  = ICONS.get(obj.type)
                icolor = OBJECT_COLORS.get(obj.type)
                if obj.locked:
                    icolor = C.TEXT_MUTED
                p.setFont(QFont("Segoe UI", 10))
                p.setPen(QPen(icolor))
                p.drawText(QRect(ix, y, ICON_W, ITEM_H),
                           Qt.AlignVCenter | Qt.AlignLeft, icon)

                # Name
                nx = ix + ICON_W + 2
                p.setFont(font)
                name_color = (C.SEL_FG if is_sel
                              else C.TEXT_MUTED if obj.locked
                              else C.TEXT)
                p.setPen(QPen(name_color))

                name = obj.name
                badges = ""
                if not obj.visible: badges += " 👁"
                if obj.locked:      badges += " 🔒"

                p.drawText(QRect(nx, y, self.width() - nx - 4, ITEM_H),
                           Qt.AlignVCenter | Qt.AlignLeft,
                           fm.elidedText(name + badges, Qt.ElideRight,
                                         self.width() - nx - 8))

        # Drop indicator
        dt = self._drop_target
        if dt.is_valid():
            if dt.mode in (DropTarget.BEFORE, DropTarget.AFTER):
                # Синяя горизонтальная линия
                p.setPen(QPen(C.DROP_LINE, 2))
                p.setBrush(QBrush(C.DROP_LINE))
                p.drawLine(4, dt.y_line, self.width() - 4, dt.y_line)
                # Кружок слева
                p.drawEllipse(QPoint(6, dt.y_line), 4, 4)
            elif dt.mode == DropTarget.INTO:
                # Синяя рамка вокруг target
                idx = self._idx_of(dt.node)
                if idx >= 0:
                    ry = idx * ITEM_H + 1
                    p.setPen(QPen(C.DROP_RECT, 2))
                    p.setBrush(Qt.transparent)
                    p.drawRoundedRect(
                        QRect(2, ry, self.width() - 4, ITEM_H - 2), 3, 3)

        p.end()

    # -----------------------------------------------------------------------
    # Mouse events
    # -----------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        node = self._node_at(event.pos().y())
        if not node:
            return

        # Toggle expand/collapse
        x = event.pos().x()
        toggle_x = PAD_LEFT + node.depth * INDENT
        if x < toggle_x + TOGGLE_W + INDENT:
            # Check if click on toggle area
            has_toggle = False
            if node.is_canvas:
                doc = self._store.document
                canvas = doc.canvases.get(node.obj_id)
                has_toggle = bool(canvas and canvas.root_ids)
            else:
                doc = self._store.document
                canvas = doc.canvases.get(node.canvas_id)
                obj = canvas.objects.get(node.obj_id) if canvas else None
                has_toggle = bool(obj and obj.children_ids)

            if has_toggle and x >= toggle_x and x < toggle_x + TOGGLE_W + 4:
                self._toggle_expand(node)
                return

        if event.button() == Qt.LeftButton:
            multi = bool(event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier))

            if node.is_canvas:
                # Клик по canvas — переключить активный
                self._controller.switch_canvas(node.obj_id)
                return

            if node.is_object:
                if multi:
                    if node.obj_id in self._selected:
                        self._selected.discard(node.obj_id)
                    else:
                        self._selected.add(node.obj_id)
                else:
                    self._selected = {node.obj_id}

                self.selection_changed.emit(list(self._selected))

                # Начало drag
                self._drag_node  = node
                self._drag_start = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        # Hover
        node = self._node_at(event.pos().y())
        new_hover = self._nodes.index(node) if node else -1
        if new_hover != self._hover_idx:
            self._hover_idx = new_hover
            self.update()

        # Начать drag если достаточно сдвинулись
        if (self._drag_node and not self._dragging and
                event.buttons() & Qt.LeftButton):
            dist = (event.pos() - self._drag_start).manhattanLength()
            if dist > QApplication.startDragDistance():
                self._dragging = True

        if self._dragging:
            dt = self._calc_drop_target(event.pos())
            if (dt.mode != self._drop_target.mode or
                    dt.node is not self._drop_target.node or
                    dt.y_line != self._drop_target.y_line):
                self._drop_target = dt
                self.update()
            self.setCursor(Qt.DragMoveCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging and self._drag_node and self._drop_target.is_valid():
            self._apply_drop(self._drag_node, self._drop_target)

        self._dragging    = False
        self._drag_node   = None
        self._drop_target = DropTarget()
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        node = self._node_at(event.pos().y())
        if node and node.is_object:
            doc = self._store.document
            canvas = doc.canvases.get(node.canvas_id)
            obj = canvas.objects.get(node.obj_id) if canvas else None
            if obj and obj.type == ObjectType.TEXT:
                from ui.dialogs.text_dialog import TextEditDialog
                dlg = TextEditDialog(obj, self)
                if dlg.exec():
                    self._controller.update_properties(
                        node.obj_id, {"payload_text": dlg.get_text()})

    def contextMenuEvent(self, event):
        node = self._node_at(event.pos().y())
        self.context_requested.emit(event.globalPos(), node)

    def leaveEvent(self, event):
        self._hover_idx = -1
        self.update()

    # -----------------------------------------------------------------------
    # Expand / Collapse
    # -----------------------------------------------------------------------

    def _toggle_expand(self, node: Node):
        if node.is_canvas:
            key = f"canvas:{node.obj_id}"
        else:
            key = node.obj_id
        self._expanded[key] = not self._expanded.get(key, True)
        # Пересоздать плоский список
        self.rebuild()

    # -----------------------------------------------------------------------
    # Drop target calculation
    # -----------------------------------------------------------------------

    def _calc_drop_target(self, pos: QPoint) -> DropTarget:
        """
        Определяет куда дропнуть dragged_node исходя из позиции мыши.

        Логика:
          - Верхняя 30% строки → BEFORE (линия сверху)
          - Нижняя 30% строки → AFTER  (линия снизу)
          - Средняя 40% строки + не canvas → INTO (рамка)
          - Нельзя дропнуть в себя или в своего потомка
        """
        drag = self._drag_node
        if not drag:
            return DropTarget()

        idx = pos.y() // ITEM_H
        local_y = pos.y() % ITEM_H

        # Клэмп к последнему элементу
        if idx >= len(self._nodes):
            if not self._nodes:
                return DropTarget()
            # After last
            last = self._nodes[-1]
            if last is drag or self._is_descendant(drag, last):
                return DropTarget()
            return DropTarget(DropTarget.AFTER, last,
                              len(self._nodes) * ITEM_H - 1)

        target = self._nodes[idx]

        # Нельзя дропнуть в себя
        if target is drag:
            return DropTarget()

        # Нельзя дропнуть в потомка
        if self._is_descendant(drag, target):
            return DropTarget()

        top_zone    = ITEM_H * 0.30
        bottom_zone = ITEM_H * 0.70

        if target.is_canvas:
            # На canvas: только BEFORE/AFTER (по краям) — INTO недоступно
            if local_y < top_zone:
                return DropTarget(DropTarget.BEFORE, target,
                                  idx * ITEM_H)
            else:
                return DropTarget(DropTarget.AFTER, target,
                                  (idx + 1) * ITEM_H)
        else:
            if local_y < top_zone:
                return DropTarget(DropTarget.BEFORE, target,
                                  idx * ITEM_H)
            elif local_y > bottom_zone:
                return DropTarget(DropTarget.AFTER, target,
                                  (idx + 1) * ITEM_H)
            else:
                return DropTarget(DropTarget.INTO, target, 0)

    def _is_descendant(self, ancestor: Node, node: Node) -> bool:
        """Проверяет, является ли node потомком ancestor."""
        cur = node.parent_node
        while cur:
            if cur is ancestor:
                return True
            cur = cur.parent_node
        return False

    # -----------------------------------------------------------------------
    # Apply drop
    # -----------------------------------------------------------------------

    def _apply_drop(self, drag: Node, target: DropTarget):
        """
        Применяет перестановку к DocumentState через TreeRearrangeCommand.
        """
        from commands.commands import TreeRearrangeCommand

        doc    = self._store.document
        canvas = doc.canvases.get(drag.canvas_id)
        if not canvas:
            return

        # Снимок ДО
        snap_before = TreeRearrangeCommand.take_snapshot(canvas)

        obj     = canvas.objects.get(drag.obj_id)
        if not obj:
            return

        t_node  = target.node
        t_mode  = target.mode

        # Определяем новое место вставки
        if t_mode == DropTarget.INTO:
            # Сделать дочерним t_node
            t_obj = canvas.objects.get(t_node.obj_id) if t_node.is_object else None
            if not t_obj:
                return
            self._detach(canvas, obj)
            t_obj.children_ids.append(obj.obj_id if hasattr(obj, 'obj_id') else drag.obj_id)
            obj.parent_id = t_node.obj_id

        elif t_mode in (DropTarget.BEFORE, DropTarget.AFTER):
            if t_node.is_canvas:
                # Вставить в root этого canvas (сверху/снизу)
                t_canvas = doc.canvases.get(t_node.obj_id)
                if not t_canvas or t_canvas is not canvas:
                    return  # cross-canvas not supported yet
                # Вставить в начало root_ids (верхний слой)
                self._detach(canvas, obj)
                if t_mode == DropTarget.BEFORE:
                    canvas.root_ids.insert(0, drag.obj_id)
                else:
                    canvas.root_ids.append(drag.obj_id)
                obj.parent_id = None
            else:
                # Вставить до/после t_node в его родительском списке
                t_obj = canvas.objects.get(t_node.obj_id)
                if not t_obj:
                    return

                # Найти родительский список
                if t_obj.parent_id:
                    parent_obj = canvas.objects.get(t_obj.parent_id)
                    lst = parent_obj.children_ids if parent_obj else canvas.root_ids
                    new_parent_id = t_obj.parent_id
                else:
                    lst = canvas.root_ids
                    new_parent_id = None

                self._detach(canvas, obj)
                # Найти позицию target в обновлённом списке
                try:
                    t_idx = lst.index(t_node.obj_id)
                except ValueError:
                    lst.append(drag.obj_id)
                    obj.parent_id = new_parent_id
                    canvas.recalc_z_indices()
                    return

                ins_idx = t_idx if t_mode == DropTarget.BEFORE else t_idx + 1
                lst.insert(ins_idx, drag.obj_id)
                obj.parent_id = new_parent_id

        canvas.recalc_z_indices()

        # Снимок ПОСЛЕ
        snap_after = TreeRearrangeCommand.take_snapshot(canvas)

        # Пушим в историю
        cmd = TreeRearrangeCommand(canvas.id, snap_before, snap_after)
        self._store.history._undo_stack.append(cmd)
        self._store.history._redo_stack.clear()
        self._store._emit_history()
        self._store.document.dirty = True

        # Перестраиваем дерево и обновляем сцену
        self.rebuild()
        self._store.document_changed.emit()
        self.drop_rearranged.emit()

    def _detach(self, canvas: CanvasState, obj: ObjectState):
        """Отсоединяет obj от текущего родителя."""
        if obj.parent_id:
            parent = canvas.objects.get(obj.parent_id)
            if parent:
                parent.children_ids = [i for i in parent.children_ids
                                        if i != obj.id]
        else:
            canvas.root_ids = [i for i in canvas.root_ids if i != obj.id]
        obj.parent_id = None


# ---------------------------------------------------------------------------
# ElementTreePanel
# ---------------------------------------------------------------------------

class ElementTreePanel(QWidget):
    def __init__(self, store: "EditorStore",
                 controller: "EditorController"):
        super().__init__()
        self._store      = store
        self._controller = controller
        self._updating_selection = False

        self._setup_ui()
        self._connect_signals()
        self.full_rebuild()

    # -----------------------------------------------------------------------
    # UI
    # -----------------------------------------------------------------------

    def _setup_ui(self):
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("border-bottom:1px solid palette(mid);")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 6, 8, 6)
        lbl = QLabel("Layers")
        lbl.setStyleSheet("font-weight:bold;font-size:12px;")
        hl.addWidget(lbl)
        hl.addStretch()
        layout.addWidget(header)

        # Scroll area with our custom widget
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea{border:none;}")

        self._tree = LayerTreeWidget(self._store, self._controller)
        self._tree.selection_changed.connect(self._on_tree_selection)
        self._tree.context_requested.connect(self._on_context_menu)

        self._scroll.setWidget(self._tree)
        layout.addWidget(self._scroll)

    # -----------------------------------------------------------------------
    # Signals
    # -----------------------------------------------------------------------

    def _connect_signals(self):
        self._store.document_structure_changed.connect(self.full_rebuild)
        self._store.document_changed.connect(self._update_labels)
        self._store.selection_changed.connect(self._on_selection_changed)
        self._store.canvas_switched.connect(lambda _: self.full_rebuild())

    # -----------------------------------------------------------------------
    # Rebuild / labels
    # -----------------------------------------------------------------------

    def full_rebuild(self):
        self._tree.rebuild()
        self._highlight_selection()

    def _update_labels(self):
        self._tree.update_labels()

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def _on_tree_selection(self, obj_ids: list[str]):
        if self._updating_selection:
            return
        self._updating_selection = True
        self._controller.select(obj_ids)
        self._updating_selection = False

    def _on_selection_changed(self, ids, active_id):
        if not self._updating_selection:
            self._highlight_selection()

    def _highlight_selection(self):
        self._tree.set_selection(list(self._store.selection.selected_ids))

    # -----------------------------------------------------------------------
    # Context menu
    # -----------------------------------------------------------------------

    def _on_context_menu(self, global_pos: QPoint, node):
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setStyleSheet(menu_stylesheet())

        if node and node.is_object:
            obj_id    = node.obj_id
            doc       = self._store.document
            canvas    = doc.canvases.get(node.canvas_id)
            obj       = canvas.objects.get(obj_id) if canvas else None

            if obj_id not in self._store.selection.selected_ids:
                self._controller.select_one(obj_id)

            if obj:
                t = menu.addAction(obj.name)
                t.setEnabled(False)
                menu.addSeparator()

            menu.addAction("✂  Duplicate", self._controller.duplicate_selected)
            menu.addAction("🗑  Delete",   self._controller.delete_selected)
            menu.addSeparator()

            if obj:
                a_lock = menu.addAction("🔒  Locked")
                a_lock.setCheckable(True); a_lock.setChecked(obj.locked)
                a_lock.triggered.connect(
                    lambda c, oid=obj_id:
                        self._controller.update_properties(oid, {"locked": c}))

                a_vis = menu.addAction("👁  Visible")
                a_vis.setCheckable(True); a_vis.setChecked(obj.visible)
                a_vis.triggered.connect(
                    lambda c, oid=obj_id:
                        self._controller.update_properties(oid, {"visible": c}))

            menu.addSeparator()
            menu.addAction("⬆  Bring Forward",
                           lambda: self._controller.bring_forward(obj_id))
            menu.addAction("⬇  Send Backward",
                           lambda: self._controller.send_backward(obj_id))

        elif node and node.is_canvas:
            menu.addAction("➕  Add Canvas",
                           lambda: self._controller.add_canvas("New Canvas"))
            menu.addSeparator()
            menu.addAction("▭  Add Rect",    self._controller.add_rect)
            menu.addAction("◯  Add Ellipse", self._controller.add_ellipse)
            menu.addAction("T  Add Text",    lambda: self._controller.add_text())
        else:
            menu.addAction("▭  Add Rect",    self._controller.add_rect)
            menu.addAction("◯  Add Ellipse", self._controller.add_ellipse)
            menu.addAction("T  Add Text",    lambda: self._controller.add_text())

        if not menu.isEmpty():
            menu.exec(global_pos)
