"""Модель объекта изображения."""

from dataclasses import dataclass, field
import uuid
from typing import Optional

from .base_object import BaseObject


@dataclass
class ImageObject(BaseObject):
    """Объект изображения для рендеринга.

    Наследуется от BaseObject и добавляет свойства изображения.
    """

    name: str = "Image"
    x: float = 0.0
    y: float = 0.0
    width: float = 200.0
    height: float = 200.0
    color: str = "#CCCCCC"  # Не используется для изображения
    visible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Свойства изображения
    image_path: str | None = None
    image_fill: bool = True  # Заполнять ли изображением
    image_scale_mode: str = "stretch"  # stretch, preserve_aspect, crop

    # Обводка
    stroke_enabled: bool = False
    stroke_color: str = "#000000"
    stroke_width: float = 1.0

    # Тип фигуры (для ImageObject всегда rect)
    shape_type: str = "rect"

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
        if isinstance(other, ImageObject):
            return self.id == other.id
        return False

    def to_dict(self) -> dict:
        """Сериализует объект в словарь."""
        base = super().to_dict()
        base.update({
            "image_scale_mode": self.image_scale_mode,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict) -> "ImageObject":
        """Создаёт объект из словаря."""
        return cls(
            name=data.get("name", "Image"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 200.0),
            height=data.get("height", 200.0),
            color=data.get("color", "#CCCCCC"),
            visible=data.get("visible", True),
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            image_path=data.get("image_path"),
            image_fill=data.get("image_fill", True),
            image_scale_mode=data.get("image_scale_mode", "stretch"),
            stroke_enabled=data.get("stroke_enabled", False),
            stroke_color=data.get("stroke_color", "#000000"),
            stroke_width=data.get("stroke_width", 1.0),
            shape_type=data.get("shape_type", "rect"),
            locked=data.get("locked", False),
            rotation=data.get("rotation", 0.0),
        )
