"""Модель текстового объекта."""

from __future__ import annotations
from dataclasses import dataclass

from .base_object import BaseObject


@dataclass
class TextObject(BaseObject):
    """Объект с текстом."""

    text: str = "Текст"
    font_family: str = "Arial"
    font_size: float = 24.0
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False
    text_color: str = "#000000"
    text_align_h: str = "left"    # left | center | right
    text_align_v: str = "top"     # top | middle | bottom
    line_height: float = 1.2
    word_wrap: bool = True

    def __post_init__(self):
        pass

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, TextObject) and self.id == other.id

    def get_properties(self) -> dict[str, dict]:
        props = super().get_properties()
        props["Текст"] = {
            "text":           self.text,
            "font_family":    self.font_family,
            "font_size":      self.font_size,
            "font_bold":      self.font_bold,
            "font_italic":    self.font_italic,
            "font_underline": self.font_underline,
            "text_color":     self.text_color,
            "text_align_h":   self.text_align_h,
            "text_align_v":   self.text_align_v,
            "line_height":    self.line_height,
            "word_wrap":      self.word_wrap,
        }
        return props

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "text":           self.text,
            "font_family":    self.font_family,
            "font_size":      self.font_size,
            "font_bold":      self.font_bold,
            "font_italic":    self.font_italic,
            "font_underline": self.font_underline,
            "text_color":     self.text_color,
            "text_align_h":   self.text_align_h,
            "text_align_v":   self.text_align_v,
            "line_height":    self.line_height,
            "word_wrap":      self.word_wrap,
        })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TextObject":
        obj = cls(
            name=d.get("name", "Text"),
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            width=d.get("width", 200.0),
            height=d.get("height", 50.0),
            rotation=d.get("rotation", 0.0),
            visible=d.get("visible", True),
            locked=d.get("locked", False),
            stroke_enabled=d.get("stroke_enabled", False),
            stroke_color=d.get("stroke_color", "#000000"),
            stroke_width=d.get("stroke_width", 1.0),
            stroke_style=d.get("stroke_style", "solid"),
            stroke_position=d.get("stroke_position", "center"),
            image_path=d.get("image_path"),
            image_fill=d.get("image_fill", False),
            parent_id=d.get("parent_id"),
            text=d.get("text", "Текст"),
            font_family=d.get("font_family", "Arial"),
            font_size=d.get("font_size", 24.0),
            font_bold=d.get("font_bold", False),
            font_italic=d.get("font_italic", False),
            font_underline=d.get("font_underline", False),
            text_color=d.get("text_color", "#000000"),
            text_align_h=d.get("text_align_h", "left"),
            text_align_v=d.get("text_align_v", "top"),
            line_height=d.get("line_height", 1.2),
            word_wrap=d.get("word_wrap", True),
        )
        obj.id = d.get("id", obj.id)
        return obj