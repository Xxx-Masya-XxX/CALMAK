"""Сцена превью для одного канваса.

Иерархия объектов:
  canvas_item (CanvasRectItem)
    └── корневые объекты (parent_id == None)
          └── дочерние объекты (parent_id задан)
                └── ...

Qt автоматически сдвигает дочерние элементы вместе с родителем,
потому что они привязаны через setParentItem.
Координаты obj.x / obj.y — ЛОКАЛЬНЫЕ (относительно родителя).
"""

from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import Signal

from ...models import Canvas, BaseObject, ShapeObject, TextObject
from ..objects.canvas_object import CanvasRectItem
from ..objects.shape_object import ShapeGraphicsItem
from ..objects.base_object import BaseGraphicsItem
from ..objects.text_object import TextGraphicsItem

class PreviewScene(QGraphicsScene):

    object_selected         = Signal(BaseObject)
    object_changed          = Signal(BaseObject)
    object_moved            = Signal(BaseObject)
    object_resized          = Signal(BaseObject)
    object_geometry_changed = Signal(BaseObject)

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas

        self._object_items: dict[BaseObject, BaseGraphicsItem] = {}
        self._items_by_id:  dict[str, BaseGraphicsItem] = {}
        self._z_counter = 0

        # Фон канваса — все объекты будут его дочерними элементами
        self.canvas_item = CanvasRectItem(canvas)
        self.addItem(self.canvas_item)

        self.setSceneRect(0, 0, canvas.width, canvas.height)
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        self.selectionChanged.connect(self._on_selection_changed)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        for item in self.selectedItems():
            if isinstance(item, BaseGraphicsItem):
                self.object_selected.emit(item.obj)
                return

    # ------------------------------------------------------------------
    # Добавление объекта
    # ------------------------------------------------------------------

    def add_object(self, obj: BaseObject):
        """Добавляет объект на сцену с правильной иерархией.

        Если у obj есть parent_id → setParentItem(parent_graphics_item)
        Иначе                     → setParentItem(canvas_item)

        После setParentItem Qt сам двигает дочерний элемент при движении родителя.
        setPos задаётся как ЛОКАЛЬНАЯ позиция (от родителя).
        """
        item = self._create_item(obj)

        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            item.setParentItem(parent_item)
            item.setZValue(parent_item.zValue() - 1)
        else:
            item.setParentItem(self.canvas_item)
            self._z_counter += 1
            item.setZValue(float(self._z_counter))

        # Локальная позиция внутри родителя
        item.setPos(obj.x, obj.y)

        self._object_items[obj] = item
        self._items_by_id[obj.id] = item

    def _create_item(self, obj: BaseObject) -> BaseGraphicsItem:
        if isinstance(obj, ShapeObject):
            return ShapeGraphicsItem(obj)
        if isinstance(obj, TextObject):
            return TextGraphicsItem(obj)
        return ShapeGraphicsItem(obj)

    # ------------------------------------------------------------------
    # Удаление объекта
    # ------------------------------------------------------------------

    def remove_object(self, obj: BaseObject):
        if obj not in self._object_items:
            return
        item = self._object_items[obj]
        # Рекурсивно удаляем дочерние
        for child in list(item.childItems()):
            if isinstance(child, BaseGraphicsItem):
                for o, i in list(self._object_items.items()):
                    if i is child:
                        self._remove_recursive(o, child)
                        break
        # Удаляем сам элемент
        item.setParentItem(None)
        self.removeItem(item)
        self._object_items.pop(obj, None)
        self._items_by_id.pop(obj.id, None)

    def _remove_recursive(self, obj: BaseObject, item: BaseGraphicsItem):
        for child in list(item.childItems()):
            if isinstance(child, BaseGraphicsItem):
                for o, i in list(self._object_items.items()):
                    if i is child:
                        self._remove_recursive(o, child)
                        break
        item.setParentItem(None)
        self.removeItem(item)
        self._object_items.pop(obj, None)
        self._items_by_id.pop(obj.id, None)

    # ------------------------------------------------------------------
    # Обновление
    # ------------------------------------------------------------------

    def update_object(self, obj: BaseObject):
        """Синхронизирует графику с моделью."""
        if obj in self._object_items:
            self._object_items[obj].sync_from_model()

    def update_canvas(self, canvas: Canvas):
        self.canvas = canvas
        self.canvas_item.update_appearance()
        self.canvas_item.update_size()
        self.setSceneRect(0, 0, canvas.width, canvas.height)

    def get_item_for_object(self, obj: BaseObject) -> BaseGraphicsItem | None:
        return self._object_items.get(obj)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def clear_selection(self):
        self.clearSelection()

    def select_object(self, obj: BaseObject):
        self.clearSelection()
        if obj in self._object_items:
            self._object_items[obj].setSelected(True)

    # ------------------------------------------------------------------
    # Перестройка иерархии (после drag & drop в дереве)
    # ------------------------------------------------------------------

    def rebuild_object_parent(self, obj: BaseObject):
        """Перестраивает parent-связь. Координаты уже пересчитаны в модели."""
        if obj not in self._object_items:
            return
        item = self._object_items[obj]

        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            item.setParentItem(parent_item)
            item.setZValue(parent_item.zValue() - 1)
        else:
            item.setParentItem(self.canvas_item)
            self._z_counter += 1
            item.setZValue(float(self._z_counter))

        item.setPos(obj.x, obj.y)

    def rebuild_z_order(self, objects_in_order: list[BaseObject]):
        self._z_counter = 0
        for z, obj in enumerate(objects_in_order):
            if obj in self._object_items:
                self._object_items[obj].setZValue(float(z))
