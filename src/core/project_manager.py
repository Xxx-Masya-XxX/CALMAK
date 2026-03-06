"""Менеджер проекта для управления канвасами и объектами."""

from ..models import Canvas, BaseObject


class ProjectManager:
    """Управляет канвасами и объектами проекта."""
    
    def __init__(self):
        self._canvases: dict[str, Canvas] = {}
        self._objects: dict[str, list[BaseObject]] = {}  # canvas_id -> objects
        self._active_canvas_id: str | None = None
    
    def add_canvas(self, canvas: Canvas) -> Canvas:
        """Добавляет новый канвас."""
        self._canvases[canvas.id] = canvas
        self._objects[canvas.id] = []
        if self._active_canvas_id is None:
            self._active_canvas_id = canvas.id
        return canvas
    
    def remove_canvas(self, canvas_id: str):
        """Удаляет канвас."""
        if canvas_id in self._canvases:
            del self._canvases[canvas_id]
            if canvas_id in self._objects:
                del self._objects[canvas_id]
            if self._active_canvas_id == canvas_id:
                self._active_canvas_id = next(iter(self._canvases.keys()), None)
    
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
    
    def get_active_canvas(self) -> Canvas | None:
        """Получает активный канвас."""
        if self._active_canvas_id:
            return self._canvases.get(self._active_canvas_id)
        return None
    
    def get_active_canvas_id(self) -> str | None:
        """Получает ID активного канваса."""
        return self._active_canvas_id
    
    def add_object(self, canvas_id: str, obj: BaseObject) -> BaseObject:
        """Добавляет объект на канвас."""
        if canvas_id not in self._objects:
            self._objects[canvas_id] = []
        self._objects[canvas_id].append(obj)
        return obj
    
    def remove_object(self, canvas_id: str, obj: BaseObject):
        """Удаляет объект с канваса (включая дочерние)."""
        if canvas_id in self._objects:
            # Сначала удаляем дочерние объекты
            children = self.get_children(canvas_id, obj.id)
            for child in children:
                self._objects[canvas_id] = [o for o in self._objects[canvas_id] if o != child]
            # Затем удаляем сам объект
            self._objects[canvas_id] = [o for o in self._objects[canvas_id] if o != obj]
    
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
        """Устанавливает родителя для объекта."""
        if parent:
            obj.parent_id = parent.id
        else:
            obj.parent_id = None
    
    def get_all_objects(self) -> list[BaseObject]:
        """Получает все объекты всех канвасов."""
        all_objects = []
        for objects in self._objects.values():
            all_objects.extend(objects)
        return all_objects
    
    def move_object_with_children(self, canvas_id: str, obj: BaseObject, dx: float, dy: float):
        """Перемещает объект и все его дочерние элементы."""
        # Перемещаем сам объект
        obj.x += dx
        obj.y += dy
        
        # Перемещаем дочерние объекты
        children = self.get_children(canvas_id, obj.id)
        for child in children:
            child.x += dx
            child.y += dy
