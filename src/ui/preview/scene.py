"""Сцена превью для одного канваса с правильным порядком рендеринга."""

from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtCore import Qt, QRectF, Signal

from ...models import Canvas, BaseObject, TextObject, ImageObject, ShapeObject
from .items.text_item import TextGraphicsItem
from .items.image_item import ImageGraphicsItem
from .items.shape_item import ShapeGraphicsItem


class CanvasRectItem(QGraphicsRectItem):
    """Визуальное представление канваса с обрезкой дочерних элементов."""

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(0, 0, canvas.width, canvas.height, parent)
        self.canvas = canvas
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemClipsChildrenToShape)
        self.update_appearance()

    def update_appearance(self):
        """Обновляет внешний вид канваса."""
        color = QColor(self.canvas.background_color)
        self.setBrush(QBrush(color))
        pen = QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashLine)
        self.setPen(pen)

    def update_size(self):
        """Обновляет размер канваса."""
        self.setRect(QRectF(0, 0, self.canvas.width, self.canvas.height))


class PreviewScene(QGraphicsScene):
    """Сцена превью для одного канваса.

    Порядок рендеринга (согласно test.txt):
    - Дочерние элементы рендерятся перед родительскими
    - Последние элементы в дереве рендерятся первыми (нижний слой)
    
    Пример:
    ROOT
    ├─ нода 1
    │  └─ нода 2
    └─ нода 3
       ├─ нода 4
       └─ нода 5
    
    Порядок рендеринга: 5 → 4 → 3 → 2 → 1
    (нода 5 - нижний слой, нода 1 - верхний слой)
    """

    object_selected = Signal(BaseObject)
    object_changed = Signal(BaseObject)
    object_moved = Signal(BaseObject)

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self._object_items: dict[BaseObject, QGraphicsRectItem] = {}
        self._items_by_id: dict[str, QGraphicsRectItem] = {}
        self._z_counter = 0

        # Добавляем фон канваса
        self.canvas_item = CanvasRectItem(canvas)
        self.addItem(self.canvas_item)

        self.setSceneRect(0, 0, canvas.width, canvas.height)
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Обработчик изменения выделения."""
        for item in self.selectedItems():
            if isinstance(item, (TextGraphicsItem, ImageGraphicsItem, ShapeGraphicsItem)):
                self.object_selected.emit(item.obj)
                break

    def _get_next_z_value(self) -> float:
        """Получает следующее z-значение для правильного порядка слоёв."""
        self._z_counter += 1
        return float(self._z_counter)

    def add_object(self, obj: BaseObject):
        """Добавляет объект на сцену."""
        if isinstance(obj, TextObject):
            graphics_item = TextGraphicsItem(obj)
        elif isinstance(obj, ImageObject):
            graphics_item = ImageGraphicsItem(obj)
        elif isinstance(obj, ShapeObject):
            graphics_item = ShapeGraphicsItem(obj)
        else:
            graphics_item = ShapeGraphicsItem(obj)

        # Устанавливаем родителя если есть
        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            graphics_item.setParentItem(parent_item)
            # Дочерний элемент должен иметь меньший z, чем родитель
            graphics_item.setZValue(parent_item.zValue() - 1)
        else:
            # Корневой объект получает следующее z-значение
            graphics_item.setZValue(self._get_next_z_value())

        self.addItem(graphics_item)
        self._object_items[obj] = graphics_item
        self._items_by_id[obj.id] = graphics_item

    def _update_children_positions(self, parent_obj: BaseObject):
        """Обновляет позиции дочерних элементов после перемещения родителя.

        При перемещении родителя дочерние элементы визуально следуют за ним,
        но их локальные координаты (obj.x, obj.y) остаются неизменными.
        """
        # Находим все объекты на сцене, у которых parent_id == parent_obj.id
        for obj, item in list(self._object_items.items()):
            if obj.parent_id == parent_obj.id:
                # Явно обновляем позицию элемента (локальные координаты не меняются)
                item.setPos(obj.x, obj.y)

    def remove_object(self, obj: BaseObject):
        """Удаляет объект со сцены."""
        if obj in self._object_items:
            item = self._object_items[obj]
            # Сначала удаляем дочерние элементы
            for child_item in list(item.childItems()):
                self.removeItem(child_item)
                for o, i in list(self._object_items.items()):
                    if i == child_item:
                        del self._object_items[o]
                        del self._items_by_id[o.id]
                        break

            self.removeItem(item)
            del self._object_items[obj]
            del self._items_by_id[obj.id]

    def update_object(self, obj: BaseObject):
        """Обновляет объект на сцене."""
        if obj in self._object_items:
            item = self._object_items[obj]
            if isinstance(item, TextGraphicsItem):
                item.update_font()
                item.update_colors()
            elif isinstance(item, ImageGraphicsItem):
                item.update_appearance()
            elif isinstance(item, ShapeGraphicsItem):
                item.update_appearance()

    def update_canvas(self, canvas: Canvas):
        """Обновляет канвас."""
        self.canvas = canvas
        self.canvas_item.update_appearance()
        self.canvas_item.update_size()
        self.setSceneRect(0, 0, canvas.width, canvas.height)

    def get_item_for_object(self, obj: BaseObject) -> QGraphicsRectItem | None:
        """Получает графический элемент для объекта."""
        return self._object_items.get(obj)

    def clear_selection(self):
        """Снимает выделение со всех объектов."""
        for item in self.selectedItems():
            item.setSelected(False)

    def select_object(self, obj: BaseObject) -> None:
        """Выделяет объект на сцене."""
        self.clearSelection()
        if obj in self._object_items:
            item = self._object_items[obj]
            item.setSelected(True)

    def rebuild_object_parent(self, obj: BaseObject):
        """Перестраивает родительскую связь для объекта и обновляет z-порядок.

        При смене родителя координаты obj.x/obj.y уже пересчитаны в контроллере.
        """
        if obj not in self._object_items:
            return

        item = self._object_items[obj]
        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            item.setParentItem(parent_item)
            # Устанавливаем позицию в локальных координатах родителя
            item.setPos(obj.x, obj.y)
            # Дочерний элемент должен иметь меньший z, чем родитель
            item.setZValue(parent_item.zValue() - 1)
        else:
            item.setParentItem(None)
            # Устанавливаем глобальную позицию
            item.setPos(obj.x, obj.y)

    def rebuild_z_order(self, objects_in_render_order: list[BaseObject]):
        """Перестраивает z-порядок всех объектов согласно порядку рендеринга.

        Args:
            objects_in_render_order: Список объектов в порядке рендеринга
                                     (первый = нижний слой, последний = верхний слой)
        """
        # Сбрасываем z-счётчик
        self._z_counter = 0

        # Назначаем z-значения в порядке рендеринга
        for z_value, obj in enumerate(objects_in_render_order):
            if obj in self._object_items:
                item = self._object_items[obj]
                item.setZValue(float(z_value))

    def get_objects_in_render_order(self) -> list[BaseObject]:
        """Получает объекты в порядке рендеринга (от нижнего к верхнему слою).

        Использует пост-порядок обхода дерева (дочерние перед родительскими,
        последние в списке детей первыми).
        """
        result = []

        def collect_objects_post_order(item: QGraphicsRectItem):
            """Собирает объекты в пост-порядке (дети перед родителями)."""
            # Сначала обрабатываем дочерние элементы (с конца к началу)
            for child_item in reversed(item.childItems()):
                if isinstance(child_item, (TextGraphicsItem, ImageGraphicsItem, ShapeGraphicsItem)):
                    collect_objects_post_order(child_item)
            # Затем добавляем сам объект
            for obj, obj_item in self._object_items.items():
                if obj_item == item:
                    result.append(obj)
                    break

        # Получаем все корневые элементы (без родителя QGraphicsRectItem)
        root_items = []
        for item in self._object_items.values():
            parent = item.parentItem()
            if parent is None or not isinstance(parent, QGraphicsRectItem):
                root_items.append(item)

        # Обрабатываем корневые элементы с конца к началу
        for root_item in reversed(root_items):
            collect_objects_post_order(root_item)

        return result
