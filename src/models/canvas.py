"""Модель канваса."""

from __future__ import annotations
from dataclasses import dataclass, field
import uuid


@dataclass
class Canvas:
    """Канвас — контейнер для объектов."""

    name: str = "Canvas"
    width: float = 2480.0
    height: float = 3508.0
    background_color: str = "#FFFFFF"

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Canvas) and self.id == other.id

    # ------------------------------------------------------------------
    # Система параметров для PropertiesPanel
    # ------------------------------------------------------------------

    def get_properties(self) -> dict[str, dict]:
        """Параметры канваса для динамической панели свойств."""
        return {
            "Канвас": {
                "name":             self.name,
                "width":            self.width,
                "height":           self.height,
                "background_color": self.background_color,
            }
        }

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "name":             self.name,
            "width":            self.width,
            "height":           self.height,
            "background_color": self.background_color,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Canvas":
        obj = cls(
            name=d.get("name", "Canvas"),
            width=d.get("width", 2480.0),
            height=d.get("height", 3508.0),
            background_color=d.get("background_color", "#FFFFFF"),
        )
        obj.id = d.get("id", obj.id)
        return obj