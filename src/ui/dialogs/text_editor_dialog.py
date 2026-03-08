"""Диалог редактирования текста."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QGroupBox, QFormLayout, QFontComboBox,
    QSpinBox, QCheckBox, QColorDialog, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from ...models import TextObject


class TextEditorDialog(QDialog):
    """Диалог для редактирования текста с форматированием."""

    def __init__(self, text_object: TextObject, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор текста")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        self.text_object = text_object

        layout = QVBoxLayout(self)

        # Группа текста
        text_group = QGroupBox("Текст")
        text_layout = QVBoxLayout(text_group)

        # Многострочное текстовое поле
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text_object.text)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setWordWrapMode(True)
        text_layout.addWidget(self.text_edit)

        layout.addWidget(text_group)

        # Группа форматирования
        format_group = QGroupBox("Форматирование")
        format_layout = QFormLayout(format_group)

        # Шрифт
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(text_object.font_family))
        format_layout.addRow("Шрифт:", self.font_combo)

        # Размер шрифта
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 200)
        self.font_size_spin.setValue(text_object.font_size)
        format_layout.addRow("Размер:", self.font_size_spin)

        # Жирный
        self.bold_check = QCheckBox()
        self.bold_check.setChecked(text_object.font_bold)
        format_layout.addRow("Жирный:", self.bold_check)

        # Курсив
        self.italic_check = QCheckBox()
        self.italic_check.setChecked(text_object.font_italic)
        format_layout.addRow("Курсив:", self.italic_check)

        # Подчёркнутый
        self.underline_check = QCheckBox()
        self.underline_check.setChecked(text_object.font_underline)
        format_layout.addRow("Подчёркнутый:", self.underline_check)

        # Цвет текста
        color_layout = QHBoxLayout()
        self.text_color_edit = QLineEdit()
        self.text_color_edit.setText(text_object.text_color)
        self.text_color_edit.setReadOnly(True)
        color_layout.addWidget(self.text_color_edit)

        self.text_color_btn = QPushButton("Выбрать цвет")
        self.text_color_btn.clicked.connect(self._on_text_color_pick)
        color_layout.addWidget(self.text_color_btn)

        format_layout.addRow("Цвет текста:", color_layout)

        layout.addWidget(format_group)

        # Группа выравнивания
        align_group = QGroupBox("Выравнивание")
        align_layout = QFormLayout(align_group)

        # Горизонтальное выравнивание
        self.align_h_combo = QComboBox()
        self.align_h_combo.addItems(["Слева", "По центру", "Справа"])
        align_map = {"left": 0, "center": 1, "right": 2}
        self.align_h_combo.setCurrentIndex(align_map.get(text_object.text_align_h, 0))
        align_layout.addRow("По горизонтали:", self.align_h_combo)

        # Вертикальное выравнивание
        self.align_v_combo = QComboBox()
        self.align_v_combo.addItems(["Сверху", "По центру", "Снизу"])
        align_v_map = {"top": 0, "center": 1, "bottom": 2}
        self.align_v_combo.setCurrentIndex(align_v_map.get(text_object.text_align_v, 0))
        align_layout.addRow("По вертикали:", self.align_v_combo)

        layout.addWidget(align_group)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _on_text_color_pick(self):
        """Открывает диалог выбора цвета текста."""
        current_color = QColor(self.text_object.text_color)
        new_color = QColorDialog.getColor(current_color, self, "Выберите цвет текста")
        if new_color.isValid():
            self.text_object.text_color = new_color.name()
            self.text_color_edit.setText(new_color.name())

    def _on_ok(self):
        """Применяет изменения и закрывает диалог."""
        self.text_object.text = self.text_edit.toPlainText()
        self.text_object.font_family = self.font_combo.currentFont().family()
        self.text_object.font_size = self.font_size_spin.value()
        self.text_object.font_bold = self.bold_check.isChecked()
        self.text_object.font_italic = self.italic_check.isChecked()
        self.text_object.font_underline = self.underline_check.isChecked()

        align_h_map = {0: "left", 1: "center", 2: "right"}
        align_v_map = {0: "top", 1: "center", 2: "bottom"}
        self.text_object.text_align_h = align_h_map.get(self.align_h_combo.currentIndex(), "left")
        self.text_object.text_align_v = align_v_map.get(self.align_v_combo.currentIndex(), "top")

        self.accept()

    def get_text(self) -> str:
        """Возвращает отредактированный текст."""
        return self.text_edit.toPlainText()
