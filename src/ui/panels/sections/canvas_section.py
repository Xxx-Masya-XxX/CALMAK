"""Секция свойств канваса."""

from PySide6.QtWidgets import QGroupBox, QFormLayout, QLineEdit, QDoubleSpinBox
from PySide6.QtCore import Signal

from ...panels.widgets.color_button import ColorButton
from ....models.canvas import Canvas


class CanvasSection(QGroupBox):
    """Группа свойств канваса: имя, размер, цвет фона."""

    canvas_changed = Signal(Canvas)

    def __init__(self, parent=None):
        super().__init__("Канвас", parent)
        self._canvas: Canvas | None = None
        self._blocking = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(4)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Имя канваса")
        self.name_edit.textChanged.connect(self._on_name)
        layout.addRow("Имя:", self.name_edit)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(100, 10000)
        self.width_spin.setDecimals(0)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._on_size)
        layout.addRow("Ширина:", self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(100, 10000)
        self.height_spin.setDecimals(0)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._on_size)
        layout.addRow("Высота:", self.height_spin)

        self.bg_color_btn = ColorButton()
        self.bg_color_btn.color_changed.connect(self._on_color)
        layout.addRow("Фон:", self.bg_color_btn)

    def load(self, canvas: Canvas):
        self._canvas = canvas
        self._blocking = True
        self.name_edit.setText(canvas.name)
        self.width_spin.setValue(canvas.width)
        self.height_spin.setValue(canvas.height)
        self.bg_color_btn.color = canvas.background_color
        self._blocking = False

    def _emit(self):
        if not self._blocking and self._canvas is not None:
            self.canvas_changed.emit(self._canvas)

    def _on_name(self, text: str):
        if self._canvas:
            self._canvas.name = text
            self._emit()

    def _on_size(self):
        if self._canvas:
            self._canvas.width = self.width_spin.value()
            self._canvas.height = self.height_spin.value()
            self._emit()

    def _on_color(self, color: str):
        if self._canvas:
            self._canvas.background_color = color
            self._emit()
