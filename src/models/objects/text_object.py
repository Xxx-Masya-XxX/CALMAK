"""Модель текстового объекта."""

from dataclasses import dataclass, field
import uuid
from typing import Optional

from .base_object import BaseObject


@dataclass
class TextObject(BaseObject):
    """Текстовый объект для рендеринга.

    Расширяет BaseObject текстовым содержимым и настройками шрифта.
    shape_type всегда 'text'.
    """

    # Содержимое
    text: str = "Text"

    # Шрифт
    font_family: str = "Arial"
    font_size: float = 14.0
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False

    # Цвет текста
    text_color: str = "#000000"

    # Горизонтальное выравнивание: left, center, right
    text_align_h: str = "left"

    # Вертикальное выравнивание: top, middle, bottom
    text_align_v: str = "top"

    # Межстрочный интервал (множитель)
    line_height: float = 1.2

    # Перенос слов
    word_wrap: bool = True

    # Автоматически подбирать высоту под содержимое
    auto_height: bool = False

    # Отступы внутри блока
    padding_top: float = 4.0
    padding_right: float = 4.0
    padding_bottom: float = 4.0
    padding_left: float = 4.0

    def __post_init__(self):
        self.shape_type = "text"
        if self.color == "#CCCCCC":
            self.color = "transparent"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, TextObject):
            return self.id == other.id
        return False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_bold": self.font_bold,
            "font_italic": self.font_italic,
            "font_underline": self.font_underline,
            "text_color": self.text_color,
            "text_align_h": self.text_align_h,
            "text_align_v": self.text_align_v,
            "line_height": self.line_height,
            "word_wrap": self.word_wrap,
            "auto_height": self.auto_height,
            "padding_top": self.padding_top,
            "padding_right": self.padding_right,
            "padding_bottom": self.padding_bottom,
            "padding_left": self.padding_left,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TextObject":
        return cls(
            name=data.get("name", "Text"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 200.0),
            height=data.get("height", 50.0),
            color=data.get("color", "transparent"),
            visible=data.get("visible", True),
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            stroke_enabled=data.get("stroke_enabled", False),
            stroke_color=data.get("stroke_color", "#000000"),
            stroke_width=data.get("stroke_width", 1.0),
            locked=data.get("locked", False),
            rotation=data.get("rotation", 0.0),
            text=data.get("text", "Text"),
            font_family=data.get("font_family", "Arial"),
            font_size=data.get("font_size", 14.0),
            font_bold=data.get("font_bold", False),
            font_italic=data.get("font_italic", False),
            font_underline=data.get("font_underline", False),
            text_color=data.get("text_color", "#000000"),
            text_align_h=data.get("text_align_h", "left"),
            text_align_v=data.get("text_align_v", "top"),
            line_height=data.get("line_height", 1.2),
            word_wrap=data.get("word_wrap", True),
            auto_height=data.get("auto_height", False),
            padding_top=data.get("padding_top", 4.0),
            padding_right=data.get("padding_right", 4.0),
            padding_bottom=data.get("padding_bottom", 4.0),
            padding_left=data.get("padding_left", 4.0),
        )