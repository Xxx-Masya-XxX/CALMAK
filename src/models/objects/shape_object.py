"""Модель объекта-фигуры."""

from __future__ import annotations
from dataclasses import dataclass

from .base_object import BaseObject


@dataclass
class ShapeObject(BaseObject):
    """Объект-фигура (прямоугольник, эллипс, треугольник)."""

    shape_type: str = "rect"    # rect | ellipse | triangle
    color: str = "#CCCCCC"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, ShapeObject) and self.id == other.id

    def get_properties(self) -> dict[str, dict]:
        props = super().get_properties()
        props["Фигура"] = {
            "color":      self.color,
            "shape_type": self.shape_type,
        }
        return props

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"shape_type": self.shape_type, "color": self.color})
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ShapeObject":
        obj = cls(
            name=d.get("name", "Shape"),
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            width=d.get("width", 100.0),
            height=d.get("height", 100.0),
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
            shape_type=d.get("shape_type", "rect"),
            color=d.get("color", "#CCCCCC"),
        )
        obj.id = d.get("id", obj.id)
        return obj