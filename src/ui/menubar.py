"""Верхнее меню приложения."""

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal


class AppMenuBar(QMenuBar):
    """Класс верхнего меню приложения."""

    # сигналы
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._create_menu()

    def _create_menu(self):
        """Создает структуру меню."""

        # --- меню настройки ---
        settings_menu = self.addMenu("Настройки")

        settings_action = QAction("Настройки...", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        settings_menu.addAction(settings_action)

        settings_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.exit_requested.emit)
        settings_menu.addAction(exit_action)

    def open_settings(self):
        """Открывает диалог настроек."""
        from .dialogs import SettingsDialog

        dialog = SettingsDialog(self.parent())
        dialog.exec()