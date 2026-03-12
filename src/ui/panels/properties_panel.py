"""Панель свойств объектов."""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit,
    QScrollArea, QWidget
)
from PySide6.QtCore import Signal, Qt

from ...models.objects.base_object import BaseObject
from ...models.objects.text_object import TextObject
from ...models.canvas import Canvas
from .sections import (
    CanvasSection, TransformSection, AppearanceSection,
    StrokeSection, TextSection
)


class PropertiesPanel(QFrame):
    """Панель свойств выбранного объекта или канваса.

    Каждая группа свойств — отдельная секция со своим load() и signal.
    PropertiesPanel только управляет видимостью и маршрутизирует сигналы.
    """

    canvas_changed = Signal(Canvas)
    object_changed = Signal(BaseObject)
    request_objects_list = Signal()

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self._current_canvas: Canvas | None = None
        self._current_object: BaseObject | None = None

        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(4)

        # Заголовок
        self.title_label = QLabel("Свойства")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(self.title_label)

        # Имя объекта (отдельно — всегда сверху)
        from PySide6.QtWidgets import QGroupBox, QFormLayout
        self._name_group = QGroupBox("Объект")
        name_form = QFormLayout(self._name_group)
        name_form.setSpacing(4)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Имя объекта")
        self._name_edit.textChanged.connect(self._on_name_changed)
        name_form.addRow("Имя:", self._name_edit)
        layout.addWidget(self._name_group)

        # Канвас
        self.canvas_section = CanvasSection()
        layout.addWidget(self.canvas_section)

        # Секции объекта
        self.transform = TransformSection()
        self.appearance = AppearanceSection("s")
        self.stroke = StrokeSection("Обводка")
        self.text_section = TextSection("Текст")

        for section in (self.transform, self.appearance, self.stroke, self.text_section):
            layout.addWidget(section)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # По умолчанию всё скрыто
        self._hide_all()

    def _connect_signals(self):
        self.canvas_section.canvas_changed.connect(self.canvas_changed)
        self.transform.object_changed.connect(self.object_changed)
        self.appearance.object_changed.connect(self.object_changed)
        self.stroke.object_changed.connect(self.object_changed)
        self.text_section.object_changed.connect(self.object_changed)

    # ------------------------------------------------------------------
    # Публичный API (совместим со старым PropertiesPanel)
    # ------------------------------------------------------------------

    def set_canvas(self, canvas: Canvas | None):
        """Показывает свойства канваса."""
        self._current_canvas = canvas
        self._current_object = None
        self._hide_all()

        if canvas is None:
            self.title_label.setText("Свойства")
            return

        self.canvas_section.load(canvas)
        self.canvas_section.setVisible(True)
        self.title_label.setText(f"Канвас: {canvas.name}")

    def set_object(self, obj: BaseObject | None):
        """Показывает свойства объекта."""
        self._current_object = obj
        self._hide_all()

        if obj is None:
            self.title_label.setText(
                f"Канвас: {self._current_canvas.name}" if self._current_canvas else "Свойства"
            )
            return

        self.request_objects_list.emit()

        is_text = isinstance(obj, TextObject)

        # Имя
        self._name_group.setVisible(True)
        self._name_edit.blockSignals(True)
        self._name_edit.setText(obj.name)
        self._name_edit.blockSignals(False)

        # Секции
        self.transform.setVisible(True)
        self.transform.load(obj)

        self.appearance.setVisible(True)
        self.appearance.load(obj)

        self.stroke.setVisible(True)
        self.stroke.load(obj)

        self.text_section.setVisible(is_text)
        if is_text:
            self.text_section.load(obj)

        self.title_label.setText(f"Объект: {obj.name}")

    def set_objects_list(self, objects: list[BaseObject]):
        """Передаёт список объектов в TransformSection для выбора родителя."""
        self.transform.set_objects_list(objects)

    def update_object_position(self, obj: BaseObject):
        """Обновляет только координаты в реальном времени при перетаскивании."""
        if self._current_object and self._current_object.id == obj.id:
            self.transform.update_position(obj)

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------
    def update_object_geometry(self, obj: BaseObject):
        """Обновляет позицию и размеры в реальном времени (при resize)."""
        if self._current_object and self._current_object.id == obj.id:
            t = self.transform
            t._blocking = True
            t.x_spin.setValue(obj.x)
            t.y_spin.setValue(obj.y)
            t.width_spin.setValue(obj.width)
            t.height_spin.setValue(obj.height)
            gx, gy = obj.get_global_position()
            t.global_label.setText(f"{gx:.1f}, {gy:.1f}")
            t._blocking = False
    def _hide_all(self):
        self._name_group.setVisible(False)
        self.canvas_section.setVisible(False)
        for s in (self.transform, self.appearance, self.stroke, self.text_section):
            s.setVisible(False)

    def _on_name_changed(self, text: str):
        if self._current_object:
            self._current_object.name = text
            self.object_changed.emit(self._current_object)
