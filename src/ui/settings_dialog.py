"""Окно настроек приложения."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPushButton, QLabel, QGroupBox, QApplication
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    """Диалоговое окно настроек приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # Текущие настройки
        self._current_style = QApplication.style().objectName().lower()
        self._current_theme = "light"
        
        layout = QVBoxLayout(self)
        
        # Группа стиля
        style_group = QGroupBox("Стиль приложения")
        style_layout = QFormLayout(style_group)
        
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Fusion",
            "Windows",
            "WindowsVista"
        ])
        # Устанавливаем текущий стиль
        style_index = self.style_combo.findText(self._current_style.capitalize())
        if style_index >= 0:
            self.style_combo.setCurrentIndex(style_index)
        
        style_layout.addRow("Стиль:", self.style_combo)
        layout.addWidget(style_group)
        
        # Группа темы
        theme_group = QGroupBox("Цветовая тема")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная"])
        theme_layout.addRow("Тема:", self.theme_combo)
        layout.addWidget(theme_group)
        
        # Описание
        info_label = QLabel(
            "Изменения вступят в силу после нажатия кнопки «Применить».\n"
            "Стиль Fusion рекомендуется для кроссплатформенной работы."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(self.apply_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)

    def _on_apply(self):
        """Применяет настройки без закрытия окна."""
        self._apply_settings()

    def _on_ok(self):
        """Применяет настройки и закрывает окно."""
        self._apply_settings()
        self.accept()
    
    def _apply_settings(self):
        """Применяет выбранные настройки."""
        style_name = self.style_combo.currentText()
        theme_name = self.theme_combo.currentText()
        
        # Сообщаем родителю о необходимости применить настройки
        if self.parent():
            self.parent().apply_settings(style_name, theme_name)
    
    def get_settings(self) -> dict:
        """Возвращает текущие настройки."""
        return {
            "style": self.style_combo.currentText(),
            "theme": "dark" if self.theme_combo.currentIndex() == 1 else "light"
        }
