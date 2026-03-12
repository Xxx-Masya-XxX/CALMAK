"""Секция внешнего вида: цвет фона, видимость, форма, изображение."""

from PySide6.QtWidgets import (
    QFormLayout, QCheckBox, QComboBox,
    QLineEdit, QPushButton, QFileDialog
)

from .base_section import BaseSection
from ..widgets.color_button import ColorButton
from ....models.objects.base_object import BaseObject


class AppearanceSection(BaseSection):
    """Цвет фона, видимость, тип формы, изображение."""

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(4)

        # Видимость
        self.visible_check = QCheckBox()
        self.visible_check.stateChanged.connect(self._on_visible)
        layout.addRow("Видимый:", self.visible_check)

        # Цвет фона
        self.color_btn = ColorButton()
        self.color_btn.color_changed.connect(self._on_color)
        layout.addRow("Цвет фона:", self.color_btn)

        # Тип формы (скрывается для TextObject)
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Прямоугольник", "Эллипс", "Треугольник"])
        self.shape_combo.currentIndexChanged.connect(self._on_shape)
        self._shape_label = layout.labelForField(self.shape_combo) if False else None
        layout.addRow("Фигура:", self.shape_combo)

        # Изображение
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("Путь к изображению")
        self.image_path_edit.setReadOnly(True)
        layout.addRow("Изображение:", self.image_path_edit)

        self.image_browse_btn = QPushButton("Обзор...")
        self.image_browse_btn.clicked.connect(self._on_image_browse)
        layout.addRow("", self.image_browse_btn)

        self.image_fill_check = QCheckBox()
        self.image_fill_check.stateChanged.connect(self._on_image_fill)
        layout.addRow("Заполнять:", self.image_fill_check)

    def _load(self, obj: BaseObject):
        from ....models.objects.text_object import TextObject
        self.visible_check.setChecked(obj.visible)
        self.color_btn.color = obj.color if obj.color else "#CCCCCC"
        self.shape_combo.setCurrentIndex(
            {"rect": 0, "ellipse": 1, "triangle": 2}.get(obj.shape_type, 0)
        )
        self.image_path_edit.setText(obj.image_path or "")
        self.image_fill_check.setChecked(obj.image_fill)

        # Скрываем выбор формы для текстового объекта
        is_text = isinstance(obj, TextObject)
        self.shape_combo.setVisible(not is_text)

    def _on_visible(self, state: int):
        if self._obj:
            self._obj.visible = state == 2
            self._emit()

    def _on_color(self, color: str):
        if self._obj:
            self._obj.color = color
            self._emit()

    def _on_shape(self, index: int):
        if self._obj:
            self._obj.shape_type = {0: "rect", 1: "ellipse", 2: "triangle"}.get(index, "rect")
            self._emit()

    def _on_image_browse(self):
        if self._obj:
            path, _ = QFileDialog.getOpenFileName(
                self, "Выберите изображение", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if path:
                self._obj.image_path = path
                self.image_path_edit.setText(path)
                self._emit()

    def _on_image_fill(self, state: int):
        if self._obj:
            self._obj.image_fill = state == 2
            self._emit()
