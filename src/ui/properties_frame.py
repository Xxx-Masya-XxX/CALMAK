"""Панель свойств объектов."""

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QCheckBox, QVBoxLayout, QLabel, QGroupBox, QFontComboBox,
    QScrollArea, QPushButton, QColorDialog, QFileDialog, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont

from ..models import BaseObject, Canvas, TextObject
from .text_editor_dialog import TextEditorDialog


class PropertiesPanel(QWidget):
    """Панель свойств выбранного объекта или канваса."""

    canvas_changed = Signal(Canvas)
    object_changed = Signal(BaseObject)
    request_objects_list = Signal()  # Сигнал для запроса списка объектов

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_canvas: Canvas | None = None
        self._current_object: BaseObject | None = None
        self._blocking_signals = False
        self._objects_list: list[BaseObject] = []  # Список объектов для выбора родителя
        
        # Основной layout с прокруткой
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаём скролл-область
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Виджет для содержимого
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Заголовок
        self.title_label = QLabel("Свойства")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)
        
        # Группа свойств канваса
        self.canvas_group = QGroupBox("Канвас")
        canvas_layout = QFormLayout(self.canvas_group)
        
        # Имя канваса
        self.canvas_name_edit = QLineEdit()
        self.canvas_name_edit.setPlaceholderText("Имя канваса")
        self.canvas_name_edit.textChanged.connect(self._on_canvas_name_changed)
        canvas_layout.addRow("Имя:", self.canvas_name_edit)
        
        # Ширина канваса
        self.canvas_width_spin = QDoubleSpinBox()
        self.canvas_width_spin.setRange(100, 10000)
        self.canvas_width_spin.setDecimals(0)
        self.canvas_width_spin.setSuffix(" px")
        self.canvas_width_spin.valueChanged.connect(self._on_canvas_size_changed)
        canvas_layout.addRow("Ширина:", self.canvas_width_spin)
        
        # Высота канваса
        self.canvas_height_spin = QDoubleSpinBox()
        self.canvas_height_spin.setRange(100, 10000)
        self.canvas_height_spin.setDecimals(0)
        self.canvas_height_spin.setSuffix(" px")
        self.canvas_height_spin.valueChanged.connect(self._on_canvas_size_changed)
        canvas_layout.addRow("Высота:", self.canvas_height_spin)
        
        # Цвет фона
        self.canvas_color_edit = QLineEdit()
        self.canvas_color_edit.setPlaceholderText("#FFFFFF")
        self.canvas_color_edit.setReadOnly(True)
        canvas_layout.addRow("Фон:", self.canvas_color_edit)
        
        self.canvas_color_btn = QPushButton("Выбрать цвет")
        self.canvas_color_btn.clicked.connect(self._on_canvas_color_pick)
        canvas_layout.addRow("", self.canvas_color_btn)
        
        layout.addWidget(self.canvas_group)
        self.canvas_group.setVisible(False)
        
        # Группа свойств базового объекта
        self.object_group = QGroupBox("Объект")
        object_layout = QFormLayout(self.object_group)

        # Имя объекта
        self.object_name_edit = QLineEdit()
        self.object_name_edit.setPlaceholderText("Имя объекта")
        self.object_name_edit.textChanged.connect(self._on_object_name_changed)
        object_layout.addRow("Имя:", self.object_name_edit)

        # Блокировка объекта
        self.locked_check = QCheckBox()
        self.locked_check.stateChanged.connect(self._on_locked_changed)
        object_layout.addRow("Заблокирован:", self.locked_check)

        # Позиция X (локальная) с иконкой замка
        x_layout = QHBoxLayout()
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.setDecimals(1)
        self.x_spin.valueChanged.connect(self._on_position_changed)
        self.x_lock_label = QLabel("")
        self.x_lock_label.setStyleSheet("color: #888; font-size: 14px;")
        x_layout.addWidget(self.x_spin)
        x_layout.addWidget(self.x_lock_label)
        object_layout.addRow("X (локальн.):", x_layout)

        # Позиция Y (локальная) с иконкой замка
        y_layout = QHBoxLayout()
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.setDecimals(1)
        self.y_spin.valueChanged.connect(self._on_position_changed)
        self.y_lock_label = QLabel("")
        self.y_lock_label.setStyleSheet("color: #888; font-size: 14px;")
        y_layout.addWidget(self.y_spin)
        y_layout.addWidget(self.y_lock_label)
        object_layout.addRow("Y (локальн.):", y_layout)

        # Глобальные координаты (только для чтения)
        self.global_coords_label = QLabel("")
        self.global_coords_label.setStyleSheet("color: #666; font-size: 11px;")
        object_layout.addRow("Глобальные:", self.global_coords_label)

        # Родитель объекта
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("Нет", None)
        self.parent_combo.currentIndexChanged.connect(self._on_parent_changed)
        object_layout.addRow("Родитель:", self.parent_combo)

        # Ширина
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setDecimals(1)
        self.width_spin.valueChanged.connect(self._on_size_changed)
        object_layout.addRow("Ширина:", self.width_spin)
        
        # Высота
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setDecimals(1)
        self.height_spin.valueChanged.connect(self._on_size_changed)
        object_layout.addRow("Высота:", self.height_spin)

        # Поворот
        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-360, 360)
        self.rotation_spin.setDecimals(1)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.valueChanged.connect(self._on_rotation_changed)
        object_layout.addRow("Поворот:", self.rotation_spin)

        # Цвет (для BaseObject)
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#CCCCCC")
        self.color_edit.setReadOnly(True)
        object_layout.addRow("Цвет:", self.color_edit)
        
        self.color_btn = QPushButton("Выбрать цвет")
        self.color_btn.clicked.connect(self._on_color_pick)
        object_layout.addRow("", self.color_btn)
        
        # Видимость
        self.visible_check = QCheckBox()
        self.visible_check.stateChanged.connect(self._on_visibility_changed)
        object_layout.addRow("Видимый:", self.visible_check)
        
        # Тип фигуры
        self.shape_type_combo = QComboBox()
        self.shape_type_combo.addItems(["Прямоугольник", "Эллипс", "Треугольник"])
        self.shape_type_combo.currentIndexChanged.connect(self._on_shape_type_changed)
        object_layout.addRow("Фигура:", self.shape_type_combo)
        
        layout.addWidget(self.object_group)
        self.object_group.setVisible(False)
        
        # Группа свойств изображения
        self.image_group = QGroupBox("Изображение")
        image_layout = QFormLayout(self.image_group)
        
        # Путь к изображению
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("Путь к изображению")
        self.image_path_edit.setReadOnly(True)
        image_layout.addRow("Путь:", self.image_path_edit)
        
        self.image_browse_btn = QPushButton("Обзор...")
        self.image_browse_btn.clicked.connect(self._on_image_browse)
        image_layout.addRow("", self.image_browse_btn)
        
        # Заполнение изображением
        self.image_fill_check = QCheckBox()
        self.image_fill_check.stateChanged.connect(self._on_image_fill_changed)
        image_layout.addRow("Заполнять:", self.image_fill_check)
        
        layout.addWidget(self.image_group)
        self.image_group.setVisible(False)
        
        # Группа свойств текста
        self.text_group = QGroupBox("Текст")
        text_layout = QFormLayout(self.text_group)
        
        # Кнопка открытия редактора текста
        self.edit_text_btn = QPushButton("Редактировать текст...")
        self.edit_text_btn.clicked.connect(self._on_edit_text)
        text_layout.addRow(self.edit_text_btn)
        
        # Предпросмотр текста
        self.text_preview = QLineEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setPlaceholderText("Предпросмотр")
        text_layout.addRow("Предпросмотр:", self.text_preview)
        
        # Шрифт
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        text_layout.addRow("Шрифт:", self.font_combo)
        
        # Размер шрифта
        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(1, 200)
        self.font_size_spin.setDecimals(0)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        text_layout.addRow("Размер:", self.font_size_spin)
        
        # Жирный
        self.bold_check = QCheckBox()
        self.bold_check.stateChanged.connect(self._on_font_style_changed)
        text_layout.addRow("Жирный:", self.bold_check)
        
        # Курсив
        self.italic_check = QCheckBox()
        self.italic_check.stateChanged.connect(self._on_font_style_changed)
        text_layout.addRow("Курсив:", self.italic_check)
        
        # Подчёркнутый
        self.underline_check = QCheckBox()
        self.underline_check.stateChanged.connect(self._on_font_style_changed)
        text_layout.addRow("Подчёркнутый:", self.underline_check)
        
        # Цвет текста
        self.text_color_edit = QLineEdit()
        self.text_color_edit.setPlaceholderText("#000000")
        self.text_color_edit.setReadOnly(True)
        text_layout.addRow("Цвет текста:", self.text_color_edit)
        
        self.text_color_btn = QPushButton("Выбрать цвет")
        self.text_color_btn.clicked.connect(self._on_text_color_pick)
        text_layout.addRow("", self.text_color_btn)
        
        # Выравнивание по горизонтали
        self.text_align_h_combo = QComboBox()
        self.text_align_h_combo.addItems(["Слева", "По центру", "Справа"])
        self.text_align_h_combo.currentIndexChanged.connect(self._on_text_align_changed)
        text_layout.addRow("Выравнивание (гор.):", self.text_align_h_combo)
        
        # Выравнивание по вертикали
        self.text_align_v_combo = QComboBox()
        self.text_align_v_combo.addItems(["Сверху", "По центру", "Снизу"])
        self.text_align_v_combo.currentIndexChanged.connect(self._on_text_align_changed)
        text_layout.addRow("Выравнивание (верт.):", self.text_align_v_combo)
        
        layout.addWidget(self.text_group)
        self.text_group.setVisible(False)
        
        # Группа обводки
        self.stroke_group = QGroupBox("Обводка")
        stroke_layout = QFormLayout(self.stroke_group)
        
        # Включить обводку
        self.stroke_enabled_check = QCheckBox()
        self.stroke_enabled_check.stateChanged.connect(self._on_stroke_changed)
        stroke_layout.addRow("Включена:", self.stroke_enabled_check)
        
        # Цвет обводки
        self.stroke_color_edit = QLineEdit()
        self.stroke_color_edit.setPlaceholderText("#000000")
        self.stroke_color_edit.setReadOnly(True)
        stroke_layout.addRow("Цвет:", self.stroke_color_edit)
        
        self.stroke_color_btn = QPushButton("Выбрать цвет")
        self.stroke_color_btn.clicked.connect(self._on_stroke_color_pick)
        stroke_layout.addRow("", self.stroke_color_btn)
        
        # Толщина обводки
        self.stroke_width_spin = QDoubleSpinBox()
        self.stroke_width_spin.setRange(0, 20)
        self.stroke_width_spin.setDecimals(1)
        self.stroke_width_spin.valueChanged.connect(self._on_stroke_width_changed)
        stroke_layout.addRow("Толщина:", self.stroke_width_spin)
        
        layout.addWidget(self.stroke_group)
        self.stroke_group.setVisible(False)
        
        layout.addStretch()
        
        # Устанавливаем контент в скролл
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
    
    def update_object_position(self, obj: BaseObject):
        """Обновляет только позицию объекта (для реального времени)."""
        if self._current_object and self._current_object.id == obj.id:
            self._blocking_signals = True
            self.x_spin.setValue(obj.x)
            self.y_spin.setValue(obj.y)
            self.rotation_spin.setValue(obj.rotation)
            # Обновляем метку глобальных координат
            global_x, global_y = obj.get_global_position()
            self.global_coords_label.setText(f"{global_x:.1f}, {global_y:.1f}")
            self._blocking_signals = False
    
    def set_canvas(self, canvas: Canvas | None):
        """Устанавливает текущий канвас для редактирования."""
        self._current_canvas = canvas
        self._current_object = None
        
        if canvas is None:
            self._block_canvas_signals(True)
            self.canvas_name_edit.clear()
            self.canvas_width_spin.setValue(0)
            self.canvas_height_spin.setValue(0)
            self.canvas_color_edit.clear()
            self._block_canvas_signals(False)
            self.canvas_group.setVisible(False)
            self.object_group.setVisible(False)
            self.text_group.setVisible(False)
            self.stroke_group.setVisible(False)
            self.image_group.setVisible(False)
            self.title_label.setText("Свойства")
            return
        
        self._block_canvas_signals(True)
        self.canvas_name_edit.setText(canvas.name)
        self.canvas_width_spin.setValue(canvas.width)
        self.canvas_height_spin.setValue(canvas.height)
        self.canvas_color_edit.setText(canvas.background_color)
        self._block_canvas_signals(False)
        
        self.canvas_group.setVisible(True)
        self.object_group.setVisible(False)
        self.text_group.setVisible(False)
        self.stroke_group.setVisible(False)
        self.image_group.setVisible(False)
        self.title_label.setText(f"Канвас: {canvas.name}")
    
    def set_object(self, obj: BaseObject | None):
        """Устанавливает текущий объект для редактирования."""
        self._current_object = obj

        if obj is None:
            self._block_object_signals(True)
            self._clear_object_fields()
            self._block_object_signals(False)
            self.object_group.setVisible(False)
            self.text_group.setVisible(False)
            self.stroke_group.setVisible(False)
            self.image_group.setVisible(False)
            if self._current_canvas:
                self.title_label.setText(f"Канвас: {self._current_canvas.name}")
            else:
                self.title_label.setText("Свойства")
            return

        # Запрашиваем список объектов для обновления родителя
        self.request_objects_list.emit()
        
        self._block_object_signals(True)

        # Общие поля
        self.object_name_edit.setText(obj.name)
        self.x_spin.setValue(obj.x)
        self.y_spin.setValue(obj.y)
        self.locked_check.setChecked(obj.locked)

        # Обновляем метку глобальных координат
        global_x, global_y = obj.get_global_position()
        self.global_coords_label.setText(f"{global_x:.1f}, {global_y:.1f}")

        # Обновляем иконки замков у полей координат
        self._update_lock_icons()

        # Обновляем список родителей
        self._update_parent_combo(obj)

        self.width_spin.setValue(obj.width)
        self.height_spin.setValue(obj.height)
        self.rotation_spin.setValue(obj.rotation)
        self.color_edit.setText(obj.color)
        self.visible_check.setChecked(obj.visible)

        # Тип фигуры
        shape_index = {"rect": 0, "ellipse": 1, "triangle": 2}.get(obj.shape_type, 0)
        self.shape_type_combo.setCurrentIndex(shape_index)

        # Изображение
        self.image_path_edit.setText(obj.image_path or "")
        self.image_fill_check.setChecked(obj.image_fill)

        self.object_group.setVisible(True)
        self.image_group.setVisible(True)

        # Обводка (для всех объектов)
        self.stroke_enabled_check.setChecked(obj.stroke_enabled)
        self.stroke_color_edit.setText(obj.stroke_color)
        self.stroke_width_spin.setValue(obj.stroke_width)
        self.stroke_group.setVisible(True)

        # Поля текста
        if isinstance(obj, TextObject):
            self.text_preview.setText(obj.text[:50] + "..." if len(obj.text) > 50 else obj.text)
            self.font_combo.setCurrentFont(QFont(obj.font_family))
            self.font_size_spin.setValue(obj.font_size)
            self.bold_check.setChecked(obj.font_bold)
            self.italic_check.setChecked(obj.font_italic)
            self.underline_check.setChecked(obj.font_underline)
            self.text_color_edit.setText(obj.text_color)

            # Выравнивание
            align_h_map = {"left": 0, "center": 1, "right": 2}
            align_v_map = {"top": 0, "center": 1, "bottom": 2}
            self.text_align_h_combo.setCurrentIndex(align_h_map.get(obj.text_align_h, 0))
            self.text_align_v_combo.setCurrentIndex(align_v_map.get(obj.text_align_v, 0))

            self.text_group.setVisible(True)
        else:
            self.text_group.setVisible(False)

        self._block_object_signals(False)
        self.title_label.setText(f"Объект: {obj.name}")

    def set_objects_list(self, objects: list[BaseObject]):
        """Устанавливает список объектов для выбора родителя."""
        self._objects_list = objects
        # Обновляем комбобокс если объект выбран
        if self._current_object:
            self._update_parent_combo(self._current_object)

    def _update_lock_icons(self):
        """Обновляет иконки замков у полей координат."""
        if self._current_object and self._current_object.locked:
            self.x_lock_label.setText("🔒")
            self.y_lock_label.setText("🔒")
            self.x_spin.setEnabled(False)
            self.y_spin.setEnabled(False)
        else:
            self.x_lock_label.setText("")
            self.y_lock_label.setText("")
            self.x_spin.setEnabled(True)
            self.y_spin.setEnabled(True)

    def _update_parent_combo(self, obj: BaseObject):
        """Обновляет список родителей в комбобоксе."""
        self._blocking_signals = True
        self.parent_combo.clear()
        self.parent_combo.addItem("Нет", None)
        
        # Добавляем все объекты кроме текущего и его потомков
        for o in self._objects_list:
            if o.id != obj.id and o.id != obj.parent_id:
                # Проверяем, не является ли объект потомком текущего
                if not self._is_descendant(o, obj):
                    display_name = f"{o.name}"
                    self.parent_combo.addItem(display_name, o.id)
        
        # Выбираем текущего родителя
        for i in range(self.parent_combo.count()):
            parent_id = self.parent_combo.itemData(i)
            if parent_id == obj.parent_id:
                self.parent_combo.setCurrentIndex(i)
                break
        
        self._blocking_signals = False

    def _is_descendant(self, potential_child: BaseObject, potential_parent: BaseObject) -> bool:
        """Проверяет является ли potential_child потомком potential_parent."""
        if potential_child.parent_id is None:
            return False
        if potential_child.parent_id == potential_parent.id:
            return True
        # Рекурсивно проверяем родителя
        for o in self._objects_list:
            if o.id == potential_child.parent_id:
                return self._is_descendant(o, potential_parent)
        return False

    def _on_parent_changed(self, index: int):
        """Обработчик изменения родителя."""
        if self._blocking_signals or not self._current_object:
            return
        
        parent_id = self.parent_combo.itemData(index)
        self._current_object.parent_id = parent_id
        
        # Находим объект родителя и устанавливаем ссылку
        parent_obj = None
        if parent_id:
            for o in self._objects_list:
                if o.id == parent_id:
                    parent_obj = o
                    break
        self._current_object._parent = parent_obj
        
        self._emit_object_changed()

    def _on_locked_changed(self, state: int):
        """Обработчик изменения блокировки объекта."""
        if self._current_object:
            self._current_object.locked = state == 2  # Qt.Checked
            self._update_lock_icons()
            self._emit_object_changed()

    def _clear_object_fields(self):
        """Очищает поля объекта."""
        self.object_name_edit.clear()
        self.x_spin.setValue(0)
        self.y_spin.setValue(0)
        self.locked_check.setChecked(False)
        self.global_coords_label.setText("")
        self.width_spin.setValue(0)
        self.height_spin.setValue(0)
        self.rotation_spin.setValue(0)
        self.color_edit.clear()
        self.visible_check.setChecked(False)
        self.shape_type_combo.setCurrentIndex(0)

        self.text_preview.clear()
        self.font_size_spin.setValue(16)
        self.text_color_edit.clear()
        self.bold_check.setChecked(False)
        self.italic_check.setChecked(False)
        self.underline_check.setChecked(False)

        self.stroke_enabled_check.setChecked(False)
        self.stroke_color_edit.clear()
        self.stroke_width_spin.setValue(1)

        self.image_path_edit.clear()
        self.image_fill_check.setChecked(False)

        self.text_align_h_combo.setCurrentIndex(0)
        self.text_align_v_combo.setCurrentIndex(0)

    def _block_canvas_signals(self, block: bool):
        """Блокирует сигналы канваса."""
        self._blocking_signals = block
        self.canvas_name_edit.blockSignals(block)
        self.canvas_width_spin.blockSignals(block)
        self.canvas_height_spin.blockSignals(block)

    def _block_object_signals(self, block: bool):
        """Блокирует сигналы объекта."""
        self._blocking_signals = block
        self.object_name_edit.blockSignals(block)
        self.x_spin.blockSignals(block)
        self.y_spin.blockSignals(block)
        self.locked_check.blockSignals(block)
        self.parent_combo.blockSignals(block)
        self.width_spin.blockSignals(block)
        self.height_spin.blockSignals(block)
        self.rotation_spin.blockSignals(block)
        self.visible_check.blockSignals(block)
        self.shape_type_combo.blockSignals(block)

        self.text_preview.blockSignals(block)
        self.font_combo.blockSignals(block)
        self.font_size_spin.blockSignals(block)
        self.bold_check.blockSignals(block)
        self.italic_check.blockSignals(block)
        self.underline_check.blockSignals(block)

        self.stroke_enabled_check.blockSignals(block)
        self.stroke_width_spin.blockSignals(block)

        self.image_path_edit.blockSignals(block)
        self.image_fill_check.blockSignals(block)

        self.text_align_h_combo.blockSignals(block)
        self.text_align_v_combo.blockSignals(block)

    def _emit_canvas_changed(self):
        """Испускает сигнал об изменении канваса."""
        if not self._blocking_signals and self._current_canvas:
            self.canvas_changed.emit(self._current_canvas)

    def _emit_object_changed(self):
        """Испускает сигнал об изменении объекта."""
        if not self._blocking_signals and self._current_object:
            self.object_changed.emit(self._current_object)

    # Обработчики канваса
    def _on_canvas_name_changed(self, text: str):
        """Обработчик изменения имени канваса."""
        if self._current_canvas:
            self._current_canvas.name = text
            self._emit_canvas_changed()

    def _on_canvas_size_changed(self):
        """Обработчик изменения размера канваса."""
        if self._current_canvas:
            self._current_canvas.width = self.canvas_width_spin.value()
            self._current_canvas.height = self.canvas_height_spin.value()
            self._emit_canvas_changed()

    def _on_canvas_color_pick(self):
        """Открывает диалог выбора цвета фона."""
        if self._current_canvas:
            current_color = QColor(self._current_canvas.background_color)
            new_color = QColorDialog.getColor(current_color, self, "Выберите цвет фона")
            if new_color.isValid():
                self._current_canvas.background_color = new_color.name()
                self.canvas_color_edit.setText(new_color.name())
                self._emit_canvas_changed()

    # Обработчики объекта
    def _on_object_name_changed(self, text: str):
        """Обработчик изменения имени объекта."""
        if self._current_object:
            self._current_object.name = text
            self._emit_object_changed()

    def _on_position_changed(self):
        """Обработчик изменения позиции."""
        if self._current_object:
            self._current_object.x = self.x_spin.value()
            self._current_object.y = self.y_spin.value()
            # Обновляем метку глобальных координат
            global_x, global_y = self._current_object.get_global_position()
            self.global_coords_label.setText(f"{global_x:.1f}, {global_y:.1f}")
            self._emit_object_changed()

    def _on_size_changed(self):
        """Обработчик изменения размера."""
        if self._current_object:
            self._current_object.width = self.width_spin.value()
            self._current_object.height = self.height_spin.value()
            self._emit_object_changed()

    def _on_rotation_changed(self):
        """Обработчик изменения поворота."""
        if self._current_object:
            self._current_object.rotation = self.rotation_spin.value()
            self._emit_object_changed()

    def _on_visibility_changed(self, state: int):
        """Обработчик изменения видимости."""
        if self._current_object:
            self._current_object.visible = state == 2  # Qt.Checked
            self._emit_object_changed()

    # Обработчики цвета
    def _on_color_pick(self):
        """Открывает диалог выбора цвета объекта."""
        if self._current_object:
            current_color = QColor(self._current_object.color)
            new_color = QColorDialog.getColor(current_color, self, "Выберите цвет")
            if new_color.isValid():
                self._current_object.color = new_color.name()
                self.color_edit.setText(new_color.name())
                self._emit_object_changed()

    def _on_text_color_pick(self):
        """Открывает диалог выбора цвета текста."""
        if isinstance(self._current_object, TextObject):
            current_color = QColor(self._current_object.text_color)
            new_color = QColorDialog.getColor(current_color, self, "Выберите цвет текста")
            if new_color.isValid():
                self._current_object.text_color = new_color.name()
                self.text_color_edit.setText(new_color.name())
                self._emit_object_changed()

    def _on_stroke_color_pick(self):
        """Открывает диалог выбора цвета обводки."""
        if self._current_object:
            current_color = QColor(self._current_object.stroke_color)
            new_color = QColorDialog.getColor(current_color, self, "Выберите цвет обводки")
            if new_color.isValid():
                self._current_object.stroke_color = new_color.name()
                self.stroke_color_edit.setText(new_color.name())
                self._emit_object_changed()

    # Обработчики текста
    def _on_edit_text(self):
        """Открывает диалог редактирования текста."""
        if isinstance(self._current_object, TextObject):
            dialog = TextEditorDialog(self._current_object, self)
            if dialog.exec():
                # Обновляем предпросмотр
                self.text_preview.setText(
                    self._current_object.text[:50] + "..." 
                    if len(self._current_object.text) > 50 
                    else self._current_object.text
                )
                self._emit_object_changed()

    def _on_font_changed(self, font):
        """Обработчик изменения шрифта."""
        if isinstance(self._current_object, TextObject):
            self._current_object.font_family = font.family()
            self._emit_object_changed()

    def _on_font_size_changed(self):
        """Обработчик изменения размера шрифта."""
        if isinstance(self._current_object, TextObject):
            self._current_object.font_size = int(self.font_size_spin.value())
            self._emit_object_changed()

    def _on_font_style_changed(self):
        """Обработчик изменения стиля шрифта."""
        if isinstance(self._current_object, TextObject):
            self._current_object.font_bold = self.bold_check.isChecked()
            self._current_object.font_italic = self.italic_check.isChecked()
            self._current_object.font_underline = self.underline_check.isChecked()
            self._emit_object_changed()

    def _on_text_align_changed(self):
        """Обработчик изменения выравнивания текста."""
        if isinstance(self._current_object, TextObject):
            align_h_map = {0: "left", 1: "center", 2: "right"}
            align_v_map = {0: "top", 1: "center", 2: "bottom"}
            self._current_object.text_align_h = align_h_map.get(self.text_align_h_combo.currentIndex(), "left")
            self._current_object.text_align_v = align_v_map.get(self.text_align_v_combo.currentIndex(), "top")
            self._emit_object_changed()

    # Обработчики обводки
    def _on_stroke_changed(self):
        """Обработчик изменения обводки."""
        if self._current_object:
            self._current_object.stroke_enabled = self.stroke_enabled_check.isChecked()
            self._emit_object_changed()

    def _on_stroke_width_changed(self):
        """Обработчик изменения толщины обводки."""
        if self._current_object:
            self._current_object.stroke_width = self.stroke_width_spin.value()
            self._emit_object_changed()

    # Обработчики фигуры
    def _on_shape_type_changed(self, index: int):
        """Обработчик изменения типа фигуры."""
        if self._current_object:
            shape_types = {0: "rect", 1: "ellipse", 2: "triangle"}
            self._current_object.shape_type = shape_types.get(index, "rect")
            self._emit_object_changed()

    # Обработчики изображения
    def _on_image_browse(self):
        """Открывает диалог выбора изображения."""
        if self._current_object:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите изображение",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if file_path:
                self._current_object.image_path = file_path
                self.image_path_edit.setText(file_path)
                self._emit_object_changed()

    def _on_image_fill_changed(self, state: int):
        """Обработчик изменения заполнения изображением."""
        if self._current_object:
            self._current_object.image_fill = state == 2  # Qt.Checked
            self._emit_object_changed()