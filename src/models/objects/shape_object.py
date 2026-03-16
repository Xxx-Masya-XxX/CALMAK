"""Модель объекта-фигуры."""

from __future__ import annotations
from dataclasses import dataclass

from .base_object import BaseObject


@dataclass
class ShapeObject(BaseObject):
    """Объект-фигура (прямоугольник, эллипс, треугольник).

    Хранит всё визуальное оформление: форму, заливку, обводку, текстуру.
    BaseObject отвечает только за трансформацию и иерархию.
    """

    # --- Форма ---
    shape_type: str = "rect"          # rect | ellipse | triangle

    # --- Заливка ---
    color: str = "#CCCCCC"

    # --- Обводка ---
    stroke_enabled: bool = False
    stroke_color: str = "#000000"
    stroke_width: float = 1.0
    stroke_style: str = "solid"       # solid | dash | dot | dash_dot
    stroke_position: str = "center"   # center | outside | inside

    # --- Текстура / изображение ---
    image_path: str | None = None
    image_fill: bool = False          # True → растянуть, False → замостить

    # ------------------------------------------------------------------

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, ShapeObject) and self.id == other.id

    # ------------------------------------------------------------------
    # PropertiesPanel
    # ------------------------------------------------------------------

    def get_properties(self) -> dict[str, dict]:
        props = super().get_properties()
        props["Фигура"] = {
            "shape_type": self.shape_type,
            "color":      self.color,
        }
        props["Обводка"] = {
            "stroke_enabled":  self.stroke_enabled,
            "stroke_color":    self.stroke_color,
            "stroke_width":    self.stroke_width,
            "stroke_style":    self.stroke_style,
            "stroke_position": self.stroke_position,
        }
        props["Текстура"] = {
            "image_path": self.image_path or "",
            "image_fill": self.image_fill,
        }
        return props

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "shape_type":      self.shape_type,
            "color":           self.color,
            "stroke_enabled":  self.stroke_enabled,
            "stroke_color":    self.stroke_color,
            "stroke_width":    self.stroke_width,
            "stroke_style":    self.stroke_style,
            "stroke_position": self.stroke_position,
            "image_path":      self.image_path,
            "image_fill":      self.image_fill,
        })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ShapeObject":
        obj = cls(
            # --- базовые ---
            name=d.get("name", "Shape"),
            visible=d.get("visible", True),
            locked=d.get("locked", False),
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            width=d.get("width", 100.0),
            height=d.get("height", 100.0),
            rotation=d.get("rotation", 0.0),
            parent_id=d.get("parent_id"),
            # --- фигура ---
            shape_type=d.get("shape_type", "rect"),
            color=d.get("color", "#CCCCCC"),
            # --- обводка ---
            stroke_enabled=d.get("stroke_enabled", False),
            stroke_color=d.get("stroke_color", "#000000"),
            stroke_width=d.get("stroke_width", 1.0),
            stroke_style=d.get("stroke_style", "solid"),
            stroke_position=d.get("stroke_position", "center"),
            # --- текстура ---
            image_path=d.get("image_path"),
            image_fill=d.get("image_fill", False),
        )
        obj.id = d.get("id", obj.id)
        return obj