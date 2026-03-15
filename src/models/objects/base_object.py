"""Базовый объект сцены.

Каждый объект описывает свои параметры через get_properties() → dict[str, dict].
Ключ верхнего уровня — название группы (QGroupBox в PropertiesPanel).
Вложенный dict: ключ = имя атрибута, значение = текущее значение атрибута.

PropertiesPanel определяет тип виджета автоматически:
  bool                          → QCheckBox
  float                         → QDoubleSpinBox
  int                           → QSpinBox
  str начинающийся с '#' len 7  → ColorButton
  str                           → QLineEdit
  ключ в COMBO_OPTIONS          → QComboBox
"""

from __future__ import annotations
from dataclasses import dataclass, field
import uuid


@dataclass
class BaseObject:
    """Базовый объект сцены."""

    name: str = "Object"
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0
    visible: bool = True
    locked: bool = False

    # Обводка
    stroke_enabled: bool = False
    stroke_color: str = "#000000"
    stroke_width: float = 1.0
    stroke_style: str = "solid"       # solid | dash | dot | dash_dot
    stroke_position: str = "center"   # center | outside | inside

    # Изображение
    image_path: str | None = None
    image_fill: bool = False

    # Иерархия
    parent_id: str | None = None
    _parent: "BaseObject | None" = field(default=None, repr=False, compare=False)

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, BaseObject) and self.id == other.id

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def parent(self) -> "BaseObject | None":
        return self._parent

    @parent.setter
    def parent(self, value: "BaseObject | None"):
        self._parent = value
        self.parent_id = value.id if value else None

    def get_global_position(self) -> tuple[float, float]:
        if self._parent:
            px, py = self._parent.get_global_position()
            return px + self.x, py + self.y
        return self.x, self.y

    @property
    def global_x(self) -> float:
        return self.get_global_position()[0]

    @property
    def global_y(self) -> float:
        return self.get_global_position()[1]

    # ------------------------------------------------------------------
    # Система параметров для PropertiesPanel
    # ------------------------------------------------------------------

    def get_properties(self) -> dict[str, dict]:
        """Возвращает словарь групп параметров.

        Подклассы вызывают super().get_properties() и добавляют свои группы:

            def get_properties(self):
                props = super().get_properties()
                props["Фигура"] = {"color": self.color, ...}
                return props
        """
        return {
            "Основные": {
                "name":    self.name,
                "visible": self.visible,
                "locked":  self.locked,
            },
            "Трансформация": {
                "x":        self.x,
                "y":        self.y,
                "width":    self.width,
                "height":   self.height,
                "rotation": self.rotation,
            },
            "Обводка": {
                "stroke_enabled":  self.stroke_enabled,
                "stroke_color":    self.stroke_color,
                "stroke_width":    self.stroke_width,
                "stroke_style":    self.stroke_style,
                "stroke_position": self.stroke_position,
            },
        }

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "type":            self.__class__.__name__,
            "name":            self.name,
            "x":               self.x,
            "y":               self.y,
            "width":           self.width,
            "height":          self.height,
            "rotation":        self.rotation,
            "visible":         self.visible,
            "locked":          self.locked,
            "stroke_enabled":  self.stroke_enabled,
            "stroke_color":    self.stroke_color,
            "stroke_width":    self.stroke_width,
            "stroke_style":    self.stroke_style,
            "stroke_position": self.stroke_position,
            "image_path":      self.image_path,
            "image_fill":      self.image_fill,
            "parent_id":       self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BaseObject":
        obj = cls(
            name=d.get("name", "Object"),
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
        )
        obj.id = d.get("id", obj.id)
        return obj