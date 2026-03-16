"""Базовый объект сцены.

BaseObject хранит ТОЛЬКО трансформацию и иерархию.
Всё остальное (цвет, обводка, текстура…) — ответственность подклассов.

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
    """Базовый объект сцены. Содержит только трансформацию и иерархию."""

    # --- Мета ---
    name: str = "Object"
    visible: bool = True
    locked: bool = False

    # --- Трансформация ---
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0

    # --- Иерархия ---
    parent_id: str | None = None
    _parent: "BaseObject | None" = field(default=None, repr=False, compare=False)

    # --- Идентификатор ---
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ------------------------------------------------------------------
    # Базовые dunder
    # ------------------------------------------------------------------

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, BaseObject) and self.id == other.id

    # ------------------------------------------------------------------
    # Иерархия
    # ------------------------------------------------------------------

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
        }

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "type":      self.__class__.__name__,
            "name":      self.name,
            "visible":   self.visible,
            "locked":    self.locked,
            "x":         self.x,
            "y":         self.y,
            "width":     self.width,
            "height":    self.height,
            "rotation":  self.rotation,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BaseObject":
        obj = cls(
            name=d.get("name", "Object"),
            visible=d.get("visible", True),
            locked=d.get("locked", False),
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            width=d.get("width", 100.0),
            height=d.get("height", 100.0),
            rotation=d.get("rotation", 0.0),
            parent_id=d.get("parent_id"),
        )
        obj.id = d.get("id", obj.id)
        return obj