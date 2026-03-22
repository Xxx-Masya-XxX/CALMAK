"""
ui/toolbars/tools_toolbar.py — тулбар инструментов трансформации.

Move · Rotate · Scale · Bezier Path | Bring Forward · Send Backward
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar

from tools.tool_manager import (ToolManager,
                                 TOOL_MOVE, TOOL_ROTATE,
                                 TOOL_SCALE, TOOL_BEZIER)
from ui.icons import get_icon
from ui.hotkeys import DEFAULT_HOTKEYS, ACTION_LABELS

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


# (tool_id, icon_name, hotkey_id)
_TOOLS = [
    (TOOL_MOVE,   "move",   "tool_move"),
    (TOOL_ROTATE, "rotate", "tool_rotate"),
    (TOOL_SCALE,  "scale",  "tool_scale"),
    (TOOL_BEZIER, "bezier", "tool_bezier"),
]


class ToolsToolbar(QToolBar):
    """
    Тулбар «Transform Tools».

    Публичные атрибуты:
      tool_actions: dict[str, QAction]  — по tool_id
      hotkey_ids:   dict[str, str]      — tool_id → hotkey_key
    """

    def __init__(self, tool_manager: ToolManager,
                 bring_forward_cb,
                 send_backward_cb,
                 parent: "QMainWindow" = None):
        super().__init__("Transform Tools", parent)
        self._tm = tool_manager
        self._bring_forward_cb = bring_forward_cb
        self._send_backward_cb = send_backward_cb

        self.setObjectName("tb_tools")
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QSize(20, 20))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.tool_actions: dict[str, QAction] = {}
        self.hotkey_ids:   dict[str, str]     = {}

        self._build()
        self._tm.tool_changed.connect(self._on_tool_changed)

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def _build(self):
        for tool_id, icon_name, hk_id in _TOOLS:
            default_key = DEFAULT_HOTKEYS.get(hk_id, "")
            label       = ACTION_LABELS.get(hk_id, hk_id)
            tip = f"{label}  ({default_key})" if default_key else label

            a = QAction(self)
            a.setIcon(get_icon(icon_name, 20))
            a.setToolTip(tip)
            a.setCheckable(True)
            a.setData(tool_id)
            a.triggered.connect(
                lambda checked, tid=tool_id: self._tm.set_tool(tid))
            self.addAction(a)
            self.tool_actions[tool_id] = a
            self.hotkey_ids[tool_id]   = hk_id

        self.tool_actions[TOOL_MOVE].setChecked(True)

        self.addSeparator()

        af = QAction(self)
        af.setIcon(get_icon("forward", 20))
        af.setToolTip("Bring Forward  (Ctrl+])")
        af.triggered.connect(self._bring_forward_cb)
        self.addAction(af)

        ab = QAction(self)
        ab.setIcon(get_icon("backward", 20))
        ab.setToolTip("Send Backward  (Ctrl+[)")
        ab.triggered.connect(self._send_backward_cb)
        self.addAction(ab)

        self._forward_action  = af
        self._backward_action = ab

    # -----------------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------------

    def _on_tool_changed(self, tool_id: str):
        for tid, act in self.tool_actions.items():
            act.setChecked(tid == tool_id)

    # -----------------------------------------------------------------------
    # Icon refresh
    # -----------------------------------------------------------------------

    def refresh_icons(self):
        for tool_id, icon_name, _ in _TOOLS:
            a = self.tool_actions.get(tool_id)
            if a:
                a.setIcon(get_icon(icon_name, 20))
        self._forward_action.setIcon(get_icon("forward", 20))
        self._backward_action.setIcon(get_icon("backward", 20))
