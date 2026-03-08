"""Модель текстового объекта."""

from dataclasses import dataclass, field
import uuid
from typing import Optional

from .base_object import BaseObject


@dataclass
class TextObject(BaseObject):
    """Текстовый объект для рендеринга.

    Наследуется от BaseObject и добавляет текстовые свойства.
    """

    name: str = "Text"
    x: float = 0.0
    y: float = 0.0
    width: float = 200.0
    height: float = 50.0
    color: str = "#000000"  # Не используется для текста
    visible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Текстовые свойства
    text: str = "Text"
    font_family: str = "Arial"
    font_size: int = 16
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False
    text_color: str = "#000000"

    # Выравнивание текста
    text_align_h: str = "left"  # left, center, right
    text_align_v: str = "top"  # top, center, bottom

    # Роль для подстановки текста (для CalendarNode)
    role: str | None = None

    def __hash__(self):
        """Хеш по id."""
        return hash(self.id)

    def __eq__(self, other):
        """Сравнение по id."""
        if isinstance(other, TextObject):
            return self.id == other.id
        return False

    def to_dict(self) -> dict:
        """Сериализует объект в словарь."""
        base = super().to_dict()
        base.update({
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_bold": self.font_bold,
            "font_italic": self.font_italic,
            "font_underline": self.font_underline,
            "text_color": self.text_color,
            "text_align_h": self.text_align_h,
            "text_align_v": self.text_align_v,
            "role": self.role,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict) -> "TextObject":
        """Создаёт объект из словаря."""
        return cls(
            name=data.get("name", "Text"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 200.0),
            height=data.get("height", 50.0),
            color=data.get("color", "#000000"),
            visible=data.get("visible", True),
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            text=data.get("text", "Text"),
            font_family=data.get("font_family", "Arial"),
            font_size=data.get("font_size", 16),
            font_bold=data.get("font_bold", False),
            font_italic=data.get("font_italic", False),
            font_underline=data.get("font_underline", False),
            text_color=data.get("text_color", "#000000"),
            stroke_enabled=data.get("stroke_enabled", False),
            stroke_color=data.get("stroke_color", "#000000"),
            stroke_width=data.get("stroke_width", 1.0),
            image_path=data.get("image_path"),
            image_fill=data.get("image_fill", False),
            shape_type=data.get("shape_type", "rect"),
            text_align_h=data.get("text_align_h", "left"),
            text_align_v=data.get("text_align_v", "top"),
            locked=data.get("locked", False),
            rotation=data.get("rotation", 0.0),
            role=data.get("role"),
        )
