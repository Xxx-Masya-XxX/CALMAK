"""Верхнее меню приложения."""

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Signal


class AppMenuBar(QObject):
    """Класс верхнего меню приложения."""

    # Сигналы
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self._menubar: QMenuBar | None = None
        self._settings_menu: QMenu | None = None

    def create_menu_bar(self) -> QMenuBar:
        """Создаёт и возвращает верхнее меню."""
        self._menubar = self._parent.menuBar()

        self._settings_menu = self._menubar.addMenu("Настройки")

        settings_action = QAction("Настройки...", self._parent)
        settings_action.triggered.connect(lambda: self.settings_requested.emit())
        self._settings_menu.addAction(settings_action)

        self._settings_menu.addSeparator()

        exit_action = QAction("Выход", self._parent)
        exit_action.triggered.connect(lambda: self.exit_requested.emit())
        self._settings_menu.addAction(exit_action)

        return self._menubar

    def open_settings(self):
        """Открывает диалог настроек."""
        from .dialogs import SettingsDialog
        dialog = SettingsDialog(self._parent)
        dialog.exec()
