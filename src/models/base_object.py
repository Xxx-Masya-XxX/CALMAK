"""Модель базового объекта."""

from dataclasses import dataclass, field
import uuid


@dataclass
class BaseObject:
    """Базовый объект для рендеринга.
    
    Представляет собой квадрат/прямоугольник с позицией и размерами.
    Поддерживает иерархию через parent_id.
    """
    
    name: str = "Object"
    x: float = 0.0
    y: float = 0.0
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
    
    # Изображение фона
    image_path: str | None = None
    image_fill: bool = False  # Заполнять ли изображением
    
    # Тип фигуры: rect, ellipse, triangle
    shape_type: str = "rect"
    
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
    def bounds(self) -> tuple[float, float, float, float]:
        """Возвращает границы объекта (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)
    
    def contains_point(self, px: float, py: float) -> bool:
        """Проверяет, находится ли точка внутри объекта."""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)
    
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
            "image_path": self.image_path,
            "image_fill": self.image_fill,
            "shape_type": self.shape_type,
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
            image_path=data.get("image_path"),
            image_fill=data.get("image_fill", False),
            shape_type=data.get("shape_type", "rect"),
        )
