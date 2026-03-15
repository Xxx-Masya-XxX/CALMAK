"""Панель свойств — строится динамически из obj.get_properties().

Логика определения виджета по значению:
  str, начинающийся с '#' и длиной 7  → ColorButton
  bool                                 → QCheckBox
  int                                  → QSpinBox
  float                                → QDoubleSpinBox
  str (всё остальное)                  → QLineEdit

Специальные ключи с комбо-вариантами задаются в COMBO_OPTIONS ниже.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit, QCheckBox,
    QScrollArea, QWidget, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QGroupBox, QFormLayout, QHBoxLayout,
    QColorDialog, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from ..models import BaseObject, Canvas


# ---------------------------------------------------------------------------
# Ключи, для которых нужен QComboBox, и их варианты
# ---------------------------------------------------------------------------
COMBO_OPTIONS: dict[str, list[str]] = {
    "stroke_style":    ["solid", "dash", "dot", "dash_dot"],
    "stroke_position": ["center", "outside", "inside"],
    "shape_type":      ["rect", "ellipse", "triangle"],
    "text_align_h":    ["left", "center", "right"],
    "text_align_v":    ["top", "middle", "bottom"],
}

# Ограничения для числовых полей: ключ → (min, max, decimals, step)
SPIN_LIMITS: dict[str, tuple] = {
    "x":           (-99999, 99999, 1, 1.0),
    "y":           (-99999, 99999, 1, 1.0),
    "width":       (1,      99999, 1, 1.0),
    "height":      (1,      99999, 1, 1.0),
    "rotation":    (-360,   360,   1, 1.0),
    "font_size":   (1,      500,   1, 1.0),
    "stroke_width":(0.1,    100,   1, 0.5),
    "line_height": (0.5,    5.0,   2, 0.1),
}

# Человекочитаемые названия ключей
LABELS: dict[str, str] = {
    "name":             "Имя",
    "visible":          "Видимый",
    "locked":           "Заблокирован",
    "x":                "X",
    "y":                "Y",
    "width":            "Ширина",
    "height":           "Высота",
    "rotation":         "Поворот (°)",
    "stroke_enabled":   "Включена",
    "stroke_color":     "Цвет",
    "stroke_width":     "Толщина",
    "stroke_style":     "Стиль",
    "stroke_position":  "Позиция",
    "color":            "Цвет заливки",
    "shape_type":       "Тип",
    "text":             "Текст",
    "font_family":      "Шрифт",
    "font_size":        "Размер",
    "font_bold":        "Жирный",
    "font_italic":      "Курсив",
    "font_underline":   "Подчёркнутый",
    "text_color":       "Цвет текста",
    "text_align_h":     "Выравнивание H",
    "text_align_v":     "Выравнивание V",
    "line_height":      "Межстрочный",
    "word_wrap":        "Перенос слов",
    "image_path":       "Путь",
    "image_fill":       "Заполнять",
    "background_color": "Цвет фона",
}


# ---------------------------------------------------------------------------
# ColorButton
# ---------------------------------------------------------------------------

class ColorButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(56, 22)
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self):
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; "
            f"border: 1px solid #777; border-radius: 3px; }}"
            f"QPushButton:hover {{ border: 1px solid #333; }}"
        )

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self._refresh()
            self.color_changed.emit(self._color)

    def get_color(self) -> str:
        return self._color

    def set_color(self, color: str):
        if self._color != color:
            self._color = color
            self._refresh()


# ---------------------------------------------------------------------------
# PropertiesPanel
# ---------------------------------------------------------------------------

class PropertiesPanel(QFrame):
    """Динамическая панель свойств."""

    # Первый аргумент — Canvas или BaseObject
    object_property_changed = Signal(object, str, object)

    LIGHT = """
        QGroupBox {
            font-weight: bold; border: 1px solid #ccc;
            border-radius: 4px; margin-top: 6px; padding-top: 6px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
    """
    DARK = """
        QGroupBox {
            font-weight: bold; border: 1px solid #555; color: #eee;
            border-radius: 4px; margin-top: 6px; padding-top: 6px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        QLabel { color: #ddd; }
        QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox {
            background: #3a3a3a; color: #eee;
            border: 1px solid #555; border-radius: 3px; padding: 2px 4px;
        }
        QCheckBox { color: #ddd; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Canvas или BaseObject
        self._obj: Canvas | BaseObject | None = None
        # Хранит виджеты текущего объекта: key → widget
        self._widgets: dict[str, QWidget] = {}
        # Хранит текущие QGroupBox-ы: group_title → QGroupBox
        self._groups: dict[str, QGroupBox] = {}

        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(260)
        self.setMaximumWidth(400)
        self.setStyleSheet(self.LIGHT)

        self._build_shell()

    def _build_shell(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)

        self._title = QLabel("Свойства объекта")
        self._title.setStyleSheet("font-size: 13px; font-weight: bold;")
        outer.addWidget(self._title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(0, 0, 2, 0)
        self._layout.setSpacing(3)
        self._layout.addStretch()

        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_theme(self, is_dark: bool):
        self.setStyleSheet(self.DARK if is_dark else self.LIGHT)

    def set_object(self, obj: "Canvas | BaseObject | None"):
        """Устанавливает объект (Canvas или BaseObject) и перестраивает UI."""
        self._obj = obj
        self._rebuild()

    def refresh_values(self):
        """Обновляет значения виджетов без перестройки UI.
        Вызывается при движении/resize объекта.
        """
        if self._obj is None:
            return
        props = self._obj.get_properties()
        for _group, fields in props.items():
            for key, val in fields.items():
                w = self._widgets.get(key)
                if w is not None:
                    self._set_value(w, val)

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _rebuild(self):
        # Удаляем старые группы
        for gb in list(self._groups.values()):
            self._layout.removeWidget(gb)
            gb.deleteLater()
        self._groups.clear()
        self._widgets.clear()

        # Убираем stretch
        item = self._layout.takeAt(self._layout.count() - 1)

        if self._obj is None:
            self._title.setText("Свойства объекта")
            self._layout.addStretch()
            return

        self._title.setText(f"Свойства: {self._obj.name}")

        for group_title, fields in self._obj.get_properties().items():
            gb = self._build_group(group_title, fields)
            self._layout.addWidget(gb)
            self._groups[group_title] = gb

        self._layout.addStretch()

    def _build_group(self, title: str, fields: dict) -> QGroupBox:
        gb = QGroupBox(title)
        form = QFormLayout()
        form.setSpacing(4)
        form.setContentsMargins(6, 10, 6, 6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        for key, val in fields.items():
            widget = self._make_widget(key, val)
            self._widgets[key] = widget
            label = LABELS.get(key, key)
            form.addRow(label + ":", widget)

        gb.setLayout(form)
        return gb

    def _make_widget(self, key: str, val) -> QWidget:
        """Создаёт виджет по типу значения."""

        # ComboBox — если ключ в COMBO_OPTIONS
        if key in COMBO_OPTIONS:
            w = QComboBox()
            w.addItems(COMBO_OPTIONS[key])
            if str(val) in COMBO_OPTIONS[key]:
                w.setCurrentText(str(val))
            w.currentTextChanged.connect(lambda v, k=key: self._on_change(k, v))
            return w

        # Color button — строка вида #rrggbb
        if isinstance(val, str) and val.startswith("#") and len(val) in (7, 9):
            w = ColorButton(val)
            w.color_changed.connect(lambda v, k=key: self._on_change(k, v))
            return w

        # Bool → CheckBox
        if isinstance(val, bool):
            w = QCheckBox()
            w.setChecked(val)
            w.toggled.connect(lambda v, k=key: self._on_change(k, v))
            return w

        # Float → DoubleSpinBox
        if isinstance(val, float):
            mn, mx, dec, step = SPIN_LIMITS.get(key, (-99999, 99999, 2, 1.0))
            w = QDoubleSpinBox()
            w.setRange(mn, mx)
            w.setDecimals(dec)
            w.setSingleStep(step)
            w.setValue(val)
            w.setMinimumWidth(80)
            w.valueChanged.connect(lambda v, k=key: self._on_change(k, v))
            return w

        # Int → SpinBox
        if isinstance(val, int):
            mn, mx, *_ = SPIN_LIMITS.get(key, (-99999, 99999, 0, 1))
            w = QSpinBox()
            w.setRange(int(mn), int(mx))
            w.setValue(val)
            w.valueChanged.connect(lambda v, k=key: self._on_change(k, v))
            return w

        # str → LineEdit
        w = QLineEdit(str(val))
        w.textChanged.connect(lambda v, k=key: self._on_change(k, v))
        return w

    # ------------------------------------------------------------------
    # Обработка изменений
    # ------------------------------------------------------------------

    def _on_change(self, key: str, value):
        if self._obj is None:
            return
        setattr(self._obj, key, value)
        # Обновляем заголовок если изменилось имя
        if key == "name":
            self._title.setText(f"Свойства: {value}")
        self.object_property_changed.emit(self._obj, key, value)

    # ------------------------------------------------------------------
    # Обновление значения виджета без сигналов
    # ------------------------------------------------------------------

    def _set_value(self, widget: QWidget, val):
        widget.blockSignals(True)
        try:
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(val))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(val))
            elif isinstance(widget, ColorButton):
                widget.set_color(str(val))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(val))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))
        finally:
            widget.blockSignals(False)