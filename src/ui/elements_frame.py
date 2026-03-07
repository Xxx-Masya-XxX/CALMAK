"""Панель элементов - дерево объектов (кастомная реализация без QTreeWidget)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import (
    QAbstractItemModel,
    QMimeData,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon

from ..models import BaseObject, Canvas, TextObject


# ---------------------------------------------------------------------------
# Узел дерева
# ---------------------------------------------------------------------------

class TreeNode:
    """Узел кастомного дерева."""

    __slots__ = ("data", "parent", "children", "row_in_parent")

    def __init__(self, data: Any, parent: "TreeNode | None" = None):
        self.data = data                  # Canvas | BaseObject | None (root)
        self.parent: TreeNode | None = parent
        self.children: list[TreeNode] = []
        self.row_in_parent: int = 0       # кэш — обновляется при вставке/удалении

    # ------------------------------------------------------------------
    def append_child(self, node: "TreeNode") -> None:
        node.parent = self
        node.row_in_parent = len(self.children)
        self.children.append(node)

    def remove_child(self, node: "TreeNode") -> None:
        idx = self.children.index(node)
        self.children.pop(idx)
        # пересчитываем row_in_parent для сдвинувшихся
        for i in range(idx, len(self.children)):
            self.children[i].row_in_parent = i

    def insert_child(self, row: int, node: "TreeNode") -> None:
        node.parent = self
        self.children.insert(row, node)
        for i in range(row, len(self.children)):
            self.children[i].row_in_parent = i

    # ------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Модель дерева
# ---------------------------------------------------------------------------

class SceneTreeModel(QAbstractItemModel):
    """Кастомная модель для дерева сцены (Canvas → BaseObject)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._root = TreeNode(None)          # невидимый корень

        # быстрый доступ по id
        self._canvas_nodes: dict[str, TreeNode] = {}
        self._obj_nodes: dict[str, TreeNode] = {}   # obj_id → TreeNode

    # ------------------------------------------------------------------
    # QAbstractItemModel API
    # ------------------------------------------------------------------

    def index(self, row: int, column: int,
              parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = self._node(parent)
        if row < len(parent_node.children):
            child = parent_node.children[row]
            return self.createIndex(row, column, child)
        return QModelIndex()

    def parent(self, index: QModelIndex | QPersistentModelIndex = QModelIndex()) -> QModelIndex:  # type: ignore[override]
        if not index.isValid():
            return QModelIndex()
        node: TreeNode = index.internalPointer()  # type: ignore[assignment]
        parent_node = node.parent
        if parent_node is None or parent_node is self._root:
            return QModelIndex()
        return self.createIndex(parent_node.row_in_parent, 0, parent_node)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._node(parent).children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        node: TreeNode = index.internalPointer()  # type: ignore[assignment]

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

    def setData(self, index: QModelIndex, value: Any,
                role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        node: TreeNode = index.internalPointer()  # type: ignore[assignment]
        if role == Qt.ItemDataRole.EditRole and node.is_object:
            node.data.name = value
            self.dataChanged.emit(index, index, [role, Qt.ItemDataRole.DisplayRole])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        default = super().flags(index)
        if not index.isValid():
            return default
        node: TreeNode = index.internalPointer()  # type: ignore[assignment]
        flags = default | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if node.is_object:
            flags |= (Qt.ItemFlag.ItemIsEditable
                      | Qt.ItemFlag.ItemIsDragEnabled
                      | Qt.ItemFlag.ItemIsDropEnabled)
        return flags

    # Drag & Drop MIME
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return ["application/x-scene-obj-id"]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime = QMimeData()
        if indexes:
            node: TreeNode = indexes[0].internalPointer()  # type: ignore[assignment]
            if node.is_object:
                mime.setData("application/x-scene-obj-id",
                             node.data.id.encode())
        return mime

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction,
                        row: int, column: int, parent: QModelIndex) -> bool:
        if not data.hasFormat("application/x-scene-obj-id"):
            return False
        obj_id = data.data("application/x-scene-obj-id").toStdString()
        obj_node = self._obj_nodes.get(obj_id)
        if obj_node is None:
            return False

        # row >= 0  →  вставка между элементами (reorder)
        # row == -1 →  drop на элемент (смена родителя)
        if row >= 0:
            # вставка между элементами внутри parent-узла
            if not parent.isValid():
                # корень — запрещаем (канвасы не перетаскиваем)
                return False
            parent_node: TreeNode = parent.internalPointer()  # type: ignore[assignment]
            # допускаем вставку внутри канваса (siblings) или внутри объекта
            src_canvas = self._canvas_for_node(obj_node)
            dst_canvas = self._canvas_for_node(parent_node) if parent_node.is_object else parent_node
            if src_canvas is None or dst_canvas is None or src_canvas is not dst_canvas:
                return False
            if parent_node.is_object and self._is_descendant(parent_node, obj_node):
                return False
            return True

        # row == -1: drop прямо на элемент
        if not parent.isValid():
            return False
        target_node: TreeNode = parent.internalPointer()  # type: ignore[assignment]
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

        obj_id = data.data("application/x-scene-obj-id").toStdString()
        obj_node = self._obj_nodes[obj_id]

        if row >= 0:
            # ── вставка между элементами (reorder / смена уровня) ──────────
            parent_node: TreeNode = parent.internalPointer()  # type: ignore[assignment]
            new_parent_id = parent_node.data.id if parent_node.is_object else None
        else:
            # ── drop на элемент → делаем его дочерним ──────────────────────
            parent_node = parent.internalPointer()  # type: ignore[assignment]
            new_parent_id = parent_node.data.id if parent_node.is_object else None

        # пересчёт координат объекта
        self._recalc_coords(obj_node.data, new_parent_id)

        # удаляем узел со старого места
        old_parent_node = obj_node.parent
        old_row = obj_node.row_in_parent
        old_parent_index = self._index_for_node(old_parent_node)
        self.beginRemoveRows(old_parent_index, old_row, old_row)
        old_parent_node.remove_child(obj_node)
        self.endRemoveRows()

        # корректируем insert_row если вставляем в тот же parent после удаления
        insert_row = row if row >= 0 else len(parent_node.children)
        if old_parent_node is parent_node and row > old_row:
            insert_row = max(0, insert_row - 1)
        insert_row = min(insert_row, len(parent_node.children))

        new_parent_index = self._index_for_node(parent_node)
        self.beginInsertRows(new_parent_index, insert_row, insert_row)
        parent_node.insert_child(insert_row, obj_node)
        self.endInsertRows()

        return True

    # ------------------------------------------------------------------
    # Публичные методы управления деревом
    # ------------------------------------------------------------------

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
        # убираем все объекты канваса из кэша
        for obj_node in list(self._obj_nodes.values()):
            if self._canvas_for_node(obj_node) is None:
                del self._obj_nodes[obj_node.data.id]

    def add_object(self, canvas_id: str, obj: BaseObject) -> QModelIndex:
        canvas_node = self._canvas_nodes.get(canvas_id)
        if canvas_node is None:
            return QModelIndex()

        # определяем родительский узел
        if obj.parent_id and obj.parent_id in self._obj_nodes:
            parent_node = self._obj_nodes[obj.parent_id]
        else:
            parent_node = canvas_node

        parent_index = self._index_for_node(parent_node)
        row = len(parent_node.children)
        self.beginInsertRows(parent_index, row, row)
        new_node = TreeNode(obj)
        parent_node.append_child(new_node)
        self._obj_nodes[obj.id] = new_node
        self.endInsertRows()
        return self.createIndex(new_node.row_in_parent, 0, new_node)

    def remove_object(self, canvas_id: str, obj: BaseObject) -> None:
        node = self._obj_nodes.pop(obj.id, None)
        if node is None:
            return
        parent_node = node.parent
        parent_index = self._index_for_node(parent_node)
        row = node.row_in_parent
        self.beginRemoveRows(parent_index, row, row)
        parent_node.remove_child(node)
        self.endRemoveRows()

    def move_object(self, canvas_id: str, obj: BaseObject,
                    new_parent_id: str | None) -> None:
        """Пересчитывает координаты и перемещает узел в дереве."""
        node = self._obj_nodes.get(obj.id)
        if node is None:
            return

        self._recalc_coords(obj, new_parent_id)

        canvas_node = self._canvas_nodes.get(canvas_id)
        if canvas_node is None:
            return

        if new_parent_id and new_parent_id in self._obj_nodes:
            new_parent_node = self._obj_nodes[new_parent_id]
        else:
            new_parent_node = canvas_node

        if node.parent is new_parent_node:
            return  # уже там

        # удаляем со старого места
        old_parent = node.parent
        old_row = node.row_in_parent
        self.beginRemoveRows(self._index_for_node(old_parent), old_row, old_row)
        old_parent.remove_child(node)
        self.endRemoveRows()

        # вставляем в новое место
        new_parent_index = self._index_for_node(new_parent_node)
        insert_row = len(new_parent_node.children)
        self.beginInsertRows(new_parent_index, insert_row, insert_row)
        new_parent_node.append_child(node)
        self.endInsertRows()

    def update_canvas_name(self, canvas: Canvas) -> None:
        node = self._canvas_nodes.get(canvas.id)
        if node:
            idx = self.createIndex(node.row_in_parent, 0, node)
            self.dataChanged.emit(idx, idx,
                                  [Qt.ItemDataRole.DisplayRole])

    def update_object(self, canvas_id: str, obj: BaseObject) -> None:
        node = self._obj_nodes.get(obj.id)
        if node:
            node.data = obj
            idx = self.createIndex(node.row_in_parent, 0, node)
            self.dataChanged.emit(idx, idx,
                                  [Qt.ItemDataRole.DisplayRole,
                                   Qt.ItemDataRole.DecorationRole])

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def node_for_index(self, index: QModelIndex) -> TreeNode | None:
        if not index.isValid():
            return None
        return index.internalPointer()  # type: ignore[return-value]

    def _node(self, index: QModelIndex) -> TreeNode:
        if not index.isValid():
            return self._root
        return index.internalPointer()  # type: ignore[return-value]

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
        canvas_node = self._canvas_for_node(node)
        if canvas_node and canvas_node.is_canvas:
            return canvas_node.data.id
        return None

    def get_canvas_id_for_obj(self, obj: BaseObject) -> str | None:
        node = self._obj_nodes.get(obj.id)
        if node:
            return self._canvas_id_for_node(node)
        return None

    def _is_descendant(self, potential_child: TreeNode,
                        potential_parent: TreeNode) -> bool:
        cur = potential_child.parent
        while cur is not None and cur is not self._root:
            if cur is potential_parent:
                return True
            cur = cur.parent
        return False

    def _recalc_coords(self, obj: BaseObject, new_parent_id: str | None) -> None:
        """Пересчитывает координаты при смене родителя."""
        old_parent_node = None
        if obj.parent_id and obj.parent_id in self._obj_nodes:
            old_parent_node = self._obj_nodes[obj.parent_id]

        if old_parent_node:
            gp = old_parent_node.data.get_global_position()
            gx = gp[0] + obj.x
            gy = gp[1] + obj.y
        else:
            gx, gy = obj.x, obj.y

        new_parent_obj = None
        if new_parent_id and new_parent_id in self._obj_nodes:
            new_parent_obj = self._obj_nodes[new_parent_id].data

        obj.parent_id = new_parent_id
        obj._parent = new_parent_obj

        if new_parent_obj:
            np_ = new_parent_obj.get_global_position()
            obj.x = gx - np_[0]
            obj.y = gy - np_[1]
        else:
            obj.x = gx
            obj.y = gy

    def all_obj_nodes_for_canvas(self, canvas_id: str) -> dict[str, TreeNode]:
        """Возвращает все объектные узлы, принадлежащие данному канвасу."""
        result = {}
        canvas_node = self._canvas_nodes.get(canvas_id)
        if canvas_node is None:
            return result
        self._collect_obj_nodes(canvas_node, result)
        return result

    def _collect_obj_nodes(self, node: TreeNode,
                            out: dict[str, TreeNode]) -> None:
        for child in node.children:
            if child.is_object:
                out[child.data.id] = child
                self._collect_obj_nodes(child, out)


# ---------------------------------------------------------------------------
# Делегат — рисует кастомный индикатор вставки
# ---------------------------------------------------------------------------

class _DropLineDelegate(QStyledItemDelegate):
    """Делегат, подсвечивающий строку-цель при drag-over."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drop_row: int = -1
        self._drop_parent: QModelIndex = QModelIndex()
        self._drop_on_item: bool = False  # True = drop на элемент, False = между

    def set_drop_target(self, row: int, parent: QModelIndex,
                        on_item: bool) -> None:
        self._drop_row = row
        self._drop_parent = QPersistentModelIndex(parent)
        self._drop_on_item = on_item

    def clear_drop_target(self) -> None:
        self._drop_row = -1
        self._drop_parent = QModelIndex()
        self._drop_on_item = False

    def paint(self, painter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        super().paint(painter, option, index)

        view: CustomTreeView = self.parent()  # type: ignore[assignment]
        model = view.model()

        # подсветка элемента при drop-on
        if self._drop_on_item and self._drop_parent.isValid():
            target_index = QModelIndex(self._drop_parent)
            if index == target_index:
                from PySide6.QtGui import QPainter
                painter.save()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 120, 215, 40))
                painter.drawRect(option.rect)
                painter.restore()
            return

        # линия между строками
        if self._drop_row < 0:
            return

        parent_index = QModelIndex(self._drop_parent) \
            if self._drop_parent.isValid() else QModelIndex()

        # строим index строки, перед которой будем вставлять
        if self._drop_row < model.rowCount(parent_index):
            target_idx = model.index(self._drop_row, 0, parent_index)
        else:
            # вставка после последнего — рисуем под последним
            r = model.rowCount(parent_index) - 1
            if r < 0:
                return
            target_idx = model.index(r, 0, parent_index)

        if index != target_idx:
            return

        from PySide6.QtGui import QPen
        painter.save()
        pen = QPen(QColor(0, 120, 215), 2)
        painter.setPen(pen)

        rect = option.rect
        if self._drop_row < model.rowCount(parent_index):
            y = rect.top()
        else:
            y = rect.bottom()

        # отступ по уровню вложенности
        indent = view.indentation() * self._nesting_level(target_idx)
        painter.drawLine(indent + 4, y, rect.right() - 4, y)

        # маленькие «кружочки» на концах линии
        r = 4
        painter.setBrush(QColor(0, 120, 215))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(indent + 4 - r // 2, y - r // 2, r, r)
        painter.drawEllipse(rect.right() - 4 - r // 2, y - r // 2, r, r)

        painter.restore()

    def _nesting_level(self, index: QModelIndex) -> int:
        level = 0
        p = index.parent()
        while p.isValid():
            level += 1
            p = p.parent()
        return level


# ---------------------------------------------------------------------------
# Кастомный QTreeView
# ---------------------------------------------------------------------------

class CustomTreeView(QTreeView):
    """QTreeView с drag-and-drop и контекстным меню для сцены."""

    canvas_selected = Signal(str)
    object_selected = Signal(BaseObject)
    object_parent_changed = Signal(BaseObject)
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
        # Используем DragDrop вместо InternalMove — управляем сами через модель
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(False)  # отключаем стандартный, рисуем свой
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Кастомный делегат для отрисовки индикатора
        self._delegate = _DropLineDelegate(self)
        self.setItemDelegate(self._delegate)

        self.customContextMenuRequested.connect(self._show_context_menu)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.doubleClicked.connect(self._on_double_clicked)

        self._model.rowsInserted.connect(self._on_rows_inserted)
        self._model.rowsInserted.connect(self._after_drop)

    # ------------------------------------------------------------------
    # Drag & Drop события
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-scene-obj-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not event.mimeData().hasFormat("application/x-scene-obj-id"):
            event.ignore()
            return

        pos = event.position().toPoint()
        index = self.indexAt(pos)
        rect = self.visualRect(index) if index.isValid() else None

        # Определяем: вставка между элементами или drop на элемент
        drop_row = -1
        drop_parent = QModelIndex()
        on_item = False

        if index.isValid():
            node: TreeNode = self._model.node_for_index(index)

            if node and node.is_object:
                # Зона «горячая»: 30% сверху — вставить перед, 30% снизу — вставить после,
                # 40% по центру — drop в дочерние
                h = rect.height()
                rel_y = pos.y() - rect.top()
                zone = h * 0.28

                if rel_y < zone:
                    # вставить перед этим элементом
                    drop_parent = self._model.parent(index)
                    drop_row = index.row()
                elif rel_y > h - zone:
                    # вставить после этого элемента
                    drop_parent = self._model.parent(index)
                    drop_row = index.row() + 1
                else:
                    # drop прямо на элемент (сделать дочерним)
                    drop_parent = index
                    drop_row = -1
                    on_item = True

            elif node and node.is_canvas:
                # drop на канвас — вставить в конец его children как объект
                drop_parent = index
                drop_row = self._model.rowCount(index)

        can = self._model.canDropMimeData(
            event.mimeData(), Qt.DropAction.MoveAction,
            drop_row, 0, drop_parent)

        if can:
            event.acceptProposedAction()
            self._delegate.set_drop_target(drop_row, drop_parent, on_item)
        else:
            event.ignore()
            self._delegate.clear_drop_target()

        self.viewport().update()

    def dragLeaveEvent(self, event) -> None:
        self._delegate.clear_drop_target()
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat("application/x-scene-obj-id"):
            event.ignore()
            return

        drop_row = self._delegate._drop_row
        drop_parent_persistent = self._delegate._drop_parent
        on_item = self._delegate._drop_on_item

        drop_parent = QModelIndex(drop_parent_persistent) \
            if drop_parent_persistent.isValid() else QModelIndex()

        self._delegate.clear_drop_target()
        self.viewport().update()

        if on_item:
            row_arg = -1
        else:
            row_arg = drop_row

        ok = self._model.dropMimeData(
            event.mimeData(), Qt.DropAction.MoveAction,
            row_arg, 0, drop_parent)

        if ok:
            event.acceptProposedAction()
            # испускаем сигнал об изменении родителя
            obj_id = event.mimeData().data(
                "application/x-scene-obj-id").toStdString()
            node = self._model._obj_nodes.get(obj_id)
            if node:
                self.object_parent_changed.emit(node.data)
        else:
            event.ignore()

    # ------------------------------------------------------------------
    # Свойства совместимости (для кода, обращающегося к внутренним полям)
    # ------------------------------------------------------------------

    @property
    def _canvas_items(self) -> dict[str, QModelIndex]:
        """Совместимость: возвращает {canvas_id: QModelIndex}."""
        return {
            cid: self._model._index_for_node(node)
            for cid, node in self._model._canvas_nodes.items()
        }

    @property
    def _object_items(self) -> dict[str, dict[str, QModelIndex]]:
        """Совместимость: возвращает {canvas_id: {obj_id: QModelIndex}}."""
        result: dict[str, dict[str, QModelIndex]] = {}
        for canvas_id, canvas_node in self._model._canvas_nodes.items():
            obj_map: dict[str, QModelIndex] = {}
            nodes = self._model.all_obj_nodes_for_canvas(canvas_id)
            for obj_id, node in nodes.items():
                obj_map[obj_id] = self._model._index_for_node(node)
            result[canvas_id] = obj_map
        return result

    @property
    def _obj_to_item(self) -> dict[str, QModelIndex]:
        """Совместимость: возвращает {obj_id: QModelIndex}."""
        return {
            obj_id: self._model._index_for_node(node)
            for obj_id, node in self._model._obj_nodes.items()
        }

    def setCurrentItem(self, item: QModelIndex) -> None:
        """Совместимость с QTreeWidget.setCurrentItem — принимает QModelIndex."""
        if item is not None and item.isValid():
            self.setCurrentIndex(item)

    # ------------------------------------------------------------------
    # Публичные методы (аналоги CustomTreeWidget)
    # ------------------------------------------------------------------

    def add_canvas(self, canvas: Canvas) -> None:
        self._model.add_canvas(canvas)
        node = self._model._canvas_nodes.get(canvas.id)
        if node:
            idx = self._model._index_for_node(node)
            self.expand(idx)

    def remove_canvas(self, canvas_id: str) -> None:
        self._model.remove_canvas(canvas_id)

    def add_object(self, canvas_id: str, obj: BaseObject) -> None:
        idx = self._model.add_object(canvas_id, obj)
        if idx.isValid():
            self.expand(idx)
            parent_idx = self._model.parent(idx)
            if parent_idx.isValid():
                self.expand(parent_idx)

    def remove_object(self, canvas_id: str, obj: BaseObject) -> None:
        self._model.remove_object(canvas_id, obj)

    def move_object(self, canvas_id: str, obj: BaseObject,
                    new_parent_id: str | None) -> None:
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
        idx = self.currentIndex()
        if not idx.isValid():
            return None
        node = self._model.node_for_index(idx)
        if node is None:
            return None
        if node.is_canvas:
            return node.data
        canvas_node = self._model._canvas_for_node(node)
        if canvas_node:
            return canvas_node.data
        return None

    def get_selected_object(self) -> BaseObject | None:
        idx = self.currentIndex()
        if not idx.isValid():
            return None
        node = self._model.node_for_index(idx)
        if node and node.is_object:
            return node.data
        return None

    # ------------------------------------------------------------------
    # Внутренние обработчики
    # ------------------------------------------------------------------

    def _on_rows_inserted(self, parent: QModelIndex, first: int, last: int) -> None:
        self.expand(parent)

    def _after_drop(self, *_) -> None:
        """После вставки строки — раскрываем родителя."""
        self._delegate.clear_drop_target()

    def _on_selection_changed(self, *_) -> None:
        canvas = self.get_selected_canvas()
        if canvas:
            self.canvas_selected.emit(canvas.id)
        obj = self.get_selected_object()
        if obj:
            self.object_selected.emit(obj)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        node = self._model.node_for_index(index)
        if node and node.is_object:
            self.object_selected.emit(node.data)

    def _show_context_menu(self, position) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return
        node = self._model.node_for_index(index)
        if node is None:
            return
        global_pos = self.viewport().mapToGlobal(position)

        if node.is_object:
            obj = node.data
            menu = QMenu(self)

            add_child_menu = menu.addMenu("Добавить в объект")
            shapes_submenu = add_child_menu.addMenu("Фигуры")

            for label, kind in (("Прямоугольник", "rect"),
                                 ("Эллипс", "ellipse"),
                                 ("Треугольник", "triangle")):
                act = shapes_submenu.addAction(label)
                act.triggered.connect(
                    lambda _checked, k=kind: self._on_add_child(obj, k))

            text_act = add_child_menu.addAction("Текст")
            text_act.triggered.connect(lambda: self._on_add_child(obj, "text"))

            set_parent_menu = menu.addMenu("Сделать родителем")
            no_parent_act = set_parent_menu.addAction("Без родителя")
            no_parent_act.triggered.connect(
                lambda: self._on_set_parent(obj, None))

            canvas_id = self.get_canvas_id_for_object(obj)
            if canvas_id:
                for other_id, other_node in \
                        self._model.all_obj_nodes_for_canvas(canvas_id).items():
                    if other_id != obj.id and other_id != obj.parent_id:
                        other_obj = other_node.data
                        act = set_parent_menu.addAction(other_obj.name)
                        act.triggered.connect(
                            lambda _c, p=other_obj: self._on_set_parent(obj, p))

            menu.exec(global_pos)

        elif node.is_canvas:
            menu = QMenu(self)
            add_obj_act = QAction("Добавить объект", self)
            add_obj_act.triggered.connect(
                lambda: self.canvas_context_menu.emit(node.data))
            menu.addAction(add_obj_act)
            menu.exec(global_pos)

    def _on_add_child(self, parent_obj: BaseObject, obj_type: str) -> None:
        self.add_child_requested.emit(parent_obj, obj_type)

    def _on_set_parent(self, obj: BaseObject,
                       parent: BaseObject | None) -> None:
        canvas_id = self.get_canvas_id_for_object(obj)
        if canvas_id:
            parent_id = parent.id if parent else None
            self.move_object(canvas_id, obj, parent_id)
            self.object_parent_changed.emit(obj)


# ---------------------------------------------------------------------------
# Панель элементов
# ---------------------------------------------------------------------------

class ElementsPanel(QWidget):
    """Панель элементов управления."""

    canvas_selected = Signal(str)
    object_selected = Signal(BaseObject)
    object_parent_changed = Signal(BaseObject)
    add_child_requested = Signal(object, str)
    canvas_context_menu = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = CustomTreeView(self)
        layout.addWidget(self.tree)

        self.tree.canvas_selected.connect(self.canvas_selected.emit)
        self.tree.object_selected.connect(self.object_selected.emit)
        self.tree.canvas_context_menu.connect(self.canvas_context_menu.emit)
        self.tree.object_parent_changed.connect(self.object_parent_changed.emit)
        self.tree.add_child_requested.connect(self.add_child_requested.emit)

    # ------------------------------------------------------------------
    # Публичный API (идентичен оригиналу)
    # ------------------------------------------------------------------

    def add_canvas(self, canvas: Canvas) -> None:
        self.tree.add_canvas(canvas)

    def remove_canvas(self, canvas_id: str) -> None:
        self.tree.remove_canvas(canvas_id)

    def add_object(self, canvas_id: str, obj: BaseObject) -> None:
        self.tree.add_object(canvas_id, obj)

    def remove_object(self, canvas_id: str, obj: BaseObject) -> None:
        self.tree.remove_object(canvas_id, obj)

    def move_object(self, canvas_id: str, obj: BaseObject,
                    parent_id: str | None) -> None:
        self.tree.move_object(canvas_id, obj, parent_id)

    def update_object_name(self, canvas_id: str, obj: BaseObject) -> None:
        self.tree.update_object_name(canvas_id, obj)

    def update_object_lock(self, canvas_id: str, obj: BaseObject) -> None:
        self.tree.update_object_lock(canvas_id, obj)

    def update_canvas_name(self, canvas: Canvas) -> None:
        self.tree.update_canvas_name(canvas)