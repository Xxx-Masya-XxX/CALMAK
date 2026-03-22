"""
ui/toolbars/create_toolbar.py — тулбар создания объектов.

Rectangle · Ellipse · Triangle · Text · Image · Bezier Curve
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar

from ui.icons import get_icon

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow
    from controllers.editor_controller import EditorController


# (action_id, icon_name, display_label)
_OBJECTS = [
    ("add_rect",     "rect",     "Add Rectangle"),
    ("add_ellipse",  "ellipse",  "Add Ellipse"),
    ("add_triangle", "triangle", "Add Triangle"),
    ("add_text",     "text",     "Add Text"),
    ("add_image",    "image",    "Add Image"),
    ("add_bezier",   "bezier",   "Add Bezier Curve"),
]


class CreateToolbar(QToolBar):
    """
    Тулбар «Create Objects».

    Публичные атрибуты:
      actions_map: dict[str, QAction]  — по action_id
      labels:      dict[str, str]      — base labels для hotkey tooltips
    """

    def __init__(self, controller: "EditorController",
                 parent: "QMainWindow" = None):
        super().__init__("Create Objects", parent)
        self._ctrl = controller

        self.setObjectName("tb_create")
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QSize(20, 20))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.actions_map: dict[str, QAction] = {}
        self.labels:      dict[str, str]     = {}

        self._build()

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def _build(self):
        for action_id, icon_name, label in _OBJECTS:
            a = QAction(self)
            a.setIcon(get_icon(icon_name, 20))
            a.setToolTip(label)
            slot = self._make_slot(action_id)
            a.triggered.connect(slot)
            self.addAction(a)
            self.actions_map[action_id] = a
            self.labels[action_id]      = label

    def _make_slot(self, action_id: str):
        slots = {
            "add_rect":     lambda: self._ctrl.add_rect(),
            "add_ellipse":  lambda: self._ctrl.add_ellipse(),
            "add_triangle": lambda: self._ctrl.add_triangle(),
            "add_text":     lambda: self._ctrl.add_text(),
            "add_image":    lambda: self._ctrl.add_image_from_dialog(
                                self.parent()),
            "add_bezier":   lambda: self._ctrl.add_bezier(),
        }
        return slots[action_id]

    # -----------------------------------------------------------------------
    # Icon refresh
    # -----------------------------------------------------------------------

    def refresh_icons(self):
        """Перерисовать иконки после смены темы."""
        for action_id, icon_name, _ in _OBJECTS:
            a = self.actions_map.get(action_id)
            if a:
                a.setIcon(get_icon(icon_name, 20))
