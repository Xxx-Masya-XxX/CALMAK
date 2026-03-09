"""Контроллер сцены для управления объектами и канвасами."""

from typing import Callable

from ..models import Canvas, BaseObject, TextObject, ImageObject, ShapeObject


class SceneController:
    """Контроллер для управления сценой, объектами и канвасами."""

    def __init__(self):
        self._canvases: dict[str, Canvas] = {}
        self._objects: dict[str, list[BaseObject]] = {}  # canvas_id -> objects
        self._active_canvas_id: str | None = None

        # Callbacks для уведомлений об изменениях
        self._on_canvas_added: Callable[[Canvas], None] | None = None
        self._on_canvas_removed: Callable[[str], None] | None = None
        self._on_canvas_changed: Callable[[Canvas], None] | None = None
        self._on_object_added: Callable[[str, BaseObject], None] | None = None
        self._on_object_removed: Callable[[str, BaseObject], None] | None = None
        self._on_object_changed: Callable[[str, BaseObject], None] | None = None
        self._on_active_canvas_changed: Callable[[str | None], None] | None = None

    # === Callbacks ===

    def set_canvas_added_callback(self, callback: Callable[[Canvas], None]):
        """Устанавливает callback при добавлении канваса."""
        self._on_canvas_added = callback

    def set_canvas_removed_callback(self, callback: Callable[[str], None]):
        """Устанавливает callback при удалении канваса."""
        self._on_canvas_removed = callback

    def set_canvas_changed_callback(self, callback: Callable[[Canvas], None]):
        """Устанавливает callback при изменении канваса."""
        self._on_canvas_changed = callback

    def set_object_added_callback(self, callback: Callable[[str, BaseObject], None]):
        """Устанавливает callback при добавлении объекта."""
        self._on_object_added = callback

    def set_object_removed_callback(self, callback: Callable[[str, BaseObject], None]):
        """Устанавливает callback при удалении объекта."""
        self._on_object_removed = callback

    def set_object_changed_callback(self, callback: Callable[[str, BaseObject], None]):
        """Устанавливает callback при изменении объекта."""
        self._on_object_changed = callback

    def set_active_canvas_changed_callback(self, callback: Callable[[str | None], None]):
        """Устанавливает callback при изменении активного канваса."""
        self._on_active_canvas_changed = callback

    def _notify_canvas_added(self, canvas: Canvas):
        if self._on_canvas_added:
            self._on_canvas_added(canvas)

    def _notify_canvas_removed(self, canvas_id: str):
        if self._on_canvas_removed:
            self._on_canvas_removed(canvas_id)

    def _notify_canvas_changed(self, canvas: Canvas):
        if self._on_canvas_changed:
            self._on_canvas_changed(canvas)

    def _notify_object_added(self, canvas_id: str, obj: BaseObject):
        if self._on_object_added:
            self._on_object_added(canvas_id, obj)

    def _notify_object_removed(self, canvas_id: str, obj: BaseObject):
        if self._on_object_removed:
            self._on_object_removed(canvas_id, obj)

    def _notify_object_changed(self, canvas_id: str, obj: BaseObject):
        if self._on_object_changed:
            self._on_object_changed(canvas_id, obj)

    def _notify_active_canvas_changed(self, canvas_id: str | None):
        if self._on_active_canvas_changed:
            self._on_active_canvas_changed(canvas_id)

    # === Canvas operations ===

    def add_canvas(self, canvas: Canvas) -> Canvas:
        """Добавляет новый канвас."""
        self._canvases[canvas.id] = canvas
        self._objects[canvas.id] = []
        if self._active_canvas_id is None:
            self._active_canvas_id = canvas.id
            self._notify_active_canvas_changed(canvas.id)
        self._notify_canvas_added(canvas)
        return canvas

    def remove_canvas(self, canvas_id: str):
        """Удаляет канвас."""
        if canvas_id in self._canvases:
            # Удаляем все объекты канваса
            objects = self._objects.get(canvas_id, [])
            for obj in objects:
                self._notify_object_removed(canvas_id, obj)

            del self._canvases[canvas_id]
            if canvas_id in self._objects:
                del self._objects[canvas_id]
            if self._active_canvas_id == canvas_id:
                self._active_canvas_id = next(iter(self._canvases.keys()), None)
                self._notify_active_canvas_changed(self._active_canvas_id)
            self._notify_canvas_removed(canvas_id)

    def get_canvas(self, canvas_id: str) -> Canvas | None:
        """Получает канвас по ID."""
        return self._canvases.get(canvas_id)

    def get_all_canvases(self) -> list[Canvas]:
        """Получает все канвасы."""
        return list(self._canvases.values())

    def set_active_canvas(self, canvas_id: str):
        """Устанавливает активный канвас."""
        if canvas_id in self._canvases:
            self._active_canvas_id = canvas_id
            self._notify_active_canvas_changed(canvas_id)

    def get_active_canvas(self) -> Canvas | None:
        """Получает активный канвас."""
        if self._active_canvas_id:
            return self._canvases.get(self._active_canvas_id)
        return None

    def get_active_canvas_id(self) -> str | None:
        """Получает ID активного канваса."""
        return self._active_canvas_id

    # === Object operations ===

    def add_object(self, canvas_id: str, obj: BaseObject) -> BaseObject:
        """Добавляет объект на канвас."""
        if canvas_id not in self._objects:
            self._objects[canvas_id] = []
        self._objects[canvas_id].append(obj)

        # Устанавливаем ссылку на родителя если есть
        if obj.parent_id:
            parent = self.get_parent(canvas_id, obj)
            if parent:
                obj._parent = parent

        self._notify_object_added(canvas_id, obj)
        return obj

    def remove_object(self, canvas_id: str, obj: BaseObject):
        """Удаляет объект с канваса (включая дочерние)."""
        if canvas_id in self._objects:
            # Сначала удаляем дочерние объекты
            children = self.get_children(canvas_id, obj.id)
            for child in children:
                self._objects[canvas_id] = [o for o in self._objects[canvas_id] if o != child]
                self._notify_object_removed(canvas_id, child)
            # Затем удаляем сам объект
            self._objects[canvas_id] = [o for o in self._objects[canvas_id] if o != obj]
            self._notify_object_removed(canvas_id, obj)

    def get_objects(self, canvas_id: str) -> list[BaseObject]:
        """Получает все объекты канваса."""
        return self._objects.get(canvas_id, [])

    def get_root_objects(self, canvas_id: str) -> list[BaseObject]:
        """Получает корневые объекты канваса (без родителя)."""
        objects = self.get_objects(canvas_id)
        return [obj for obj in objects if obj.parent_id is None]

    def get_children(self, canvas_id: str, parent_id: str) -> list[BaseObject]:
        """Получает дочерние объекты."""
        objects = self.get_objects(canvas_id)
        return [obj for obj in objects if obj.parent_id == parent_id]

    def get_parent(self, canvas_id: str, obj: BaseObject) -> BaseObject | None:
        """Получает родительский объект."""
        if obj.parent_id is None:
            return None
        objects = self.get_objects(canvas_id)
        for o in objects:
            if o.id == obj.parent_id:
                return o
        return None

    def set_parent(self, canvas_id: str, obj: BaseObject, parent: BaseObject | None):
        """Устанавливает родителя для объекта.

        Сохраняет глобальную позицию объекта, пересчитывая локальные координаты.
        """
        old_parent_id = obj.parent_id
        
        # Получаем глобальные координаты объекта ДО смены родителя
        if old_parent_id:
            old_parent = self.get_parent(canvas_id, obj)
            if old_parent:
                old_parent_global = old_parent.get_global_position()
                global_x = old_parent_global[0] + obj.x
                global_y = old_parent_global[1] + obj.y
            else:
                global_x, global_y = obj.x, obj.y
        else:
            global_x, global_y = obj.x, obj.y

        # Устанавливаем нового родителя
        if parent:
            obj.parent_id = parent.id
            obj._parent = parent
        else:
            obj.parent_id = None
            obj._parent = None

        # Пересчитываем локальные координаты относительно нового родителя
        if obj._parent:
            new_parent_global = obj._parent.get_global_position()
            obj.x = global_x - new_parent_global[0]
            obj.y = global_y - new_parent_global[1]
        else:
            obj.x = global_x
            obj.y = global_y

        self._notify_object_changed(canvas_id, obj)

    def _recalculate_coords(self, obj: BaseObject, old_parent_id: str | None):
        """Пересчитывает координаты при смене родителя.

        Сохраняет глобальную позицию объекта при смене родителя,
        пересчитывая локальные координаты.
        """
        # Получаем глобальные координаты до смены родителя
        if old_parent_id:
            objects = self._objects.get(old_parent_id, [])
            old_parent = next((o for o in objects if o.id == old_parent_id), None)
            if old_parent:
                old_parent_global = old_parent.get_global_position()
                global_x = old_parent_global[0] + obj.x
                global_y = old_parent_global[1] + obj.y
            else:
                global_x, global_y = obj.x, obj.y
        else:
            global_x, global_y = obj.x, obj.y

        # Устанавливаем новые локальные координаты относительно нового родителя
        if obj._parent:
            new_parent_global = obj._parent.get_global_position()
            obj.x = global_x - new_parent_global[0]
            obj.y = global_y - new_parent_global[1]
        else:
            obj.x = global_x
            obj.y = global_y

    def get_all_objects(self) -> list[BaseObject]:
        """Получает все объекты всех канвасов."""
        all_objects = []
        for objects in self._objects.values():
            all_objects.extend(objects)
        return all_objects

    def move_object_with_children(self, canvas_id: str, obj: BaseObject, dx: float, dy: float):
        """Перемещает объект и все его дочерние элементы.

        Перемещает только локальные координаты объекта.
        Дочерние объекты следуют за родителем автоматически через систему координат.
        """
        # Перемещаем сам объект (локальные координаты)
        obj.x += dx
        obj.y += dy
        self._notify_object_changed(canvas_id, obj)

    def update_object(self, canvas_id: str, obj: BaseObject):
        """Уведомляет об изменении объекта."""
        self._notify_object_changed(canvas_id, obj)

    # === Factory methods ===

    def create_text_object(
        self,
        name: str = "Text",
        x: float = 50,
        y: float = 50,
        width: float = 200,
        height: float = 50,
        text: str = "Hello World",
        font_family: str = "Arial",
        font_size: int = 16,
        text_color: str = "#000000",
    ) -> TextObject:
        """Создаёт текстовый объект."""
        return TextObject(
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            text=text,
            font_family=font_family,
            font_size=font_size,
            text_color=text_color,
        )

    def create_shape_object(
        self,
        name: str = "Shape",
        x: float = 50,
        y: float = 50,
        width: float = 100,
        height: float = 100,
        color: str = "#CCCCCC",
        shape_type: str = "rect",
    ) -> ShapeObject:
        """Создаёт объект фигуры."""
        return ShapeObject(
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            color=color,
            shape_type=shape_type,
        )

    def create_image_object(
        self,
        name: str = "Image",
        x: float = 50,
        y: float = 50,
        width: float = 200,
        height: float = 200,
        image_path: str | None = None,
    ) -> ImageObject:
        """Создаёт объект изображения."""
        return ImageObject(
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            image_path=image_path,
        )
