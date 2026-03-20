"""
ElementTreePanel — дерево канвасов и объектов.

Ключевые решения:
  1. Переопределяем dropEvent чтобы различать:
       - Drop ON item  → reparent (сделать дочерним)
       - Drop ABOVE/BELOW → reorder на том же уровне

  2. После drop → читаем структуру виджета → пишем в модель → recalc_z_indices
     Эмитим только document_changed (не structure_changed) → дерево не перестраивается

  3. full_rebuild() вызывается только при document_structure_changed
     (add/delete/undo/redo)

  4. При обычных изменениях (move/color) → только _update_labels()
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QAbstractItemView, QSizePolicy, QFrame,
)

from domain.models import ObjectType, ObjectState, CanvasState

if TYPE_CHECKING:
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController


ROLE_KIND      = Qt.UserRole        # "canvas" | "object"
ROLE_ID        = Qt.UserRole + 1    # obj_id or canvas_id
ROLE_CANVAS_ID = Qt.UserRole + 2    # canvas_id (for objects)

TYPE_ICONS = {
    ObjectType.RECT:    "▭",
    ObjectType.ELLIPSE: "◯",
    ObjectType.TEXT:    "T",
    ObjectType.IMAGE:   "🖼",
    ObjectType.GROUP:   "📁",
}
TYPE_COLORS = {
    ObjectType.RECT:    "#4A90E2",
    ObjectType.ELLIPSE: "#E2604A",
    ObjectType.TEXT:    "#4AE27A",
    ObjectType.IMAGE:   "#E2A84A",
    ObjectType.GROUP:   "#A84AE2",
}


# ---------------------------------------------------------------------------
# LayerTree — QTreeWidget с кастомным dropEvent
# ---------------------------------------------------------------------------

class LayerTree(QTreeWidget):
    """
    QTreeWidget который умеет:
      - Drop ON item  → вложить (reparent)
      - Drop ABOVE/BELOW → переставить на том же уровне
    """

    def __init__(self, panel: "ElementTreePanel"):
        super().__init__()
        self._panel = panel
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # DragDrop вместо InternalMove — чтобы можно было drop ON item
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setIndentation(18)
        self.setAnimated(True)
        self.setStyleSheet("""
            QTreeWidget {
                background: #1E1E2E; color: #CCCCDD;
                border: none; font-size: 12px; outline: none;
            }
            QTreeWidget::item {
                height: 26px; padding-left: 2px; border-radius: 3px;
            }
            QTreeWidget::item:selected { background: #3A4A6A; color: #FFFFFF; }
            QTreeWidget::item:hover:!selected { background: #2A2A3E; }
            QTreeWidget::branch { background: #1E1E2E; }
        """)

    def dropEvent(self, event):
        """
        Полностью управляем drop сами — Qt не умеет вкладывать items.

        Логика:
          OnItem   → вложить dragged как последнего ребёнка target
          Above    → вставить dragged перед target (тот же родитель)
          Below    → вставить dragged после target (тот же родитель)
          OnViewport/canvas → переместить в root активного canvas
        """
        target_item = self.itemAt(event.position().toPoint())
        indicator   = self.dropIndicatorPosition()

        # Собираем только object-items
        dragged_items = [i for i in self.selectedItems()
                         if i.data(0, ROLE_KIND) == "object"]
        if not dragged_items:
            event.ignore()
            return

        # Для каждого перетаскиваемого item выполняем операцию
        for drag_item in dragged_items:
            self._do_move(drag_item, target_item, indicator)

        event.accept()
        self.expandAll()

        # Синхронизируем модель из обновлённого виджета
        self._panel._sync_widget_to_model()

    def _do_move(self, drag_item: "QTreeWidgetItem",
                 target_item: "QTreeWidgetItem | None",
                 indicator: "QAbstractItemView.DropIndicatorPosition"):
        """Перемещает drag_item в виджете согласно indicator."""

        # Нельзя вложить в самого себя или в своих потомков
        if target_item is not None and self._is_ancestor(drag_item, target_item):
            return
        if target_item is drag_item:
            return

        # Отсоединяем drag_item от текущего родителя
        old_parent = drag_item.parent()
        if old_parent is None:
            idx = self.indexOfTopLevelItem(drag_item)
            self.takeTopLevelItem(idx)
        else:
            idx = old_parent.indexOfChild(drag_item)
            old_parent.takeChild(idx)

        # Вставляем в новое место
        if target_item is None:
            # Drop на пустое место → root первого canvas
            ci = self.topLevelItem(0)
            if ci:
                ci.addChild(drag_item)
            else:
                self.addTopLevelItem(drag_item)
            return

        target_kind = target_item.data(0, ROLE_KIND)

        if indicator == QAbstractItemView.OnItem:
            if target_kind == "canvas":
                # Drop на canvas → root этого canvas (в начало)
                target_item.insertChild(0, drag_item)
            else:
                # Drop на объект → стать его последним ребёнком
                target_item.addChild(drag_item)

        elif indicator in (QAbstractItemView.AboveItem,
                           QAbstractItemView.BelowItem):
            # Вставить рядом с target (тот же родитель)
            target_parent = target_item.parent()
            target_idx = (target_parent.indexOfChild(target_item)
                          if target_parent else
                          self.indexOfTopLevelItem(target_item))

            insert_idx = (target_idx
                          if indicator == QAbstractItemView.AboveItem
                          else target_idx + 1)

            if target_parent is None:
                # target — top-level (canvas or root object)
                # drag_item должен стать top-level рядом — но только
                # если target_kind == "object" (не canvas)
                if target_kind == "canvas":
                    # Нельзя вставить объект между канвасами → root этого canvas
                    target_item.insertChild(0, drag_item)
                else:
                    # target — root object; найдём его canvas
                    canvas_item = self._find_canvas_item_for(target_item)
                    if canvas_item:
                        ci_idx = canvas_item.indexOfChild(target_item)
                        ins = (ci_idx if indicator == QAbstractItemView.AboveItem
                               else ci_idx + 1)
                        canvas_item.insertChild(ins, drag_item)
                    else:
                        self.insertTopLevelItem(insert_idx, drag_item)
            else:
                target_parent.insertChild(insert_idx, drag_item)

        else:
            # OnViewport → root первого canvas
            ci = self.topLevelItem(0)
            if ci:
                ci.addChild(drag_item)

    def _is_ancestor(self, ancestor: "QTreeWidgetItem",
                     item: "QTreeWidgetItem") -> bool:
        """Проверяет является ли ancestor предком item."""
        p = item.parent()
        while p:
            if p is ancestor:
                return True
            p = p.parent()
        return False

    def _find_canvas_item_for(self,
                               item: "QTreeWidgetItem") -> "QTreeWidgetItem | None":
        """Находит canvas-item которому принадлежит item."""
        p = item.parent()
        while p:
            if p.data(0, ROLE_KIND) == "canvas":
                return p
            p = p.parent()
        return None

    def dragEnterEvent(self, event):
        if event.source() is self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() is self:
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# ElementTreePanel
# ---------------------------------------------------------------------------

class ElementTreePanel(QWidget):
    def __init__(self, store: "EditorStore", controller: "EditorController"):
        super().__init__()
        self._store      = store
        self._controller = controller
        self._updating_selection = False

        self._setup_ui()
        self._connect_signals()
        self.full_rebuild()

    def _setup_ui(self):
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            "background:#252535;border-bottom:1px solid #3A3A4A;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 6, 8, 6)
        lbl = QLabel("Layers")
        lbl.setStyleSheet("color:#CCCCDD;font-weight:bold;font-size:12px;")
        hl.addWidget(lbl)
        hl.addStretch()
        layout.addWidget(header)

        self._tree = LayerTree(self)
        layout.addWidget(self._tree)

    def _connect_signals(self):
        # Структурные → rebuild
        self._store.document_structure_changed.connect(self.full_rebuild)
        # Несструктурные → только тексты
        self._store.document_changed.connect(self._update_labels)
        self._store.selection_changed.connect(self._on_selection_changed)
        self._store.canvas_switched.connect(lambda _: self.full_rebuild())
        self._tree.itemSelectionChanged.connect(self._on_tree_selection)

    # -----------------------------------------------------------------------
    # Full rebuild
    # -----------------------------------------------------------------------

    def full_rebuild(self):
        self._tree.blockSignals(True)
        self._tree.clear()
        doc = self._store.document

        for canvas_id, canvas in doc.canvases.items():
            ci = self._make_canvas_item(canvas)
            self._tree.addTopLevelItem(ci)
            # reversed: root_ids[0]=нижний → идёт последним в виджете
            for obj_id in reversed(canvas.root_ids):
                obj = canvas.objects.get(obj_id)
                if obj:
                    ci.addChild(self._make_object_item(canvas, obj))
            ci.setExpanded(True)

        self._tree.blockSignals(False)
        self._highlight_selection()

    def _make_canvas_item(self, canvas: CanvasState) -> QTreeWidgetItem:
        active = canvas.id == self._store.document.active_canvas_id
        item = QTreeWidgetItem([f"{'▶' if active else '🎨'}  {canvas.name}"])
        item.setData(0, ROLE_KIND,      "canvas")
        item.setData(0, ROLE_ID,        canvas.id)
        item.setData(0, ROLE_CANVAS_ID, canvas.id)
        item.setForeground(0, QColor("#FFFFFF" if active else "#AAAACC"))
        f = QFont(); f.setBold(active); f.setPointSize(11)
        item.setFont(0, f)
        # Canvas нельзя перетаскивать, но можно дропать на него
        item.setFlags((item.flags() & ~Qt.ItemIsDragEnabled)
                      | Qt.ItemIsDropEnabled)
        return item

    def _make_object_item(self, canvas: CanvasState,
                           obj: ObjectState) -> QTreeWidgetItem:
        item = QTreeWidgetItem([self._obj_label(obj)])
        item.setData(0, ROLE_KIND,      "object")
        item.setData(0, ROLE_ID,        obj.id)
        item.setData(0, ROLE_CANVAS_ID, canvas.id)
        item.setForeground(0, QColor(
            "#555566" if obj.locked
            else TYPE_COLORS.get(obj.type, "#CCCCCC")))
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
        # Дети (reversed: children_ids[0]=нижний → последним в виджете)
        for child_id in reversed(obj.children_ids):
            child = canvas.objects.get(child_id)
            if child:
                item.addChild(self._make_object_item(canvas, child))
        item.setExpanded(True)
        return item

    @staticmethod
    def _obj_label(obj: ObjectState) -> str:
        label = f"{TYPE_ICONS.get(obj.type, '?')}  {obj.name}"
        if not obj.visible: label += "  👁‍🗨"
        if obj.locked:      label += "  🔒"
        return label

    # -----------------------------------------------------------------------
    # Update labels only
    # -----------------------------------------------------------------------

    def _update_labels(self):
        doc = self._store.document
        self._tree.blockSignals(True)

        def walk(item: QTreeWidgetItem):
            kind = item.data(0, ROLE_KIND)
            if kind == "object":
                canvas = doc.canvases.get(item.data(0, ROLE_CANVAS_ID))
                obj = canvas.objects.get(item.data(0, ROLE_ID)) if canvas else None
                if obj:
                    item.setText(0, self._obj_label(obj))
                    item.setForeground(0, QColor(
                        "#555566" if obj.locked
                        else TYPE_COLORS.get(obj.type, "#CCCCCC")))
            elif kind == "canvas":
                canvas = doc.canvases.get(item.data(0, ROLE_ID))
                if canvas:
                    active = canvas.id == doc.active_canvas_id
                    item.setText(0, f"{'▶' if active else '🎨'}  {canvas.name}")
                    item.setForeground(0, QColor("#FFFFFF" if active else "#AAAACC"))
                    f = QFont(); f.setBold(active); f.setPointSize(11)
                    item.setFont(0, f)
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))
        self._tree.blockSignals(False)

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def _on_tree_selection(self):
        if self._updating_selection:
            return
        selected_obj_ids = []
        active_canvas_id = None
        for item in self._tree.selectedItems():
            kind = item.data(0, ROLE_KIND)
            if kind == "canvas":
                active_canvas_id = item.data(0, ROLE_ID)
            elif kind == "object":
                selected_obj_ids.append(item.data(0, ROLE_ID))
                if active_canvas_id is None:
                    active_canvas_id = item.data(0, ROLE_CANVAS_ID)

        self._updating_selection = True
        if (active_canvas_id
                and active_canvas_id != self._store.document.active_canvas_id):
            self._controller.switch_canvas(active_canvas_id)
        self._controller.select(selected_obj_ids)
        self._updating_selection = False

    def _on_selection_changed(self, ids, active_id):
        if not self._updating_selection:
            self._highlight_selection()

    def _highlight_selection(self):
        self._updating_selection = True
        self._tree.blockSignals(True)
        sel = set(self._store.selection.selected_ids)

        def walk(item: QTreeWidgetItem):
            item.setSelected(
                item.data(0, ROLE_KIND) == "object"
                and item.data(0, ROLE_ID) in sel)
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self._tree.topLevelItemCount()):
            walk(self._tree.topLevelItem(i))

        self._tree.blockSignals(False)
        self._updating_selection = False

    # -----------------------------------------------------------------------
    # Sync widget → model (вызывается из LayerTree.dropEvent)
    # -----------------------------------------------------------------------

    def _sync_widget_to_model(self):
        """
        Читает текущую структуру виджета → обновляет DocumentState.
        Эмитит только document_changed (не structure_changed).
        """
        doc = self._store.document

        for ci in range(self._tree.topLevelItemCount()):
            canvas_item = self._tree.topLevelItem(ci)
            canvas_id   = canvas_item.data(0, ROLE_CANVAS_ID)
            canvas      = doc.canvases.get(canvas_id)
            if not canvas:
                continue

            # Сбрасываем старые связи
            canvas.root_ids = []
            for obj in canvas.objects.values():
                obj.parent_id    = None
                obj.children_ids = []

            # Читаем из виджета
            self._read_item_children(canvas_item, canvas, parent_obj_id=None)

            # Пересчитываем z_index
            canvas.recalc_z_indices()

        doc.dirty = True
        # Только doc_changed — дерево не перестраивается
        self._store.document_changed.emit()

    def _read_item_children(self, parent_item: QTreeWidgetItem,
                             canvas: CanvasState,
                             parent_obj_id: str | None):
        """
        Рекурсивно читает детей parent_item → пишет в модель.
        Первый item в виджете = верхний слой.
        root_ids/children_ids[0] = нижний → инвертируем.
        """
        collected: list[str] = []

        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            if child_item.data(0, ROLE_KIND) != "object":
                continue
            obj_id = child_item.data(0, ROLE_ID)
            obj    = canvas.objects.get(obj_id)
            if obj is None:
                continue
            obj.parent_id = parent_obj_id
            collected.append(obj_id)
            # Рекурсия
            self._read_item_children(child_item, canvas, obj_id)

        # Инвертируем: виджет[0]=верхний → list[-1]=верхний = конец списка
        inv = list(reversed(collected))
        if parent_obj_id is None:
            canvas.root_ids = inv
        else:
            p = canvas.objects.get(parent_obj_id)
            if p:
                p.children_ids = inv
