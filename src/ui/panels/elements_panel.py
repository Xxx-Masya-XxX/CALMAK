"""Панель элементов - дерево объектов."""

from PySide6.QtWidgets import (
    QAbstractItemView, QMenu, QStyledItemDelegate, QStyleOptionViewItem,
    QTreeView, QVBoxLayout, QWidget, QFrame, QHBoxLayout, QPushButton
)
from PySide6.QtCore import (
    QAbstractItemModel, QMimeData, QModelIndex, QPersistentModelIndex,
    Qt, Signal, QRect
)
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QPen

from ...models import BaseObject, Canvas, TextObject


class TreeNode:
    __slots__ = ("data", "parent", "children", "row_in_parent")

    def __init__(self, data, parent: "TreeNode | None" = None):
        self.data = data
        self.parent: TreeNode | None = parent
        self.children: list[TreeNode] = []
        self.row_in_parent: int = 0

    def append_child(self, node: "TreeNode") -> None:
        node.parent = self
        node.row_in_parent = len(self.children)
        self.children.append(node)

    def remove_child(self, node: "TreeNode") -> None:
        idx = self.children.index(node)
        self.children.pop(idx)
        for i in range(idx, len(self.children)):
            self.children[i].row_in_parent = i

    def insert_child(self, row: int, node: "TreeNode") -> None:
        node.parent = self
        self.children.insert(row, node)
        for i in range(row, len(self.children)):
            self.children[i].row_in_parent = i

    @property
    def is_canvas(self) -> bool:
        return isinstance(self.data, Canvas)

    @property
    def is_object(self) -> bool:
        return isinstance(self.data, BaseObject)

    @property
    def display_text(self) -> str:
        if self.data is None:
            return ""
        if isinstance(self.data, BaseObject) and self.data.locked:
            return f"🔒 {self.data.name}"
        return self.data.name


