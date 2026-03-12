"""Секция обводки: тип линии, позиция, толщина, цвет."""

from PySide6.QtWidgets import QFormLayout, QCheckBox, QComboBox, QDoubleSpinBox

from .base_section import BaseSection
from ..widgets.color_button import ColorButton
from ....models.objects.base_object import BaseObject


STROKE_STYLES = [
    ("Сплошная",       "solid"),
    ("Пунктир",        "dash"),
    ("Точки",          "dot"),
    ("Пунктир-точка",  "dash_dot"),
]

STROKE_POSITIONS = [
    ("По центру", "center"),
    ("Снаружи",   "outside"),
    ("Внутри",    "inside"),
]


class StrokeSection(BaseSection):
    """Обводка с расширенными настройками: тип линии, позиция, цвет, толщина."""

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(4)

        self.enabled_check = QCheckBox()
        self.enabled_check.stateChanged.connect(self._on_enabled)
        layout.addRow("Включена:", self.enabled_check)

        self.color_btn = ColorButton()
        self.color_btn.color_changed.connect(self._on_color)
        layout.addRow("Цвет:", self.color_btn)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.5, 50)
        self.width_spin.setDecimals(1)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.valueChanged.connect(self._on_width)
        layout.addRow("Толщина:", self.width_spin)

        self.style_combo = QComboBox()
        for label, _ in STROKE_STYLES:
            self.style_combo.addItem(label)
        self.style_combo.currentIndexChanged.connect(self._on_style)
        layout.addRow("Тип линии:", self.style_combo)

        self.position_combo = QComboBox()
        for label, _ in STROKE_POSITIONS:
            self.position_combo.addItem(label)
        self.position_combo.currentIndexChanged.connect(self._on_position)
        layout.addRow("Позиция:", self.position_combo)

        self._set_fields_enabled(False)

    def _load(self, obj: BaseObject):
        self.enabled_check.setChecked(obj.stroke_enabled)
        self.color_btn.color = obj.stroke_color

        self.width_spin.blockSignals(True)
        self.width_spin.setValue(obj.stroke_width)
        self.width_spin.blockSignals(False)

        style_vals = [v for _, v in STROKE_STYLES]
        self.style_combo.setCurrentIndex(
            style_vals.index(obj.stroke_style) if obj.stroke_style in style_vals else 0
        )

        pos_vals = [v for _, v in STROKE_POSITIONS]
        self.position_combo.setCurrentIndex(
            pos_vals.index(obj.stroke_position) if obj.stroke_position in pos_vals else 0
        )

        self._set_fields_enabled(obj.stroke_enabled)

    def _set_fields_enabled(self, enabled: bool):
        for w in (self.color_btn, self.width_spin, self.style_combo, self.position_combo):
            w.setEnabled(enabled)

    def _on_enabled(self, state: int):
        if self._obj:
            self._obj.stroke_enabled = state == 2
            self._set_fields_enabled(self._obj.stroke_enabled)
            self._emit()

    def _on_color(self, color: str):
        if self._obj:
            self._obj.stroke_color = color
            self._emit()

    def _on_width(self, value: float):
        if self._obj:
            self._obj.stroke_width = value
            self._emit()

    def _on_style(self, index: int):
        if self._obj:
            self._obj.stroke_style = STROKE_STYLES[index][1]
            self._emit()

    def _on_position(self, index: int):
        if self._obj:
            self._obj.stroke_position = STROKE_POSITIONS[index][1]
            self._emit()
