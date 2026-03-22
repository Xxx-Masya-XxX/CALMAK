"""
ui/context_toolbar.py — контекстный тулбар для специальных объектов.

Появляется над сценой когда выбран объект со специальной логикой.
Каждый тип объекта регистрирует свой набор действий.
Тулбар скрывается при снятии выделения или выборе обычного объекта.

Текущие тулбары:
  • BezierToolbar — появляется при выборе объекта BEZIER + активном BezierTool
      - Add Point mode
      - Delete Point mode
      - Smooth / Corner toggle
      - Close path toggle
      - Finish (перейти в Move)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QFrame, QButtonGroup, QSizePolicy,
    QDoubleSpinBox, QCheckBox, QSplitter
)

if TYPE_CHECKING:
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController
    from tools.tool_manager import ToolManager
    from tools.bezier_tool import BezierTool


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseContextBar(QWidget):
    """Базовый контекстный тулбар. Виджет без рамки."""

    def __init__(self, store: "EditorStore",
                 controller: "EditorController",
                 tool_manager: "ToolManager",
                 parent=None):
        super().__init__(parent)
        self._store      = store
        self._ctrl       = controller
        self._tm         = tool_manager
        self._build_ui()
        self.hide()

    def _build_ui(self): ...
    def refresh(self):   ...

    def _btn(self, text: str, tip: str = "", checkable: bool = False,
             size: int = 28) -> QPushButton:
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setFixedHeight(size)
        b.setCheckable(checkable)
        b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        return b

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setFixedWidth(1)
        f.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        return f

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size:11px;padding:0 4px;")
        return lbl


# ---------------------------------------------------------------------------
# Bezier context toolbar
# ---------------------------------------------------------------------------

class BezierContextBar(BaseContextBar):
    """
    Контекстный тулбар для кривых Безье.

    Кнопки:
      [✥ Move]  [+ Add Point]  [− Del Point]  |  [⌀ Corner / Smooth]  |
      [⊙ Close/Open]  |  [↩ Stroke: ━━━ 2.5 px]  |  [✓ Done]
    """

    def _build_ui(self):
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(4)

        # ── Label ──
        lbl = QLabel("Bezier Path")
        lbl.setStyleSheet(
            "font-weight:bold;font-size:11px;"
            "padding:0 6px;color:palette(text);")
        root.addWidget(lbl)
        root.addWidget(self._sep())

        # ── Edit mode buttons (mutually exclusive) ──
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)

        self._btn_select = self._btn("↖ Select", "Select & move points", checkable=True)
        self._btn_add    = self._btn("✚ Add",    "Click on path to add point", checkable=True)
        self._btn_delete = self._btn("✖ Delete", "Click point to delete it", checkable=True)

        self._mode_group.addButton(self._btn_select)
        self._mode_group.addButton(self._btn_add)
        self._mode_group.addButton(self._btn_delete)

        for b in (self._btn_select, self._btn_add, self._btn_delete):
            root.addWidget(b)

        self._btn_select.setChecked(True)
        root.addWidget(self._sep())

        # ── Smooth / Corner ──
        self._btn_smooth = self._btn("⌀ Smooth",  "Toggle smooth handles on selected point", checkable=True)
        self._btn_smooth.setChecked(True)
        root.addWidget(self._btn_smooth)
        root.addWidget(self._sep())

        # ── Close path ──
        self._btn_close = self._btn("⊙ Close",  "Close / open path", checkable=True)
        root.addWidget(self._btn_close)
        root.addWidget(self._sep())

        # ── Stroke width ──
        root.addWidget(self._label("Stroke:"))
        self._stroke_spin = QDoubleSpinBox()
        self._stroke_spin.setRange(0.5, 100)
        self._stroke_spin.setSingleStep(0.5)
        self._stroke_spin.setDecimals(1)
        self._stroke_spin.setFixedWidth(64)
        self._stroke_spin.setFixedHeight(26)
        root.addWidget(self._stroke_spin)
        root.addWidget(self._label("px"))
        root.addWidget(self._sep())

        # ── Point count info ──
        self._pt_label = QLabel("0 pts")
        self._pt_label.setStyleSheet("font-size:10px;color:palette(mid);padding:0 4px;")
        root.addWidget(self._pt_label)

        root.addStretch()

        # ── Done ──
        self._btn_done = self._btn("✓ Done", "Finish editing, switch to Move tool")
        self._btn_done.setStyleSheet(
            "QPushButton{background:#2A6A2A;color:white;border-radius:4px;"
            "padding:2px 10px;font-size:11px;}"
            "QPushButton:hover{background:#3A8A3A;}")
        root.addWidget(self._btn_done)

        # ── Connect ──
        self._btn_select.clicked.connect(self._on_mode_select)
        self._btn_add.clicked.connect(self._on_mode_add)
        self._btn_delete.clicked.connect(self._on_mode_delete)
        self._btn_smooth.clicked.connect(self._on_toggle_smooth)
        self._btn_close.clicked.connect(self._on_toggle_close)
        self._stroke_spin.valueChanged.connect(self._on_stroke_changed)
        self._btn_done.clicked.connect(self._on_done)

    # -----------------------------------------------------------------------
    # Refresh from model
    # -----------------------------------------------------------------------

    def refresh(self):
        obj_id = self._store.selection.active_id
        canvas = self._store.active_canvas
        if not obj_id or not canvas:
            return
        obj = canvas.objects.get(obj_id)
        if not obj:
            return
        payload = obj.payload

        # Point count
        n = len(payload.points) if hasattr(payload, 'points') else 0
        self._pt_label.setText(f"{n} pt{'s' if n != 1 else ''}")

        # Closed state
        self._btn_close.blockSignals(True)
        self._btn_close.setChecked(getattr(payload, 'closed', False))
        self._btn_close.setText("⊙ Open" if getattr(payload, 'closed', False)
                                else "⊙ Close")
        self._btn_close.blockSignals(False)

        # Stroke width
        self._stroke_spin.blockSignals(True)
        self._stroke_spin.setValue(obj.style.stroke_width)
        self._stroke_spin.blockSignals(False)

        # Smooth state of selected point
        tool = self._tm.active_tool
        sel_pt = getattr(tool, '_sel_pt', -1)
        if (sel_pt >= 0 and hasattr(payload, 'points')
                and sel_pt < len(payload.points)):
            pt = payload.points[sel_pt]
            self._btn_smooth.blockSignals(True)
            self._btn_smooth.setChecked(pt.smooth)
            self._btn_smooth.setText("⌀ Smooth" if pt.smooth else "⌀ Corner")
            self._btn_smooth.blockSignals(False)

        # Sync edit mode from tool
        mode = getattr(tool, '_edit_mode', 'select')
        self._btn_select.setChecked(mode == 'select')
        self._btn_add.setChecked(mode == 'add')
        self._btn_delete.setChecked(mode == 'delete')

    # -----------------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------------

    def _on_mode_select(self):
        tool = self._tm.active_tool
        if hasattr(tool, '_edit_mode'):
            tool._edit_mode = 'select'

    def _on_mode_add(self):
        tool = self._tm.active_tool
        if hasattr(tool, '_edit_mode'):
            tool._edit_mode = 'add'

    def _on_mode_delete(self):
        tool = self._tm.active_tool
        if hasattr(tool, '_edit_mode'):
            tool._edit_mode = 'delete'

    def _on_toggle_smooth(self, checked: bool):
        tool = self._tm.active_tool
        sel_pt = getattr(tool, '_sel_pt', -1)
        if sel_pt < 0:
            return
        canvas = self._store.active_canvas
        obj_id = self._store.selection.active_id
        if not canvas or not obj_id:
            return
        obj = canvas.objects.get(obj_id)
        if not obj or sel_pt >= len(obj.payload.points):
            return
        obj.payload.points[sel_pt].smooth = checked
        self._btn_smooth.setText("⌀ Smooth" if checked else "⌀ Corner")
        self._store.document_changed.emit()
        # rebuild bezier overlay
        if hasattr(tool, '_rebuild_overlay') and tool._ctx:
            tool._rebuild_overlay(tool._ctx)

    def _on_toggle_close(self, checked: bool):
        canvas = self._store.active_canvas
        obj_id = self._store.selection.active_id
        if not canvas or not obj_id:
            return
        obj = canvas.objects.get(obj_id)
        if not obj:
            return
        obj.payload.closed = checked
        self._btn_close.setText("⊙ Open" if checked else "⊙ Close")
        self._store.document_changed.emit()

    def _on_stroke_changed(self, value: float):
        obj_id = self._store.selection.active_id
        if obj_id:
            self._ctrl.update_properties(
                obj_id, {"style.stroke_width": value})

    def _on_done(self):
        from tools.tool_manager import TOOL_MOVE
        # Finish drawing first
        tool = self._tm.active_tool
        if hasattr(tool, '_finish_drawing') and tool._ctx:
            tool._finish_drawing(tool._ctx)
        self._tm.set_tool(TOOL_MOVE)


# ---------------------------------------------------------------------------
# ContextToolbarManager — показывает нужный тулбар для активного объекта
# ---------------------------------------------------------------------------

class ContextToolbarManager(QWidget):
    """
    Контейнер который отображает нужный контекстный тулбар
    в зависимости от типа выбранного объекта + активного инструмента.

    Встраивается между основным тулбаром и сценой.
    Скрывается когда нет специального контекста.
    """

    def __init__(self, store: "EditorStore",
                 controller: "EditorController",
                 tool_manager: "ToolManager",
                 parent=None):
        super().__init__(parent)
        self._store = store
        self._ctrl  = controller
        self._tm    = tool_manager

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Register context bars
        self._bezier_bar = BezierContextBar(store, controller, tool_manager, self)
        self._layout.addWidget(self._bezier_bar)

        # All bars hidden initially
        self.setMaximumHeight(0)

        # Connect signals
        store.selection_changed.connect(self._on_selection_changed)
        tool_manager.tool_changed.connect(self._on_tool_changed)

        self._current_bar: BaseContextBar | None = None

    # -----------------------------------------------------------------------

    def _on_selection_changed(self, ids, active_id):
        self._update()

    def _on_tool_changed(self, tool_id: str):
        self._update()

    def _update(self):
        from domain.models import ObjectType
        from tools.bezier_tool import TOOL_BEZIER

        active_id  = self._store.selection.active_id
        tool_id    = self._tm.active_tool_id
        canvas     = self._store.active_canvas

        new_bar: BaseContextBar | None = None

        if active_id and canvas:
            obj = canvas.objects.get(active_id)
            if obj:
                # Bezier tool OR bezier object selected
                is_bezier_obj  = (obj.type == ObjectType.BEZIER)
                is_bezier_tool = (tool_id == TOOL_BEZIER)

                if is_bezier_obj and is_bezier_tool:
                    new_bar = self._bezier_bar

        # Switch bars
        if new_bar is not self._current_bar:
            if self._current_bar:
                self._current_bar.hide()
            self._current_bar = new_bar
            if new_bar:
                new_bar.show()
                new_bar.refresh()

        # Show/hide entire container with animation effect
        if new_bar:
            self.setMaximumHeight(44)
            self.setVisible(True)
        else:
            self.setMaximumHeight(0)
            self.setVisible(False)

    def refresh_active(self):
        """Обновить активный тулбар (вызывать при изменении модели)."""
        if self._current_bar:
            self._current_bar.refresh()