class SceneTreeModel(QAbstractItemModel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._root = TreeNode(None)
        self._canvas_nodes: dict[str, TreeNode] = {}
        self._obj_nodes: dict[str, TreeNode] = {}
        self._global_index_cache: dict[str, int] = {}

    def _rebuild_global_index(self) -> None:
        counter = [1]

        def _walk(node: TreeNode) -> None:
            for child in node.children:
                if child.is_canvas:
                    _walk(child)
                elif child.is_object:
                    self._global_index_cache[child.data.id] = counter[0]
                    counter[0] += 1
                    _walk(child)

        self._global_index_cache.clear()
        _walk(self._root)

    def global_index_of(self, obj_id: str) -> int | None:
        return self._global_index_cache.get(obj_id)

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = self._node(parent)
        if row < len(parent_node.children):
            return self.createIndex(row, column, parent_node.children[row])
        return QModelIndex()

    def parent(self, index: QModelIndex | QPersistentModelIndex = QModelIndex()) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        node: TreeNode = index.internalPointer()
        parent_node = node.parent
        if parent_node is None or parent_node is self._root:
            return QModelIndex()
        return self.createIndex(parent_node.row_in_parent, 0, parent_node)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._node(parent).children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        node: TreeNode = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return node.display_text
        if role == Qt.ItemDataRole.UserRole:
            return node.data
        if role == Qt.ItemDataRole.ForegroundRole:
            if node.is_canvas:
                return QBrush(QColor(Qt.GlobalColor.darkBlue))
        if role == Qt.ItemDataRole.FontRole:
            if node.is_canvas:
                f = QFont()
                f.setBold(True)
                return f
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        node: TreeNode = index.internalPointer()
        if role == Qt.ItemDataRole.EditRole and node.is_object:
            node.data.name = value
            self.dataChanged.emit(index, index, [role, Qt.ItemDataRole.DisplayRole])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        default = super().flags(index)
        if not index.isValid():
            return default
        node: TreeNode = index.internalPointer()
        flags = default | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if node.is_object:
            flags |= (Qt.ItemFlag.ItemIsEditable
                      | Qt.ItemFlag.ItemIsDragEnabled
                      | Qt.ItemFlag.ItemIsDropEnabled)
        if node.is_canvas:
            flags |= Qt.ItemFlag.ItemIsDragEnabled
        return flags

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return ["application/x-scene-obj-id", "application/x-scene-canvas-id"]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime = QMimeData()
        if indexes:
            node: TreeNode = indexes[0].internalPointer()
            if node.is_object:
                mime.setData("application/x-scene-obj-id", node.data.id.encode())
            elif node.is_canvas:
                mime.setData("application/x-scene-canvas-id", node.data.id.encode())
        return mime

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction,
                        row: int, column: int, parent: QModelIndex) -> bool:
        # Canvas reorder: вставка между канвасами на корневом уровне
        if data.hasFormat("application/x-scene-canvas-id"):
            # разрешаем только вставку между элементами (row >= 0) на корневом уровне
            return row >= 0 and not parent.isValid()

        if not data.hasFormat("application/x-scene-obj-id"):
            return False
        obj_id = data.data("application/x-scene-obj-id").toStdString()
        obj_node = self._obj_nodes.get(obj_id)
        if obj_node is None:
            return False

        if row >= 0:
            # Вставка между элементами
            if not parent.isValid():
                return False
            parent_node: TreeNode = parent.internalPointer()
            # нельзя вставить объект внутрь самого себя
            if parent_node is obj_node:
                return False
            src_canvas = self._canvas_for_node(obj_node)
            dst_canvas = self._canvas_for_node(parent_node) if parent_node.is_object else parent_node
            if src_canvas is None or dst_canvas is None or src_canvas is not dst_canvas:
                return False
            # нельзя вставить родителя в его же потомка
            if self._is_descendant(parent_node, obj_node):
                return False
            return True

        # Drop на элемент
        if not parent.isValid():
            return False
        target_node: TreeNode = parent.internalPointer()
        if target_node.is_canvas:
            return False
        src_canvas = self._canvas_for_node(obj_node)
        dst_canvas = self._canvas_for_node(target_node)
        if src_canvas is None or dst_canvas is None or src_canvas is not dst_canvas:
            return False
        if self._is_descendant(target_node, obj_node):
            return False
        return True

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction,
                     row: int, column: int, parent: QModelIndex) -> bool:
        if not self.canDropMimeData(data, action, row, column, parent):
            return False

        # Перемещение канваса
        if data.hasFormat("application/x-scene-canvas-id"):
            canvas_id = data.data("application/x-scene-canvas-id").toStdString()
            canvas_node = self._canvas_nodes.get(canvas_id)
            if canvas_node is None:
                return False
            old_row = canvas_node.row_in_parent
            insert_row = row if row >= 0 else len(self._root.children)
            if insert_row == old_row or insert_row == old_row + 1:
                return False  # позиция не изменилась
            self.beginRemoveRows(QModelIndex(), old_row, old_row)
            self._root.remove_child(canvas_node)
            self.endRemoveRows()
            if insert_row > old_row:
                insert_row -= 1
            insert_row = min(insert_row, len(self._root.children))
            self.beginInsertRows(QModelIndex(), insert_row, insert_row)
            self._root.insert_child(insert_row, canvas_node)
            self.endInsertRows()
            self._rebuild_global_index()
            return True

        obj_id = data.data("application/x-scene-obj-id").toStdString()
        obj_node = self._obj_nodes[obj_id]
        parent_node: TreeNode = parent.internalPointer()
        new_parent_id = parent_node.data.id if parent_node.is_object else None

        self._recalc_coords(obj_node.data, new_parent_id)

        old_parent_node = obj_node.parent
        old_row = obj_node.row_in_parent
        self.beginRemoveRows(self._index_for_node(old_parent_node), old_row, old_row)
        old_parent_node.remove_child(obj_node)
        self.endRemoveRows()

        insert_row = row if row >= 0 else len(parent_node.children)
        if old_parent_node is parent_node and row > old_row:
            insert_row = max(0, insert_row - 1)
        insert_row = min(insert_row, len(parent_node.children))

        self.beginInsertRows(self._index_for_node(parent_node), insert_row, insert_row)
        parent_node.insert_child(insert_row, obj_node)
        self.endInsertRows()
        self._rebuild_global_index()
        return True

    def add_canvas(self, canvas: Canvas) -> None:
        row = len(self._root.children)
        self.beginInsertRows(QModelIndex(), row, row)
        node = TreeNode(canvas, self._root)
        node.row_in_parent = row
        self._root.children.append(node)
        self._canvas_nodes[canvas.id] = node
        self.endInsertRows()

    def remove_canvas(self, canvas_id: str) -> None:
        node = self._canvas_nodes.pop(canvas_id, None)
        if node is None:
            return
        row = node.row_in_parent
        self.beginRemoveRows(QModelIndex(), row, row)
        self._root.remove_child(node)
        self.endRemoveRows()
        for obj_id in list(self._obj_nodes):
            if self._canvas_for_node(self._obj_nodes[obj_id]) is None:
                del self._obj_nodes[obj_id]

    def add_object(self, canvas_id: str, obj: BaseObject) -> QModelIndex:
        canvas_node = self._canvas_nodes.get(canvas_id)
        if canvas_node is None:
            return QModelIndex()
        parent_node = self._obj_nodes[obj.parent_id] if obj.parent_id and obj.parent_id in self._obj_nodes else canvas_node
        parent_index = self._index_for_node(parent_node)
        row = len(parent_node.children)
        self.beginInsertRows(parent_index, row, row)
        new_node = TreeNode(obj)
        parent_node.append_child(new_node)
        self._obj_nodes[obj.id] = new_node
        self.endInsertRows()
        self._rebuild_global_index()
        return self.createIndex(new_node.row_in_parent, 0, new_node)

    def remove_object(self, canvas_id: str, obj: BaseObject) -> None:
        node = self._obj_nodes.pop(obj.id, None)
        if node is None:
            return
        parent_node = node.parent
        row = node.row_in_parent
        self.beginRemoveRows(self._index_for_node(parent_node), row, row)
        parent_node.remove_child(node)
        self.endRemoveRows()
        self._rebuild_global_index()

    def move_object(self, canvas_id: str, obj: BaseObject, new_parent_id: str | None) -> None:
        node = self._obj_nodes.get(obj.id)
        if node is None:
            return
        self._recalc_coords(obj, new_parent_id)
        canvas_node = self._canvas_nodes.get(canvas_id)
        if canvas_node is None:
            return
        new_parent_node = self._obj_nodes[new_parent_id] if new_parent_id and new_parent_id in self._obj_nodes else canvas_node
        if node.parent is new_parent_node:
            return
        old_parent = node.parent
        old_row = node.row_in_parent
        self.beginRemoveRows(self._index_for_node(old_parent), old_row, old_row)
        old_parent.remove_child(node)
        self.endRemoveRows()
        insert_row = len(new_parent_node.children)
        self.beginInsertRows(self._index_for_node(new_parent_node), insert_row, insert_row)
        new_parent_node.append_child(node)
        self.endInsertRows()
        self._rebuild_global_index()

    def update_canvas_name(self, canvas: Canvas) -> None:
        node = self._canvas_nodes.get(canvas.id)
        if node:
            idx = self.createIndex(node.row_in_parent, 0, node)
            self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole])

    def update_object(self, canvas_id: str, obj: BaseObject) -> None:
        node = self._obj_nodes.get(obj.id)
        if node:
            node.data = obj
            idx = self.createIndex(node.row_in_parent, 0, node)
            self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.DecorationRole])

    def node_for_index(self, index: QModelIndex) -> TreeNode | None:
        return index.internalPointer() if index.isValid() else None

    def _node(self, index: QModelIndex) -> TreeNode:
        return index.internalPointer() if index.isValid() else self._root

    def _index_for_node(self, node: TreeNode) -> QModelIndex:
        if node is self._root or node.parent is None:
            return QModelIndex()
        return self.createIndex(node.row_in_parent, 0, node)

    def _canvas_for_node(self, node: TreeNode) -> TreeNode | None:
        cur = node
        while cur is not None and cur is not self._root:
            if cur.is_canvas:
                return cur
            cur = cur.parent
        return None

    def _canvas_id_for_node(self, node: TreeNode) -> str | None:
        cn = self._canvas_for_node(node)
        return cn.data.id if cn and cn.is_canvas else None

    def get_canvas_id_for_obj(self, obj: BaseObject) -> str | None:
        node = self._obj_nodes.get(obj.id)
        return self._canvas_id_for_node(node) if node else None

    def _is_descendant(self, potential_child: TreeNode, potential_parent: TreeNode) -> bool:
        cur = potential_child.parent
        while cur is not None and cur is not self._root:
            if cur is potential_parent:
                return True
            cur = cur.parent
        return False

    def _recalc_coords(self, obj: BaseObject, new_parent_id: str | None) -> None:
        # Защита от рекурсии: нельзя сделать объект родителем самого себя или потомка
        obj_node = self._obj_nodes.get(obj.id)
        if new_parent_id and obj_node:
            new_parent_node = self._obj_nodes.get(new_parent_id)
            if new_parent_node and (new_parent_id == obj.id or self._is_descendant(new_parent_node, obj_node)):
                return

        # Получаем глобальные координаты ДО изменения родителя
        old_parent_node = self._obj_nodes.get(obj.parent_id) if obj.parent_id else None
        if old_parent_node:
            gp = old_parent_node.data.get_global_position()
            gx, gy = gp[0] + obj.x, gp[1] + obj.y
        else:
            gx, gy = obj.x, obj.y

        # Вычисляем позицию нового родителя ДО изменения obj._parent
        new_parent_obj = self._obj_nodes[new_parent_id].data if new_parent_id and new_parent_id in self._obj_nodes else None
        if new_parent_obj:
            np_ = new_parent_obj.get_global_position()
            new_local_x, new_local_y = gx - np_[0], gy - np_[1]
        else:
            new_local_x, new_local_y = gx, gy

        # Только теперь меняем родителя и координаты
        obj.parent_id = new_parent_id
        obj._parent = new_parent_obj
        obj.x, obj.y = new_local_x, new_local_y

    def all_obj_nodes_for_canvas(self, canvas_id: str) -> dict[str, TreeNode]:
        result = {}
        canvas_node = self._canvas_nodes.get(canvas_id)
        if canvas_node is None:
            return result
        self._collect_obj_nodes(canvas_node, result)
        return result

    def _collect_obj_nodes(self, node: TreeNode, out: dict[str, TreeNode]) -> None:
        for child in node.children:
            if child.is_object:
                out[child.data.id] = child
                self._collect_obj_nodes(child, out)


