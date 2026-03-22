"""
BezierTool — инструмент редактирования кривых Безье.

Режимы:
  • Нет активного объекта — клик создаёт новую кривую и добавляет первую точку
  • Есть активная кривая — каждый клик добавляет новую точку в конец
  • Двойной клик — завершить кривую (перейти в режим редактирования)
  • Escape / смена инструмента — завершить кривую

Редактирование точек (после завершения рисования):
  • Клик на anchor — выделить точку
  • Drag anchor — переместить точку (ручки двигаются вместе)
  • Drag control handle — изменить касательную
  • Клик на пустое место — снять выделение
  • Delete — удалить выбранную точку
  • Shift+клик на anchor — toggle smooth/corner

Визуальные элементы на сцене:
  • Синие квадраты — anchor-точки
  • Круглые незаполненные — контрольные ручки
  • Серые линии — tangent lines от anchor до ручек
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QColor, QPen, QBrush, QMouseEvent,
                            QPainterPath, QKeyEvent)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsEllipseItem,
                                QGraphicsRectItem, QGraphicsLineItem,
                                QGraphicsPathItem)

if TYPE_CHECKING:
    from tools.tool_manager import ToolContext
    from domain.models import BezierPayload, BezierPoint

TOOL_BEZIER = "bezier"

# Handle sizes
ANCHOR_SIZE  = 9     # px, квадрат anchor
CTRL_SIZE    = 7     # px, кружок контрольной точки
HIT_RADIUS   = 10   # px, радиус клика

# Colors
COL_ANCHOR       = QColor("#4A9EFF")
COL_ANCHOR_SEL   = QColor("#FFFFFF")
COL_ANCHOR_HOVER = QColor("#8AC4FF")
COL_CTRL         = QColor("#FF9900")
COL_CTRL_HOVER   = QColor("#FFCC66")
COL_TANGENT      = QColor(150, 150, 150, 160)
COL_PATH_PREVIEW = QColor("#E2904A")
COL_STROKE_EDIT  = QColor("#4A9EFF")


# ---------------------------------------------------------------------------
# Overlay items (не хранят данные — только отрисовка)
# ---------------------------------------------------------------------------

class AnchorItem(QGraphicsRectItem):
    """Синий квадрат — anchor-точка кривой."""
    def __init__(self, pt_idx: int):
        hs = ANCHOR_SIZE / 2
        super().__init__(-hs, -hs, ANCHOR_SIZE, ANCHOR_SIZE)
        self.pt_idx  = pt_idx
        self.kind    = "anchor"
        self.setZValue(10001)
        self.setPen(QPen(QColor("#FFFFFF"), 1.2))
        self.setBrush(QBrush(COL_ANCHOR))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)


class CtrlItem(QGraphicsEllipseItem):
    """Оранжевый кружок — контрольная ручка."""
    def __init__(self, pt_idx: int, which: str):  # which = "cx1"|"cx2"
        hs = CTRL_SIZE / 2
        super().__init__(-hs, -hs, CTRL_SIZE, CTRL_SIZE)
        self.pt_idx = pt_idx
        self.which  = which
        self.kind   = "ctrl"
        self.setZValue(10000)
        self.setPen(QPen(QColor("#FFFFFF"), 1.0))
        self.setBrush(QBrush(COL_CTRL))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)


class TangentLine(QGraphicsLineItem):
    """Серая линия от anchor до контрольной точки."""
    def __init__(self):
        super().__init__()
        self.setZValue(9999)
        self.setPen(QPen(COL_TANGENT, 1, Qt.DashLine))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)


# ---------------------------------------------------------------------------
# BezierTool
# ---------------------------------------------------------------------------

class BezierTool:
    tool_id = TOOL_BEZIER
    cursor  = Qt.CrossCursor

    def __init__(self):
        self._obj_id:    str | None = None   # активный bezier объект
        self._drawing   = True    # True = добавляем точки, False = редактируем

        # Overlay items
        self._anchors:  list[AnchorItem]  = []
        self._ctrls:    list[CtrlItem]    = []
        self._tangents: list[TangentLine] = []
        self._preview_item: QGraphicsPathItem | None = None

        # Drag state
        self._drag_what: str | None = None   # "anchor"|"ctrl"
        self._drag_pt_idx: int      = -1
        self._drag_which: str       = ""     # "cx1"|"cx2"
        self._drag_start:  QPointF  = QPointF()
        self._orig_x: float = 0
        self._orig_y: float = 0

        # Selected anchor index
        self._sel_pt: int = -1

        # Edit mode: 'select' | 'add' | 'delete'
        self._edit_mode: str = 'select'

        # Context reference (set on activate)
        self._ctx: "ToolContext | None" = None

        # Live preview last mouse pos (while drawing)
        self._live_pos: QPointF | None = None

    # -----------------------------------------------------------------------
    # Activate / Deactivate
    # -----------------------------------------------------------------------

    def activate(self, ctx: "ToolContext"):
        self._ctx = ctx
        ctx.view.setCursor(Qt.CrossCursor)
        # Если уже есть выделенный bezier — переключиться в режим редактирования
        aid = ctx.store.selection.active_id
        canvas = ctx.store.active_canvas
        if aid and canvas:
            obj = canvas.objects.get(aid)
            if obj and obj.type.value == "bezier":
                self._obj_id = aid
                self._drawing = False
                self._edit_mode = 'select'
                self._rebuild_overlay(ctx)
                return
        self._drawing = True
        self._edit_mode = 'select'
        self._obj_id  = None

    def deactivate(self, ctx: "ToolContext"):
        self._finish_drawing(ctx)
        self._clear_overlay(ctx)
        self._obj_id = None
        self._sel_pt = -1
        self._ctx    = None
        ctx.view.setCursor(Qt.ArrowCursor)

    # -----------------------------------------------------------------------
    # Mouse events
    # -----------------------------------------------------------------------

    def mouse_press(self, event: QMouseEvent, ctx: "ToolContext"):
        pos = ctx.view.mapToScene(event.pos())

        if event.button() == Qt.RightButton:
            # ПКМ — завершить рисование
            self._finish_drawing(ctx)
            return

        if event.button() != Qt.LeftButton:
            return

        if self._drawing:
            self._handle_draw_click(pos, ctx, event)
        else:
            self._handle_edit_click(pos, ctx, event)

    def mouse_move(self, event: QMouseEvent, ctx: "ToolContext"):
        pos = ctx.view.mapToScene(event.pos())

        if self._drawing:
            self._live_pos = pos
            self._update_preview(ctx)
            return

        if self._drag_what:
            self._handle_drag(pos, ctx)

    def mouse_release(self, event: QMouseEvent, ctx: "ToolContext"):
        if not self._drawing and self._drag_what:
            self._commit_drag(ctx)
        self._drag_what = None

    def mouse_double_click(self, event: QMouseEvent, ctx: "ToolContext"):
        if self._drawing:
            self._finish_drawing(ctx)

    def key_press(self, event: QKeyEvent, ctx: "ToolContext"):
        if event.key() == Qt.Key_Escape:
            self._finish_drawing(ctx)
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._delete_selected_point(ctx)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._finish_drawing(ctx)

    # -----------------------------------------------------------------------
    # Drawing mode
    # -----------------------------------------------------------------------

    def _handle_draw_click(self, pos: QPointF, ctx: "ToolContext",
                           event: QMouseEvent):
        from domain.models import BezierPayload, BezierPoint, make_bezier, ObjectType
        from commands.commands import AddObjectCommand, UpdatePropertiesCommand
        import copy

        canvas = ctx.store.active_canvas
        if not canvas:
            return

        if self._obj_id is None:
            # Создаём новый объект кривой
            from domain.models import gen_id, ObjectState, Transform, StyleState, ObjectType as OT
            from commands.commands import AddObjectCommand
            p0 = BezierPoint(x=pos.x(), y=pos.y(),
                             cx1=pos.x(), cy1=pos.y(),
                             cx2=pos.x(), cy2=pos.y())
            obj = make_bezier(x=pos.x(), y=pos.y())
            obj.payload = BezierPayload(points=[p0], closed=False)
            self._obj_id = obj.id
            ctx.controller.store._push_command(
                AddObjectCommand(canvas.id, obj))
            ctx.controller.select_one(obj.id)
        else:
            # Добавляем точку в конец
            obj = canvas.objects.get(self._obj_id)
            if not obj:
                return
            payload: BezierPayload = obj.payload

            # Если кликнули близко к первой точке — замкнуть и завершить
            if len(payload.points) > 1:
                first = payload.points[0]
                if _dist(pos, QPointF(first.x, first.y)) < HIT_RADIUS * 2:
                    payload.closed = True
                    self._finish_drawing(ctx)
                    return

            new_pt = BezierPoint(
                x=pos.x(), y=pos.y(),
                cx1=pos.x(), cy1=pos.y(),
                cx2=pos.x(), cy2=pos.y(),
            )
            import copy as _cp
            new_payload = _cp.deepcopy(payload)
            new_payload.points.append(new_pt)
            _apply_payload(obj, new_payload)
            ctx.store.document_changed.emit()

        self._rebuild_overlay(ctx)

    def _update_preview(self, ctx: "ToolContext"):
        """Рисует линию от последней точки до курсора (preview)."""
        if not self._obj_id or not self._live_pos:
            return
        canvas = ctx.store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(self._obj_id)
        if not obj:
            return
        payload = obj.payload
        if not payload.points:
            return

        last = payload.points[-1]
        path = QPainterPath(QPointF(last.x, last.y))
        path.lineTo(self._live_pos)

        if self._preview_item is None:
            self._preview_item = QGraphicsPathItem()
            self._preview_item.setZValue(9998)
            pen = QPen(COL_PATH_PREVIEW, 1.5, Qt.DashLine)
            self._preview_item.setPen(pen)
            self._preview_item.setBrush(QBrush(Qt.transparent))
            ctx.scene.addItem(self._preview_item)

        self._preview_item.setPath(path)

    def _finish_drawing(self, ctx: "ToolContext"):
        """Завершить рисование — перейти в режим редактирования."""
        if self._preview_item:
            try:
                ctx.scene.removeItem(self._preview_item)
            except Exception:
                pass
            self._preview_item = None
        self._live_pos = None

        if self._obj_id:
            self._drawing = False
            # Обновляем сцену чтобы кривая нарисовалась корректно
            ctx.store.document_changed.emit()
            self._rebuild_overlay(ctx)

    # -----------------------------------------------------------------------
    # Edit mode
    # -----------------------------------------------------------------------

    def _handle_edit_click(self, pos: QPointF, ctx: "ToolContext",
                           event: QMouseEvent):
        canvas = ctx.store.active_canvas
        if not canvas or not self._obj_id:
            return
        obj = canvas.objects.get(self._obj_id)
        if not obj:
            return
        payload = obj.payload

        # ── DELETE mode: click on anchor = delete it ──
        if self._edit_mode == 'delete':
            for i, pt in enumerate(payload.points):
                if _dist(pos, QPointF(pt.x, pt.y)) <= HIT_RADIUS:
                    if len(payload.points) > 2:
                        import copy as _cp
                        new_payload = _cp.deepcopy(payload)
                        new_payload.points.pop(i)
                        _apply_payload(obj, new_payload)
                        self._sel_pt = max(0, i - 1)
                        ctx.store.document_changed.emit()
                        self._rebuild_overlay(ctx)
                        # Notify context toolbar
                        _notify_context_toolbar(ctx)
                    return
            return

        # ── ADD mode: click anywhere = insert point on nearest segment ──
        if self._edit_mode == 'add':
            self._insert_point_at(pos, obj, ctx)
            return

        # ── SELECT mode (default) ──
        # Hit test: anchor точки
        for i, pt in enumerate(payload.points):
            if _dist(pos, QPointF(pt.x, pt.y)) <= HIT_RADIUS:
                if event.modifiers() & Qt.ShiftModifier:
                    pt.smooth = not pt.smooth
                    ctx.store.document_changed.emit()
                    self._rebuild_overlay(ctx)
                    _notify_context_toolbar(ctx)
                    return
                self._sel_pt = i
                self._drag_what    = "anchor"
                self._drag_pt_idx  = i
                self._drag_start   = pos
                self._orig_x = pt.x
                self._orig_y = pt.y
                self._rebuild_overlay(ctx)
                _notify_context_toolbar(ctx)
                return

        # Hit test: control handles
        for i, pt in enumerate(payload.points):
            for which, cx, cy in [("cx1", pt.cx1, pt.cy1),
                                   ("cx2", pt.cx2, pt.cy2)]:
                if _dist(pos, QPointF(cx, cy)) <= HIT_RADIUS:
                    self._drag_what   = "ctrl"
                    self._drag_pt_idx = i
                    self._drag_which  = which
                    self._drag_start  = pos
                    self._orig_x = cx
                    self._orig_y = cy
                    return

        # Клик на пустое место
        self._sel_pt   = -1
        self._drag_what = None
        self._rebuild_overlay(ctx)

    def _handle_drag(self, pos: QPointF, ctx: "ToolContext"):
        canvas = ctx.store.active_canvas
        if not canvas or not self._obj_id:
            return
        obj = canvas.objects.get(self._obj_id)
        if not obj:
            return
        payload = obj.payload

        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()
        pt = payload.points[self._drag_pt_idx]

        if self._drag_what == "anchor":
            pt.x   = self._orig_x + dx
            pt.y   = self._orig_y + dy
            # Двигаем ручки вместе с anchor
            pt.cx1 += dx; pt.cy1 += dy
            pt.cx2 += dx; pt.cy2 += dy
            # Обновить transform.x/y для первой точки (совместимость с деревом)
            if self._drag_pt_idx == 0:
                obj.transform.x = pt.x
                obj.transform.y = pt.y

        elif self._drag_what == "ctrl":
            new_cx = self._orig_x + dx
            new_cy = self._orig_y + dy
            if self._drag_which == "cx2":
                pt.cx2 = new_cx; pt.cy2 = new_cy
                if pt.smooth:
                    # Отражаем cx1 симметрично через anchor
                    pt.cx1 = 2 * pt.x - new_cx
                    pt.cy1 = 2 * pt.y - new_cy
            else:
                pt.cx1 = new_cx; pt.cy1 = new_cy
                if pt.smooth:
                    pt.cx2 = 2 * pt.x - new_cx
                    pt.cy2 = 2 * pt.y - new_cy

        self._update_overlay_positions(ctx)
        ctx.store.document_changed.emit()

    def _commit_drag(self, ctx: "ToolContext"):
        """Drag завершён — nothing extra needed, state already in model."""
        self._drag_what   = None
        self._drag_pt_idx = -1

    def _delete_selected_point(self, ctx: "ToolContext"):
        if self._sel_pt < 0 or not self._obj_id:
            return
        canvas = ctx.store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(self._obj_id)
        if not obj:
            return
        payload = obj.payload
        if len(payload.points) <= 2:
            return   # не удаляем если осталось ≤2 точек

        import copy as _cp
        new_payload = _cp.deepcopy(payload)
        new_payload.points.pop(self._sel_pt)
        _apply_payload(obj, new_payload)
        self._sel_pt = max(0, self._sel_pt - 1)
        ctx.store.document_changed.emit()
        self._rebuild_overlay(ctx)

    # -----------------------------------------------------------------------
    # Overlay (визуальные ручки)
    # -----------------------------------------------------------------------

    def _clear_overlay(self, ctx: "ToolContext"):
        for item in self._anchors + self._ctrls + self._tangents:
            try:
                if item.scene() is ctx.scene:
                    ctx.scene.removeItem(item)
            except (RuntimeError, Exception):
                pass
        self._anchors.clear()
        self._ctrls.clear()
        self._tangents.clear()

        if self._preview_item:
            try:
                ctx.scene.removeItem(self._preview_item)
            except Exception:
                pass
            self._preview_item = None

    def _rebuild_overlay(self, ctx: "ToolContext"):
        """Полное пересоздание overlay из текущего payload."""
        self._clear_overlay(ctx)
        if not self._obj_id:
            return

        canvas = ctx.store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(self._obj_id)
        if not obj:
            return
        payload = obj.payload

        for i, pt in enumerate(payload.points):
            is_sel = (i == self._sel_pt)

            # Anchor
            anc = AnchorItem(i)
            anc.setPos(pt.x, pt.y)
            if is_sel:
                anc.setBrush(QBrush(COL_ANCHOR_SEL))
                anc.setPen(QPen(COL_ANCHOR, 1.5))
            ctx.scene.addItem(anc)
            self._anchors.append(anc)

            # Показываем ручки только для выделенной точки (или всех если редактируем)
            show_ctrls = not self._drawing and (
                is_sel or self._sel_pt == -1)

            if show_ctrls:
                # cx1 handle
                if (pt.cx1, pt.cy1) != (pt.x, pt.y):
                    tl1 = TangentLine()
                    tl1.setLine(pt.x, pt.y, pt.cx1, pt.cy1)
                    ctx.scene.addItem(tl1)
                    self._tangents.append(tl1)

                    c1 = CtrlItem(i, "cx1")
                    c1.setPos(pt.cx1, pt.cy1)
                    ctx.scene.addItem(c1)
                    self._ctrls.append(c1)

                # cx2 handle
                if (pt.cx2, pt.cy2) != (pt.x, pt.y):
                    tl2 = TangentLine()
                    tl2.setLine(pt.x, pt.y, pt.cx2, pt.cy2)
                    ctx.scene.addItem(tl2)
                    self._tangents.append(tl2)

                    c2 = CtrlItem(i, "cx2")
                    c2.setPos(pt.cx2, pt.cy2)
                    ctx.scene.addItem(c2)
                    self._ctrls.append(c2)

    def _update_overlay_positions(self, ctx: "ToolContext"):
        """Быстрое обновление позиций существующих overlay items."""
        if not self._obj_id:
            return
        canvas = ctx.store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(self._obj_id)
        if not obj:
            return
        payload = obj.payload

        for anc in self._anchors:
            if anc.pt_idx < len(payload.points):
                pt = payload.points[anc.pt_idx]
                anc.setPos(pt.x, pt.y)

        for ctrl in self._ctrls:
            if ctrl.pt_idx < len(payload.points):
                pt = payload.points[ctrl.pt_idx]
                if ctrl.which == "cx1":
                    ctrl.setPos(pt.cx1, pt.cy1)
                else:
                    ctrl.setPos(pt.cx2, pt.cy2)

        # Tangent lines
        tidx = 0
        for i, pt in enumerate(payload.points):
            has_c1 = (pt.cx1, pt.cy1) != (pt.x, pt.y)
            has_c2 = (pt.cx2, pt.cy2) != (pt.x, pt.y)
            if has_c1 and tidx < len(self._tangents):
                self._tangents[tidx].setLine(pt.x, pt.y, pt.cx1, pt.cy1)
                tidx += 1
            if has_c2 and tidx < len(self._tangents):
                self._tangents[tidx].setLine(pt.x, pt.y, pt.cx2, pt.cy2)
                tidx += 1


    def _insert_point_at(self, pos: QPointF, obj, ctx: "ToolContext"):
        """Вставляет новую точку в позиции pos (в конец пути)."""
        import copy as _cp
        payload = obj.payload
        from domain.models import BezierPoint
        new_pt = BezierPoint(
            x=pos.x(), y=pos.y(),
            cx1=pos.x()-30, cy1=pos.y(),
            cx2=pos.x()+30, cy2=pos.y(),
        )
        new_payload = _cp.deepcopy(payload)
        new_payload.points.append(new_pt)
        _apply_payload(obj, new_payload)
        self._sel_pt = len(obj.payload.points) - 1
        ctx.store.document_changed.emit()
        self._rebuild_overlay(ctx)
        _notify_context_toolbar(ctx)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dist(a: QPointF, b: QPointF) -> float:
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def _apply_payload(obj, new_payload):
    """Применяет новый payload к объекту (прямая мутация — без команды для drag)."""
    obj.payload = new_payload


def _notify_context_toolbar(ctx: "ToolContext"):
    """Обновляет ContextToolbarManager если он доступен через view."""
    try:
        view = ctx.view
        parent = view.parent()
        while parent:
            from ui.context_toolbar import ContextToolbarManager
            mgr = parent.findChild(ContextToolbarManager)
            if mgr:
                mgr.refresh_active()
                break
            parent = parent.parent()
    except Exception:
        pass
