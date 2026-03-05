"""Панель свойств для редактирования параметров выбранного элемента."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QColorDialog, QPushButton,
    QComboBox, QFrame, QScrollArea
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.elements import CanvasElement


class PropertiesFrame(QWidget):
    """Панель свойств для редактирования параметров элемента."""
    
    # Сигнал об изменении свойства
    property_changed = Signal(str, str, object)  # element_id, property_name, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self._current_element = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Заголовок
        title = QLabel("Свойства")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Scroll area для свойств
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QFormLayout(self.content_widget)
        self.content_layout.setSpacing(6)
        self.content_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        # Общие свойства
        self._create_common_properties()
        
        # Специфичные свойства (заполняются динамически)
        self.specific_layout = QVBoxLayout()
        self.content_layout.addRow(self.specific_layout)
        
        self._clear_specific_properties()
    
    def _create_common_properties(self):
        """Создать общие свойства для всех элементов."""
        # Название
        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self._on_name_changed)
        self.content_layout.addRow("Название:", self.name_input)
        
        # Позиция X
        self.x_input = QDoubleSpinBox()
        self.x_input.setRange(-10000, 10000)
        self.x_input.setDecimals(1)
        self.x_input.valueChanged.connect(self._on_x_changed)
        self.content_layout.addRow("Позиция X:", self.x_input)
        
        # Позиция Y
        self.y_input = QDoubleSpinBox()
        self.y_input.setRange(-10000, 10000)
        self.y_input.setDecimals(1)
        self.y_input.valueChanged.connect(self._on_y_changed)
        self.content_layout.addRow("Позиция Y:", self.y_input)
        
        # Ширина
        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setDecimals(1)
        self.width_input.valueChanged.connect(self._on_width_changed)
        self.content_layout.addRow("Ширина:", self.width_input)
        
        # Высота
        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setDecimals(1)
        self.height_input.valueChanged.connect(self._on_height_changed)
        self.content_layout.addRow("Высота:", self.height_input)
        
        # Видимость
        self.visible_input = QCheckBox()
        self.visible_input.stateChanged.connect(self._on_visible_changed)
        self.content_layout.addRow("Видимый:", self.visible_input)
        
        # Заблокирован
        self.locked_input = QCheckBox()
        self.locked_input.stateChanged.connect(self._on_locked_changed)
        self.content_layout.addRow("Заблокирован:", self.locked_input)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.content_layout.addRow(line)
    
    def _clear_specific_properties(self):
        """Очистить специфичные свойства."""
        while self.specific_layout.count():
            item = self.specific_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _add_specific_property(self, label: str, widget: QWidget):
        """Добавить специфичное свойство."""
        self.specific_layout.addWidget(QLabel(label))
        self.specific_layout.addWidget(widget)
    
    def set_element(self, element: "CanvasElement | None") -> None:
        """Установить элемент для редактирования."""
        self._current_element = element
        
        if not element:
            self._disable_inputs()
            return
        
        self._enable_inputs()
        self._populate_properties()
    
    def _disable_inputs(self):
        """Отключить все поля ввода."""
        self.name_input.setEnabled(False)
        self.x_input.setEnabled(False)
        self.y_input.setEnabled(False)
        self.width_input.setEnabled(False)
        self.height_input.setEnabled(False)
        self.visible_input.setEnabled(False)
        self.locked_input.setEnabled(False)
        self._clear_specific_properties()
    
    def _enable_inputs(self):
        """Включить все поля ввода."""
        self.name_input.setEnabled(True)
        self.x_input.setEnabled(True)
        self.y_input.setEnabled(True)
        self.width_input.setEnabled(True)
        self.height_input.setEnabled(True)
        self.visible_input.setEnabled(True)
        self.locked_input.setEnabled(True)
    
    def _populate_properties(self):
        """Заполнить поля свойствами текущего элемента."""
        if not self._current_element:
            return
        
        element = self._current_element
        
        # Общие свойства
        self.name_input.blockSignals(True)
        self.name_input.setText(element.name)
        self.name_input.blockSignals(False)
        
        self.x_input.blockSignals(True)
        self.x_input.setValue(element.x)
        self.x_input.blockSignals(False)
        
        self.y_input.blockSignals(True)
        self.y_input.setValue(element.y)
        self.y_input.blockSignals(False)
        
        self.width_input.blockSignals(True)
        self.width_input.setValue(element.width)
        self.width_input.blockSignals(False)
        
        self.height_input.blockSignals(True)
        self.height_input.setValue(element.height)
        self.height_input.blockSignals(False)
        
        self.visible_input.blockSignals(True)
        self.visible_input.setChecked(element.visible)
        self.visible_input.blockSignals(False)
        
        self.locked_input.blockSignals(True)
        self.locked_input.setChecked(element.locked)
        self.locked_input.blockSignals(False)
        
        # Специфичные свойства
        self._populate_specific_properties()
    
    def _populate_specific_properties(self):
        """Заполнить специфичные свойства в зависимости от типа элемента."""
        self._clear_specific_properties()
        
        if not self._current_element:
            return
        
        from ..models.elements import ImageElement, TextElement, ShapeElement
        
        element = self._current_element
        
        if isinstance(element, ImageElement):
            self._create_image_properties(element)
        elif isinstance(element, TextElement):
            self._create_text_properties(element)
        elif isinstance(element, ShapeElement):
            self._create_shape_properties(element)
    
    def _create_image_properties(self, element: ImageElement):
        """Создать свойства для изображения."""
        # Путь к изображению
        self.image_path_input = QLineEdit(element.image_path)
        self.image_path_input.textChanged.connect(self._on_image_path_changed)
        self.specific_layout.addWidget(QLabel("Путь к файлу:"))
        self.specific_layout.addWidget(self.image_path_input)
        
        # Прозрачность
        self.opacity_input = QDoubleSpinBox()
        self.opacity_input.setRange(0.0, 1.0)
        self.opacity_input.setDecimals(2)
        self.opacity_input.setSingleStep(0.1)
        self.opacity_input.setValue(element.opacity)
        self.opacity_input.valueChanged.connect(self._on_opacity_changed)
        self.specific_layout.addWidget(QLabel("Прозрачность:"))
        self.specific_layout.addWidget(self.opacity_input)
    
    def _create_text_properties(self, element: TextElement):
        """Создать свойства для текста."""
        # Текст
        self.text_input = QLineEdit(element.text)
        self.text_input.textChanged.connect(self._on_text_changed)
        self.specific_layout.addWidget(QLabel("Текст:"))
        self.specific_layout.addWidget(self.text_input)
        
        # Размер шрифта
        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(8, 200)
        self.font_size_input.setValue(element.font_size)
        self.font_size_input.valueChanged.connect(self._on_font_size_changed)
        self.specific_layout.addWidget(QLabel("Размер шрифта:"))
        self.specific_layout.addWidget(self.font_size_input)
        
        # Цвет текста
        self.color_btn = QPushButton()
        self.color_btn.setText(element.color)
        self.color_btn.setStyleSheet(f"background-color: {element.color}; color: white;")
        self.color_btn.clicked.connect(self._on_color_clicked)
        self.specific_layout.addWidget(QLabel("Цвет текста:"))
        self.specific_layout.addWidget(self.color_btn)
        
        # Жирный
        self.bold_input = QCheckBox()
        self.bold_input.setChecked(element.bold)
        self.bold_input.stateChanged.connect(self._on_bold_changed)
        self.specific_layout.addWidget(QLabel("Жирный:"))
        self.specific_layout.addWidget(self.bold_input)
        
        # Курсив
        self.italic_input = QCheckBox()
        self.italic_input.setChecked(element.italic)
        self.italic_input.stateChanged.connect(self._on_italic_changed)
        self.specific_layout.addWidget(QLabel("Курсив:"))
        self.specific_layout.addWidget(self.italic_input)
    
    def _create_shape_properties(self, element: ShapeElement):
        """Создать свойства для фигуры."""
        # Тип фигуры
        self.shape_type_input = QComboBox()
        self.shape_type_input.addItems(["rectangle", "ellipse", "line"])
        self.shape_type_input.setCurrentText(element.shape_type)
        self.shape_type_input.currentTextChanged.connect(self._on_shape_type_changed)
        self.specific_layout.addWidget(QLabel("Тип фигуры:"))
        self.specific_layout.addWidget(self.shape_type_input)
        
        # Цвет заполнения
        self.fill_color_btn = QPushButton()
        self.fill_color_btn.setText(element.fill_color)
        self.fill_color_btn.setStyleSheet(f"background-color: {element.fill_color};")
        self.fill_color_btn.clicked.connect(lambda: self._on_fill_color_clicked())
        self.specific_layout.addWidget(QLabel("Цвет заполнения:"))
        self.specific_layout.addWidget(self.fill_color_btn)
        
        # Цвет обводки
        self.stroke_color_btn = QPushButton()
        self.stroke_color_btn.setText(element.stroke_color)
        self.stroke_color_btn.setStyleSheet(f"background-color: {element.stroke_color}; color: white;" if element.stroke_color == "#000000" else "")
        self.stroke_color_btn.clicked.connect(lambda: self._on_stroke_color_clicked())
        self.specific_layout.addWidget(QLabel("Цвет обводки:"))
        self.specific_layout.addWidget(self.stroke_color_btn)
        
        # Толщина обводки
        self.stroke_width_input = QSpinBox()
        self.stroke_width_input.setRange(0, 50)
        self.stroke_width_input.setValue(element.stroke_width)
        self.stroke_width_input.valueChanged.connect(self._on_stroke_width_changed)
        self.specific_layout.addWidget(QLabel("Толщина обводки:"))
        self.specific_layout.addWidget(self.stroke_width_input)
        
        # Прозрачность
        self.opacity_input = QDoubleSpinBox()
        self.opacity_input.setRange(0.0, 1.0)
        self.opacity_input.setDecimals(2)
        self.opacity_input.setSingleStep(0.1)
        self.opacity_input.setValue(element.opacity)
        self.opacity_input.valueChanged.connect(self._on_opacity_changed)
        self.specific_layout.addWidget(QLabel("Прозрачность:"))
        self.specific_layout.addWidget(self.opacity_input)
    
    # Обработчики общих свойств
    def _on_name_changed(self, text: str):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "name", text)
    
    def _on_x_changed(self, value: float):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "x", value)
    
    def _on_y_changed(self, value: float):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "y", value)
    
    def _on_width_changed(self, value: float):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "width", value)
    
    def _on_height_changed(self, value: float):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "height", value)
    
    def _on_visible_changed(self, state: int):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "visible", state == Qt.CheckState.Checked.value)
    
    def _on_locked_changed(self, state: int):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "locked", state == Qt.CheckState.Checked.value)
    
    # Обработчики специфичных свойств
    def _on_image_path_changed(self, text: str):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "image_path", text)
    
    def _on_opacity_changed(self, value: float):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "opacity", value)
    
    def _on_text_changed(self, text: str):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "text", text)
    
    def _on_font_size_changed(self, value: int):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "font_size", value)
    
    def _on_color_clicked(self):
        if self._current_element:
            color = QColorDialog.getColor(QColor(self._current_element.color), self)
            if color.isValid():
                self._current_element.color = color.name()
                self.color_btn.setText(color.name())
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
                self.property_changed.emit(self._current_element.id, "color", color.name())
    
    def _on_bold_changed(self, state: int):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "bold", state == Qt.CheckState.Checked.value)
    
    def _on_italic_changed(self, state: int):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "italic", state == Qt.CheckState.Checked.value)
    
    def _on_shape_type_changed(self, value: str):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "shape_type", value)
    
    def _on_fill_color_clicked(self):
        if self._current_element:
            color = QColorDialog.getColor(QColor(self._current_element.fill_color), self)
            if color.isValid():
                self._current_element.fill_color = color.name()
                self.fill_color_btn.setText(color.name())
                self.fill_color_btn.setStyleSheet(f"background-color: {color.name()};")
                self.property_changed.emit(self._current_element.id, "fill_color", color.name())
    
    def _on_stroke_color_clicked(self):
        if self._current_element:
            color = QColorDialog.getColor(QColor(self._current_element.stroke_color), self)
            if color.isValid():
                self._current_element.stroke_color = color.name()
                self.stroke_color_btn.setText(color.name())
                self.stroke_color_btn.setStyleSheet(f"background-color: {color.name()}; color: white;" if color.name() == "#000000" else "")
                self.property_changed.emit(self._current_element.id, "stroke_color", color.name())
    
    def _on_stroke_width_changed(self, value: int):
        if self._current_element:
            self.property_changed.emit(self._current_element.id, "stroke_width", value)
    
    def refresh(self):
        """Обновить отображение свойств."""
        if self._current_element:
            self._populate_properties()
    
    def update_position_fields(self, x: float, y: float):
        """Обновить поля позиции без полного рефреша."""
        self.x_input.blockSignals(True)
        self.x_input.setValue(x)
        self.x_input.blockSignals(False)
        
        self.y_input.blockSignals(True)
        self.y_input.setValue(y)
        self.y_input.blockSignals(False)
