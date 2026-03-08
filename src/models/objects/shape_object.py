"""Модель объекта фигуры."""

from dataclasses import dataclass, field
import uuid
from typing import Optional

from .base_object import BaseObject


@dataclass
class ShapeObject(BaseObject):
    """Объект фигуры для рендеринга.

    Наследуется от BaseObject и специализируется для фигур.
    """

    name: str = "Shape"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    color: str = "#CCCCCC"
    visible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Тип фигуры: rect, ellipse, triangle
    shape_type: str = "rect"

    # Обводка
    stroke_enabled: bool = False
    stroke_color: str = "#000000"
    stroke_width: float = 1.0

    # Изображение фона
    image_path: str | None = None
    image_fill: bool = False

    # Ссылка на родительский объект
    _parent: Optional['BaseObject'] = field(default=None, repr=False, compare=False)

    # Блокировка объекта
    locked: bool = False

    # Поворот объекта в градусах
    rotation: float = 0.0

    def __hash__(self):
        """Хеш по id."""
        return hash(self.id)

    def __eq__(self, other):
        """Сравнение по id."""
        if isinstance(other, ShapeObject):
            return self.id == other.id
        return False

    @classmethod
    def from_dict(cls, data: dict) -> "ShapeObject":
        """Создаёт объект из словаря."""
        return cls(
            name=data.get("name", "Shape"),
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
            image_path=data.get("image_path"),
            image_fill=data.get("image_fill", False),
            shape_type=data.get("shape_type", "rect"),
            locked=data.get("locked", False),
            rotation=data.get("rotation", 0.0),
        )
