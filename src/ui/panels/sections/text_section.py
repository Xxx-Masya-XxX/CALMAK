"""Секция текстовых свойств."""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QFontComboBox, QDoubleSpinBox, QCheckBox, QComboBox
)
from PySide6.QtGui import QFont, QTextOption

from .base_section import BaseSection
from ..widgets.color_button import ColorButton
from ....models.objects.text_object import TextObject


class TextSection(BaseSection):
    """Текст, шрифт, форматирование, выравнивание, цвет текста."""

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Текст
        layout.addWidget(QLabel("Текст:"))
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.text_edit.textChanged.connect(self._on_text)
        layout.addWidget(self.text_edit)

        # Шрифт
        layout.addWidget(QLabel("Шрифт:"))
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._on_font)
        layout.addWidget(self.font_combo)

        # Размер
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Размер:"))
        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(1, 200)
        self.font_size_spin.setDecimals(0)
        self.font_size_spin.valueChanged.connect(self._on_font_size)
        size_row.addWidget(self.font_size_spin)
        size_row.addStretch()
        layout.addLayout(size_row)

        # Стиль
        style_row = QHBoxLayout()
        style_row.addWidget(QLabel("Стиль:"))
        self.bold_check = QCheckBox("Жирный")
        self.bold_check.stateChanged.connect(self._on_style)
        self.italic_check = QCheckBox("Курсив")
        self.italic_check.stateChanged.connect(self._on_style)
        self.underline_check = QCheckBox("Подчёркнутый")
        self.underline_check.stateChanged.connect(self._on_style)
        style_row.addWidget(self.bold_check)
        style_row.addWidget(self.italic_check)
        style_row.addWidget(self.underline_check)
        style_row.addStretch()
        layout.addLayout(style_row)

        # Цвет текста
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Цвет текста:"))
        self.text_color_btn = ColorButton()
        self.text_color_btn.color_changed.connect(self._on_text_color)
        color_row.addWidget(self.text_color_btn)
        layout.addLayout(color_row)

        # Горизонтальное выравнивание
        h_row = QHBoxLayout()
        h_row.addWidget(QLabel("По горизонтали:"))
        self.align_h_combo = QComboBox()
        self.align_h_combo.addItems(["Слева", "По центру", "Справа"])
        self.align_h_combo.currentIndexChanged.connect(self._on_align)
        h_row.addWidget(self.align_h_combo)
        layout.addLayout(h_row)

        # Вертикальное выравнивание
        v_row = QHBoxLayout()
        v_row.addWidget(QLabel("По вертикали:"))
        self.align_v_combo = QComboBox()
        self.align_v_combo.addItems(["Сверху", "По центру", "Снизу"])
        self.align_v_combo.currentIndexChanged.connect(self._on_align)
        v_row.addWidget(self.align_v_combo)
        layout.addLayout(v_row)

    def _load(self, obj: TextObject):
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(obj.text)
        self.text_edit.blockSignals(False)

        self.font_combo.setCurrentFont(QFont(obj.font_family))
        self.font_size_spin.setValue(obj.font_size)
        self.bold_check.setChecked(obj.font_bold)
        self.italic_check.setChecked(obj.font_italic)
        self.underline_check.setChecked(obj.font_underline)
        self.text_color_btn.color = obj.text_color

        self.align_h_combo.setCurrentIndex(
            {"left": 0, "center": 1, "right": 2}.get(obj.text_align_h, 0)
        )
        self.align_v_combo.setCurrentIndex(
            {"top": 0, "middle": 1, "bottom": 2}.get(obj.text_align_v, 0)
        )

    def _on_text(self):
        if isinstance(self._obj, TextObject):
            self._obj.text = self.text_edit.toPlainText()
            self._emit()

    def _on_font(self, font: QFont):
        if isinstance(self._obj, TextObject):
            self._obj.font_family = font.family()
            self._emit()

    def _on_font_size(self, value: float):
        if isinstance(self._obj, TextObject):
            self._obj.font_size = int(value)
            self._emit()

    def _on_style(self):
        if isinstance(self._obj, TextObject):
            self._obj.font_bold = self.bold_check.isChecked()
            self._obj.font_italic = self.italic_check.isChecked()
            self._obj.font_underline = self.underline_check.isChecked()
            self._emit()

    def _on_text_color(self, color: str):
        if isinstance(self._obj, TextObject):
            self._obj.text_color = color
            self._emit()

    def _on_align(self):
        if isinstance(self._obj, TextObject):
            self._obj.text_align_h = {0: "left", 1: "center", 2: "right"}.get(
                self.align_h_combo.currentIndex(), "left"
            )
            self._obj.text_align_v = {0: "top", 1: "middle", 2: "bottom"}.get(
                self.align_v_combo.currentIndex(), "top"
            )
            self._emit()
