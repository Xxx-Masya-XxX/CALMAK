"""Базовые классы элементов канваса для редактора каллажей."""

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class CanvasElement:
    """Базовый класс для всех элементов канваса."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Element"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    visible: bool = True
    locked: bool = False
    parent_id: str | None = None
    children: list["CanvasElement"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Сериализация элемента в словарь."""
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "visible": self.visible,
            "locked": self.locked,
            "parent_id": self.parent_id,
            "type": self.__class__.__name__,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanvasElement":
        """Десериализация элемента из словаря."""
        element = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Element"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 100.0),
            height=data.get("height", 100.0),
            visible=data.get("visible", True),
            locked=data.get("locked", False),
            parent_id=data.get("parent_id"),
        )
        for child_data in data.get("children", []):
            child = CanvasElement.from_dict(child_data)
            child.parent_id = element.id
            element.children.append(child)
        return element

    def find_element(self, element_id: str) -> "CanvasElement | None":
        """Найти элемент по ID (рекурсивно)."""
        if self.id == element_id:
            return self
        for child in self.children:
            found = child.find_element(element_id)
            if found:
                return found
        return None

    def get_all_elements(self) -> list["CanvasElement"]:
        """Получить все элементы в виде плоского списка."""
        elements = [self]
        for child in self.children:
            elements.extend(child.get_all_elements())
        return elements


@dataclass
class ImageElement(CanvasElement):
    """Элемент изображения."""

    image_path: str = ""
    opacity: float = 1.0
    name: str = "Image"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["image_path"] = self.image_path
        data["opacity"] = self.opacity
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageElement":
        element = super().from_dict(data)
        element.image_path = data.get("image_path", "")
        element.opacity = data.get("opacity", 1.0)
        return element


@dataclass
class TextElement(CanvasElement):
    """Элемент текста."""

    text: str = "Text"
    font_size: int = 24
    font_family: str = "Arial"
    color: str = "#000000"
    bold: bool = False
    italic: bool = False
    name: str = "Text"
    width: float = 200.0
    height: float = 50.0

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["text"] = self.text
        data["font_size"] = self.font_size
        data["font_family"] = self.font_family
        data["color"] = self.color
        data["bold"] = self.bold
        data["italic"] = self.italic
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextElement":
        element = super().from_dict(data)
        element.text = data.get("text", "Text")
        element.font_size = data.get("font_size", 24)
        element.font_family = data.get("font_family", "Arial")
        element.color = data.get("color", "#000000")
        element.bold = data.get("bold", False)
        element.italic = data.get("italic", False)
        return element


@dataclass
class ShapeElement(CanvasElement):
    """Элемент фигуры (прямоугольник, эллипс, линия)."""

    shape_type: str = "rectangle"  # rectangle, ellipse, line
    fill_color: str = "#CCCCCC"
    stroke_color: str = "#000000"
    stroke_width: int = 1
    opacity: float = 1.0
    name: str = "Shape"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["shape_type"] = self.shape_type
        data["fill_color"] = self.fill_color
        data["stroke_color"] = self.stroke_color
        data["stroke_width"] = self.stroke_width
        data["opacity"] = self.opacity
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShapeElement":
        element = super().from_dict(data)
        element.shape_type = data.get("shape_type", "rectangle")
        element.fill_color = data.get("fill_color", "#CCCCCC")
        element.stroke_color = data.get("stroke_color", "#000000")
        element.stroke_width = data.get("stroke_width", 1)
        element.opacity = data.get("opacity", 1.0)
        return element


@dataclass
class Canvas(CanvasElement):
    """Канвас - корневой контейнер для всех элементов."""

    name: str = "Canvas"
    width: float = 500.0
    height: float = 500.0
    parent_id: None = None

    def add_child(self, child: CanvasElement) -> None:
        """Добавить дочерний элемент."""
        child.parent_id = self.id
        self.children.append(child)

    def remove_child(self, child_id: str) -> None:
        """Удалить дочерний элемент по ID."""
        self.children = [c for c in self.children if c.id != child_id]
