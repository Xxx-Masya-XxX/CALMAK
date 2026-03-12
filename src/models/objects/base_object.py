"""Модель базового объекта."""

from dataclasses import dataclass, field
import uuid
from typing import Optional


@dataclass
class BaseObject:
    """Базовый объект для рендеринга.

    Представляет собой квадрат/прямоугольник с позицией и размерами.
    Поддерживает иерархию через parent_id.

    Координаты:
    - x, y - локальные координаты относительно родителя (если есть) или глобальные (если нет)
    - При наличии родителя x, y хранят позицию относительно родителя
    """

    name: str = "Object"
    x: float = 0.0  # Локальная координата X относительно родителя
    y: float = 0.0  # Локальная координата Y относительно родителя
    width: float = 100.0
    height: float = 100.0
    color: str = "#CCCCCC"
    visible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Иерархия
    parent_id: str | None = None

    # Обводка
    stroke_enabled: bool = False
    stroke_color: str = "#000000"
    stroke_width: float = 1.0
    # Тип линии обводки: solid, dash, dot, dash_dot
    stroke_style: str = "solid"

    # Позиция обводки: center, outside, inside
    stroke_position: str = "center"
    # Изображение фона
    image_path: str | None = None
    image_fill: bool = False  # Заполнять ли изображением

    # Тип фигуры: rect, ellipse, triangle
    shape_type: str = "rect"

    # Ссылка на родительский объект (устанавливается извне)
    _parent: Optional['BaseObject'] = field(default=None, repr=False, compare=False)

    # Блокировка объекта (запрет перемещения и изменения размера)
    locked: bool = False

    # Поворот объекта в градусах
    rotation: float = 0.0

    def __hash__(self):
        """Хеш по id."""
        return hash(self.id)

    def __eq__(self, other):
        """Сравнение по id."""
        if isinstance(other, BaseObject):
            return self.id == other.id
        return False

    @property
    def is_root(self) -> bool:
        """Проверяет, является ли объект корневым."""
        return self.parent_id is None

    @property
    def parent(self) -> Optional['BaseObject']:
        """Возвращает родительский объект."""
        return self._parent

    @parent.setter
    def parent(self, value: Optional['BaseObject']):
        """Устанавливает родительский объект."""
        self._parent = value
        if value is not None:
            self.parent_id = value.id
        else:
            self.parent_id = None

    def get_global_position(self) -> tuple[float, float]:
        """Возвращает глобальные координаты объекта (на сцене)."""
        if self._parent is None:
            return (self.x, self.y)

        parent_global = self._parent.get_global_position()
        return (parent_global[0] + self.x, parent_global[1] + self.y)

    @property
    def global_x(self) -> float:
        """Глобальная координата X на сцене."""
        return self.get_global_position()[0]

    @property
    def global_y(self) -> float:
        """Глобальная координата Y на сцене."""
        return self.get_global_position()[1]

    @property
    def local_x(self) -> float:
        """Локальная координата X относительно родителя."""
        return self.x

    @property
    def local_y(self) -> float:
        """Локальная координата Y относительно родителя."""
        return self.y

    def set_local_position(self, x: float, y: float):
        """Устанавливает локальные координаты относительно родителя."""
        self.x = x
        self.y = y

    def set_global_position(self, x: float, y: float):
        """Устанавливает глобальные координаты, конвертируя в локальные если есть родитель."""
        if self._parent is None:
            self.x = x
            self.y = y
        else:
            parent_global = self._parent.get_global_position()
            self.x = x - parent_global[0]
            self.y = y - parent_global[1]

    def convert_to_child_local(self, x: float, y: float) -> tuple[float, float]:
        """Конвертирует глобальные координаты в локальные для дочернего объекта."""
        if self._parent is None:
            return (x, y)

        parent_global = self._parent.get_global_position()
        return (x - parent_global[0], y - parent_global[1])

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Возвращает границы объекта в локальных координатах (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    @property
    def global_bounds(self) -> tuple[float, float, float, float]:
        """Возвращает границы объекта в глобальных координатах."""
        gx, gy = self.get_global_position()
        return (gx, gy, self.width, self.height)

    def contains_point(self, px: float, py: float) -> bool:
        """Проверяет, находится ли точка внутри объекта (в локальных координатах)."""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def contains_global_point(self, px: float, py: float) -> bool:
        """Проверяет, находится ли глобальная точка внутри объекта."""
        gx, gy = self.get_global_position()
        return (gx <= px <= gx + self.width and
                gy <= py <= gy + self.height)

    def to_dict(self) -> dict:
        """Сериализует объект в словарь."""
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "color": self.color,
            "visible": self.visible,
            "id": self.id,
            "parent_id": self.parent_id,
            "stroke_enabled": self.stroke_enabled,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "stroke_style": self.stroke_style,
            "stroke_position": self.stroke_position,
            "image_path": self.image_path,
            "image_fill": self.image_fill,
            "shape_type": self.shape_type,
            "locked": self.locked,
            "rotation": self.rotation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaseObject":
        """Создаёт объект из словаря."""
        return cls(
            name=data.get("name", "Object"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 100.0),
            height=data.get("height", 100.0),
            color=data.get("color", "#CCCCCC"),
            visible=data.get("visible", True),
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            stroke_enabled=data.get("stroke_enabled", False),
            stroke_color=data.get("stroke_color", "#000000"),
            stroke_width=data.get("stroke_width", 1.0),
            stroke_style=data.get("stroke_style", "solid"),
            stroke_position=data.get("stroke_position", "center"),
            image_path=data.get("image_path"),
            image_fill=data.get("image_fill", False),
            shape_type=data.get("shape_type", "rect"),
            locked=data.get("locked", False),
            rotation=data.get("rotation", 0.0),
        )
