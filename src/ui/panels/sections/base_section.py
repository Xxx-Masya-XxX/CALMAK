"""Базовый класс секции панели свойств."""

from PySide6.QtWidgets import QGroupBox
from PySide6.QtCore import Signal

from ....models.objects.base_object import BaseObject


class BaseSection(QGroupBox):
    """Базовый класс секции панели свойств.

    Каждая секция — самостоятельный QGroupBox:
    - _setup_ui()  — создаёт виджеты (вызывается в __init__)
    - _load(obj)   — заполняет виджеты из модели
    - _emit()      — испускает object_changed
    """

    object_changed = Signal(BaseObject)

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._obj: BaseObject | None = None
        self._blocking = False
        self._setup_ui()

    def _setup_ui(self):
        """Создаёт виджеты. Переопределить в наследнике."""
        pass

    def load(self, obj: BaseObject):
        """Загружает данные объекта в UI."""
        self._obj = obj
        self._blocking = True
        self._load(obj)
        self._block_widgets(False)

    def _block_widgets(self, block: bool):
        """Блокирует сигналы всех интерактивных дочерних виджетов."""
        from PySide6.QtWidgets import (
            QAbstractSpinBox, QAbstractButton,
            QComboBox, QTextEdit, QLineEdit
        )
        for cls in (QAbstractSpinBox, QAbstractButton, QComboBox, QTextEdit, QLineEdit):
            for widget in self.findChildren(cls):
                widget.blockSignals(block)
    def _load(self, obj: BaseObject):
        """Реализация загрузки. Переопределить в наследнике."""
        pass

    def _emit(self):
        """Испускает сигнал если сигналы не заблокированы."""
        if not self._blocking and self._obj is not None:
            self.object_changed.emit(self._obj)
