"""Модель канваса."""

from dataclasses import dataclass, field
import uuid


@dataclass
class Canvas:
    """Канвас для рендеринга объектов.

    Представляет собой холст с размерами и списком объектов.
    """

    name: str = "Canvas"
    width: float = 800.0
    height: float = 600.0
    background_color: str = "#FFFFFF"
    visible: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __hash__(self):
        """Хеш по id."""
        return hash(self.id)

    def __eq__(self, other):
        """Сравнение по id."""
        if isinstance(other, Canvas):
            return self.id == other.id
        return False

    def to_dict(self) -> dict:
        """Сериализует канвас в словарь."""
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "background_color": self.background_color,
            "visible": self.visible,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Canvas":
        """Создаёт канвас из словаря."""
        return cls(
            name=data.get("name", "Canvas"),
            width=data.get("width", 800.0),
            height=data.get("height", 600.0),
            background_color=data.get("background_color", "#FFFFFF"),
            visible=data.get("visible", True),
            id=data.get("id", str(uuid.uuid4())),
        )
