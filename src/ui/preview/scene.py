"""Сцена превью для одного канваса."""

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
        # Включаем обрезку дочерних элементов по границам этого элемента
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
    """Сцена превью для одного канваса."""

    object_selected = Signal(BaseObject)
    object_changed = Signal(BaseObject)
    object_moved = Signal(BaseObject)

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self._object_items: dict[BaseObject, QGraphicsRectItem] = {}
        self._items_by_id: dict[str, QGraphicsRectItem] = {}

        # Добавляем фон канваса
        self.canvas_item = CanvasRectItem(canvas)
        self.addItem(self.canvas_item)

        # Устанавливаем обрезку по границам сцены (канваса)
        self.setSceneRect(0, 0, canvas.width, canvas.height)
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Обработчик изменения выделения."""
        for item in self.selectedItems():
            if isinstance(item, (TextGraphicsItem, ImageGraphicsItem, ShapeGraphicsItem)):
                self.object_selected.emit(item.obj)
                break

    def add_object(self, obj: BaseObject):
        """Добавляет объект на сцену."""
        # Определяем тип объекта и создаём соответствующий элемент
        if isinstance(obj, TextObject):
            graphics_item = TextGraphicsItem(obj)
        elif isinstance(obj, ImageObject):
            graphics_item = ImageGraphicsItem(obj)
        elif isinstance(obj, ShapeObject):
            graphics_item = ShapeGraphicsItem(obj)
        else:
            # Для BaseObject используем ShapeGraphicsItem
            graphics_item = ShapeGraphicsItem(obj)

        # Устанавливаем родителя если есть
        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            graphics_item.setParentItem(parent_item)

        self.addItem(graphics_item)
        self._object_items[obj] = graphics_item
        self._items_by_id[obj.id] = graphics_item

    def remove_object(self, obj: BaseObject):
        """Удаляет объект со сцены."""
        if obj in self._object_items:
            item = self._object_items[obj]
            # Сначала удаляем дочерние элементы
            for child_item in item.childItems():
                self.removeItem(child_item)
                # Находим и удаляем соответствующий объект из словарей
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

    def rebuild_object_parent(self, obj: BaseObject):
        """Перестраивает родительскую связь для объекта."""
        if obj not in self._object_items:
            return

        item = self._object_items[obj]
        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            item.setParentItem(parent_item)
        else:
            item.setParentItem(None)
