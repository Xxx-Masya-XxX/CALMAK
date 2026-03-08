"""UI компоненты приложения."""

from .main_window import MainWindow
from .panels import ElementsPanel, PropertiesPanel
from .preview import PreviewFrame
from .dialogs import SettingsDialog, TextEditorDialog

__all__ = [
    "MainWindow",
    "ElementsPanel",
    "PropertiesPanel",
    "PreviewFrame",
    "SettingsDialog",
    "TextEditorDialog",
]
