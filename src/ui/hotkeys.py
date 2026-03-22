"""
ui/hotkeys.py — константы горячих клавиш и логика их применения.

DEFAULT_HOTKEYS  — дефолтные значения (инструменты: V/R/E/B, объекты: пустые)
apply_hotkeys()  — применяет словарь hotkeys к QAction-ам из тулбаров
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence

if TYPE_CHECKING:
    from PySide6.QtWidgets import QAction


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_HOTKEYS: dict[str, str] = {
    # Create objects — по умолчанию не назначены
    "add_rect":     "",
    "add_ellipse":  "",
    "add_triangle": "",
    "add_text":     "",
    "add_image":    "",
    "add_bezier":   "",
    # Tools — дефолты
    "tool_move":    "V",
    "tool_rotate":  "R",
    "tool_scale":   "E",
    "tool_bezier":  "B",
}

# Отображение action_id → читаемое имя для тултипа
ACTION_LABELS: dict[str, str] = {
    "add_rect":     "Add Rectangle",
    "add_ellipse":  "Add Ellipse",
    "add_triangle": "Add Triangle",
    "add_text":     "Add Text",
    "add_image":    "Add Image",
    "add_bezier":   "Add Bezier Curve",
    "tool_move":    "Move",
    "tool_rotate":  "Rotate",
    "tool_scale":   "Scale",
    "tool_bezier":  "Bezier Path",
}


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply_hotkeys(
    hotkeys: dict[str, str],
    create_actions: dict[str, "QAction"],
    tool_actions: dict[str, "QAction"],
    create_labels: dict[str, str],
) -> None:
    """
    Назначает горячие клавиши и обновляет тултипы для всех action-ов.

    Args:
        hotkeys:        словарь {action_id: key_string}
        create_actions: {action_id: QAction} из Create toolbar
        tool_actions:   {tool_id:   QAction} из Tools toolbar
        create_labels:  {action_id: "Add Rectangle"} — базовые метки
    """
    from tools.tool_manager import TOOL_MOVE, TOOL_ROTATE, TOOL_SCALE, TOOL_BEZIER

    # ── Create object actions ────────────────────────────────────────────────
    create_ids = [
        "add_rect", "add_ellipse", "add_triangle",
        "add_text", "add_image",   "add_bezier",
    ]
    for action_id in create_ids:
        action = create_actions.get(action_id)
        if action is None:
            continue
        seq     = hotkeys.get(action_id, "")
        seq_str = QKeySequence(seq).toString() if seq else ""
        action.setShortcut(QKeySequence(seq) if seq else QKeySequence())
        base = create_labels.get(action_id,
               ACTION_LABELS.get(action_id, action_id))
        action.setToolTip(f"{base}  ({seq_str})" if seq_str else base)

    # ── Tool actions ─────────────────────────────────────────────────────────
    tool_hk_map = {
        "tool_move":   (TOOL_MOVE,   tool_actions.get(TOOL_MOVE)),
        "tool_rotate": (TOOL_ROTATE, tool_actions.get(TOOL_ROTATE)),
        "tool_scale":  (TOOL_SCALE,  tool_actions.get(TOOL_SCALE)),
        "tool_bezier": (TOOL_BEZIER, tool_actions.get(TOOL_BEZIER)),
    }
    for hk_id, (tool_id, action) in tool_hk_map.items():
        if action is None:
            continue
        seq     = hotkeys.get(hk_id, "")
        seq_str = QKeySequence(seq).toString() if seq else ""
        action.setShortcut(QKeySequence(seq) if seq else QKeySequence())
        name = ACTION_LABELS.get(hk_id, hk_id)
        action.setToolTip(f"{name}  ({seq_str})" if seq_str else name)
