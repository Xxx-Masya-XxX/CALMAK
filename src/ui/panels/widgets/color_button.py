"""Кнопка выбора цвета с превью."""

from PySide6.QtWidgets import QPushButton, QColorDialog
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal


class ColorButton(QPushButton):
    """Кнопка с цветным превью фона, открывает QColorDialog по клику."""

    color_changed = Signal(str)  # hex-строка

    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(26)
        self.clicked.connect(self._pick_color)
        self._apply_style()

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        self._color = value
        self._apply_style()

    def _apply_style(self):
        lightness = QColor(self._color).lightness() if self._color not in ("transparent", "") else 255
        text_color = "#000000" if lightness > 128 else "#ffffff"
        self.setStyleSheet(
            f"background-color: {self._color}; color: {text_color}; "
            f"border: 1px solid #888; border-radius: 3px; padding: 2px 8px;"
        )
        self.setText(self._color if self._color else "—")

    def _pick_color(self):
        initial = QColor(self._color) if self._color not in ("transparent", "") else QColor("#ffffff")
        new_color = QColorDialog.getColor(initial, self, "Выберите цвет")
        if new_color.isValid():
            self.color = new_color.name()
            self.color_changed.emit(self._color)