# ---------------------------------------------------------------------------
# Делегат — рисует индекс и индикатор вставки
# ---------------------------------------------------------------------------

class _DropLineDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drop_row: int = -1
        self._drop_parent: QPersistentModelIndex = QPersistentModelIndex()
        self._drop_on_item: bool = False

    def set_drop_target(self, row: int, parent: QModelIndex, on_item: bool) -> None:
        self._drop_row = row
        self._drop_parent = QPersistentModelIndex(parent)
        self._drop_on_item = on_item

    def clear_drop_target(self) -> None:
        self._drop_row = -1
        self._drop_parent = QPersistentModelIndex()
        self._drop_on_item = False

    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().paint(painter, option, index)

        view: CustomTreeView = self.parent()
        model = view.model()

        # ── Глобальный индекс ────────────────────────────────────────────
        if hasattr(model, "node_for_index") and hasattr(model, "global_index_of"):
            node = model.node_for_index(index)
            if node is not None and node.is_object:
                g_idx = model.global_index_of(node.data.id)
                if g_idx is not None:
                    painter.save()
                    idx_text = str(g_idx)
                    small_font = painter.font()
                    small_font.setPointSizeF(max(6.5, small_font.pointSizeF() - 2))
                    painter.setFont(small_font)
                    fm = painter.fontMetrics()
                    badge_w = fm.horizontalAdvance(idx_text) + 8
                    badge_h = fm.height() + 2
                    badge_x = option.rect.right() - badge_w - 4
                    badge_y = option.rect.top() + (option.rect.height() - badge_h) // 2
                    badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
                    painter.setBrush(QColor(30, 30, 30, 220))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(badge_rect, 3, 3)
                    painter.setPen(QColor(190, 190, 190))
                    painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, idx_text)
                    painter.restore()

        # ── Подсветка drop-on-item ────────────────────────────────────────
        if self._drop_on_item and self._drop_parent.isValid():
            if index == QModelIndex(self._drop_parent):
                painter.save()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 120, 215, 40))
                painter.drawRect(option.rect)
                painter.restore()
            return

        # ── Линия вставки между элементами ───────────────────────────────
        if self._drop_row < 0:
            return

        parent_index = QModelIndex(self._drop_parent) if self._drop_parent.isValid() else QModelIndex()
        row_count = model.rowCount(parent_index)

        # Какой элемент рисует линию?
        # Если вставляем перед строкой N — линия сверху строки N
        # Если вставляем после последнего — линия снизу последнего
        if self._drop_row < row_count:
            target_idx = model.index(self._drop_row, 0, parent_index)
            draw_at_top = True
        else:
            if row_count == 0:
                return
            target_idx = model.index(row_count - 1, 0, parent_index)
            draw_at_top = False

        if index != target_idx:
            return

        rect = option.rect
        y = rect.top() if draw_at_top else rect.bottom()

        # Отступ по уровню вложенности
        level = 0
        p = target_idx.parent()
        while p.isValid():
            level += 1
            p = p.parent()
        x_start = view.indentation() * (level + 1) + 4
        x_end = rect.right() - 4

        painter.save()
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.drawLine(x_start, y, x_end, y)
        # Кружки на концах
        r = 4
        painter.setBrush(QColor(0, 120, 215))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(x_start - r // 2, y - r // 2, r, r)
        painter.drawEllipse(x_end - r // 2, y - r // 2, r, r)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        sh = super().sizeHint(option, index)
        return sh.__class__(sh.width(), max(sh.height(), 36))

    def _nesting_level(self, index: QModelIndex) -> int:
        level = 0
        p = index.parent()
        while p.isValid():
            level += 1
            p = p.parent()
        return level


# ---------------------------------------------------------------------------
# CustomTreeView
# ---------------------------------------------------------------------------

class CustomTreeView(QTreeView):

    canvas_selected = Signal(str)
    object_selected = Signal(BaseObject)
    object_parent_changed = Signal(BaseObject)
    order_changed = Signal(str)
    add_child_requested = Signal(object, str)
    canvas_context_menu = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._model = SceneTreeModel(self)
        self.setModel(self._model)

        self.setHeaderHidden(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(False)   # рисуем свой
        self.setDragDropOverwriteMode(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._delegate = _DropLineDelegate(self)
        self.setItemDelegate(self._delegate)

        # Увеличенные строки и шрифт
        font = self.font()
        font.setPointSize(font.pointSize() + 1)
        self.setFont(font)
        self.setStyleSheet("""
            QTreeView::item {
                padding: 4px 6px;
                min-height: 36px;
            }
            QTreeView::item:selected {
                border-radius: 4px;
            }
            QTreeView::branch {
                padding: 4px 0px;
            }
        """)

        self.customContextMenuRequested.connect(self._show_context_menu)
        self.clicked.connect(self._on_clicked)
        self.doubleClicked.connect(self._on_double_clicked)
        self._model.rowsInserted.connect(lambda parent, *_: self.expand(parent))

    # ── совместимость ────────────────────────────────────────────────────

    @property
    def _canvas_items(self) -> dict[str, QModelIndex]:
        return {cid: self._model._index_for_node(n) for cid, n in self._model._canvas_nodes.items()}

    @property
    def _object_items(self) -> dict[str, dict[str, QModelIndex]]:
        result = {}
        for cid in self._model._canvas_nodes:
            result[cid] = {oid: self._model._index_for_node(n)
                           for oid, n in self._model.all_obj_nodes_for_canvas(cid).items()}
        return result

    @property
    def _obj_to_item(self) -> dict[str, QModelIndex]:
        return {oid: self._model._index_for_node(n) for oid, n in self._model._obj_nodes.items()}

    def setCurrentItem(self, item: QModelIndex) -> None:
        if item is not None and item.isValid():
            self.setCurrentIndex(item)

    # ── публичные методы ─────────────────────────────────────────────────

    def add_canvas(self, canvas: Canvas) -> None:
        self._model.add_canvas(canvas)
        node = self._model._canvas_nodes.get(canvas.id)
        if node:
            self.expand(self._model._index_for_node(node))

    def remove_canvas(self, canvas_id: str) -> None:
        self._model.remove_canvas(canvas_id)

    def add_object(self, canvas_id: str, obj: BaseObject) -> None:
        idx = self._model.add_object(canvas_id, obj)
        if idx.isValid():
            self.expand(self._model.parent(idx))

    def remove_object(self, canvas_id: str, obj: BaseObject) -> None:
        self._model.remove_object(canvas_id, obj)

    def move_object(self, canvas_id: str, obj: BaseObject, new_parent_id: str | None) -> None:
        self._model.move_object(canvas_id, obj, new_parent_id)

    def update_canvas_name(self, canvas: Canvas) -> None:
        self._model.update_canvas_name(canvas)

    def update_object_name(self, canvas_id: str, obj: BaseObject) -> None:
        self._model.update_object(canvas_id, obj)

    def update_object_lock(self, canvas_id: str, obj: BaseObject) -> None:
        self._model.update_object(canvas_id, obj)

    def get_canvas_id_for_object(self, obj: BaseObject) -> str | None:
        return self._model.get_canvas_id_for_obj(obj)

    def get_selected_canvas(self) -> Canvas | None:
        node = self._model.node_for_index(self.currentIndex())
        if node and node.is_canvas:
            return node.data
        if node and node.is_object:
            cn = self._model._canvas_for_node(node)
            return cn.data if cn else None
        return None

    def get_selected_object(self) -> BaseObject | None:
        node = self._model.node_for_index(self.currentIndex())
        return node.data if node and node.is_object else None

    # ── drag & drop ───────────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasFormat("application/x-scene-obj-id") or mime.hasFormat("application/x-scene-canvas-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        mime = event.mimeData()

        # ── Перетаскивание канваса ────────────────────────────────────────
        if mime.hasFormat("application/x-scene-canvas-id"):
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            dragged_id = mime.data("application/x-scene-canvas-id").toStdString()

            if index.isValid():
                node = self._model.node_for_index(index)
                if node and node.is_canvas:
                    rect = self.visualRect(index)
                    rel_y = pos.y() - rect.top()
                    # Верхняя половина — вставить перед, нижняя — вставить после
                    if rel_y < rect.height() / 2:
                        drop_row = index.row()
                    else:
                        drop_row = index.row() + 1
                    # Не показываем индикатор если позиция не меняется
                    dragged_node = self._model._canvas_nodes.get(dragged_id)
                    old_row = dragged_node.row_in_parent if dragged_node else -1
                    if drop_row != old_row and drop_row != old_row + 1:
                        self._delegate.set_drop_target(drop_row, QModelIndex(), False)
                        event.acceptProposedAction()
                    else:
                        self._delegate.clear_drop_target()
                        event.ignore()
                    self.viewport().update()
                    return
            self._delegate.clear_drop_target()
            self.viewport().update()
            event.ignore()
            return

        if not mime.hasFormat("application/x-scene-obj-id"):
            event.ignore()
            return

        pos = event.position().toPoint()
        index = self.indexAt(pos)

        if not index.isValid():
            self._delegate.clear_drop_target()
            self.viewport().update()
            event.ignore()
            return

        node = self._model.node_for_index(index)
        if node is None or not node.is_object:
            self._delegate.clear_drop_target()
            self.viewport().update()
            event.ignore()
            return

        # Получаем перетаскиваемый объект и запрещаем drop на самого себя
        dragged_id = event.mimeData().data("application/x-scene-obj-id").toStdString()
        dragged_node = self._model._obj_nodes.get(dragged_id)
        if dragged_node is node:
            self._delegate.clear_drop_target()
            self.viewport().update()
            event.ignore()
            return

        rect = self.visualRect(index)
        h = rect.height()
        rel_y = pos.y() - rect.top()
        zone = h * 0.28   # верхние/нижние 28% — зоны вставки, центр — дочерний

        if rel_y < zone:
            # вставить ПЕРЕД этим элементом
            drop_row = index.row()
            drop_parent = self._model.parent(index)
            on_item = False
        elif rel_y > h - zone:
            # вставить ПОСЛЕ этого элемента
            drop_row = index.row() + 1
            drop_parent = self._model.parent(index)
            on_item = False
        else:
            # сделать дочерним
            drop_row = -1
            drop_parent = index
            on_item = True

        can = self._model.canDropMimeData(
            event.mimeData(), Qt.DropAction.MoveAction,
            drop_row, 0, drop_parent)

        if can:
            self._delegate.set_drop_target(drop_row, drop_parent, on_item)
            event.acceptProposedAction()
        else:
            self._delegate.clear_drop_target()
            event.ignore()

        self.viewport().update()

    def dragLeaveEvent(self, event) -> None:
        self._delegate.clear_drop_target()
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        mime = event.mimeData()

        # ── Перетаскивание канваса ────────────────────────────────────────
        if mime.hasFormat("application/x-scene-canvas-id"):
            drop_row = self._delegate._drop_row
            self._delegate.clear_drop_target()
            self.viewport().update()
            ok = self._model.dropMimeData(
                mime, Qt.DropAction.MoveAction, drop_row, 0, QModelIndex())
            if ok:
                event.acceptProposedAction()
            else:
                event.ignore()
            return

        if not mime.hasFormat("application/x-scene-obj-id"):
            event.ignore()
            return

        drop_row = self._delegate._drop_row
        drop_parent_pi = self._delegate._drop_parent
        on_item = self._delegate._drop_on_item

        self._delegate.clear_drop_target()
        self.viewport().update()

        drop_parent = QModelIndex(drop_parent_pi) if drop_parent_pi.isValid() else QModelIndex()
        row_arg = -1 if on_item else drop_row

        ok = self._model.dropMimeData(
            event.mimeData(), Qt.DropAction.MoveAction,
            row_arg, 0, drop_parent)

        if ok:
            event.acceptProposedAction()
            obj_id = event.mimeData().data("application/x-scene-obj-id").toStdString()
            node = self._model._obj_nodes.get(obj_id)
            if node:
                self.object_parent_changed.emit(node.data)
                canvas_node = self._model._canvas_for_node(node)
                if canvas_node and canvas_node.is_canvas:
                    self.order_changed.emit(canvas_node.data.id)
        else:
            event.ignore()

    # ── обработчики ───────────────────────────────────────────────────────

    def _on_clicked(self, index: QModelIndex) -> None:
        node = self._model.node_for_index(index)
        if node:
            if node.is_canvas:
                self.canvas_selected.emit(node.data.id)
            elif node.is_object:
                self.object_selected.emit(node.data)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        if self.isExpanded(index):
            self.collapse(index)
        else:
            self.expand(index)

    def _show_context_menu(self, pos) -> None:
        index = self.indexAt(pos)
        node = self._model.node_for_index(index)
        if node is None:
            return
        menu = QMenu(self)
        if node.is_canvas:
            add_rect = menu.addAction("Добавить прямоугольник")
            add_text = menu.addAction("Добавить текст")
            add_rect.triggered.connect(lambda: self.canvas_context_menu.emit(node.data))
            add_text.triggered.connect(lambda: self.canvas_context_menu.emit(node.data))
        elif node.is_object:
            add_rect = menu.addAction("Добавить дочерний прямоугольник")
            add_text = menu.addAction("Добавить дочерний текст")
            add_rect.triggered.connect(lambda: self.add_child_requested.emit(node.data, "rect"))
            add_text.triggered.connect(lambda: self.add_child_requested.emit(node.data, "text"))
        menu.exec(self.viewport().mapToGlobal(pos))


# ---------------------------------------------------------------------------
# ElementsPanel
# ---------------------------------------------------------------------------

class ElementsPanel(QFrame):

    canvas_selected = Signal(str)
    object_selected = Signal(BaseObject)
    object_parent_changed = Signal(BaseObject)
    order_changed = Signal(str)
    add_child_requested = Signal(object, str)
    canvas_context_menu = Signal(object)

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        from PySide6.QtWidgets import QLabel
        title_label = QLabel("Элементы")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addWidget(header_frame)

        self.tree = CustomTreeView()
        layout.addWidget(self.tree)

        self.tree.canvas_selected.connect(self.canvas_selected.emit)
        self.tree.object_selected.connect(self.object_selected.emit)
        self.tree.object_parent_changed.connect(self.object_parent_changed.emit)
        self.tree.order_changed.connect(self.order_changed.emit)
        self.tree.add_child_requested.connect(self.add_child_requested.emit)
        self.tree.canvas_context_menu.connect(self.canvas_context_menu.emit)

    def add_canvas(self, canvas: Canvas):
        self.tree._model.add_canvas(canvas)

    def remove_canvas(self, canvas_id: str):
        self.tree._model.remove_canvas(canvas_id)

    def add_object(self, canvas_id: str, obj: BaseObject):
        self.tree._model.add_object(canvas_id, obj)

    def remove_object(self, canvas_id: str, obj: BaseObject):
        self.tree._model.remove_object(canvas_id, obj)

    def update_canvas_name(self, canvas: Canvas):
        self.tree._model.update_canvas_name(canvas)

    def update_object_name(self, canvas_id: str, obj: BaseObject):
        self.tree._model.update_object(canvas_id, obj)

    def update_object_lock(self, canvas_id: str, obj: BaseObject):
        self.tree._model.update_object(canvas_id, obj)