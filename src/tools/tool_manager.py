"""
Система инструментов редактора.

Инструменты:
  SELECT  — выделение (rubber band), без трансформаций
  MOVE    — перемещение выделенных объектов (default)
  ROTATE  — вращение объекта мышью
  SCALE   — масштабирование объекта мышью (resize)

Каждый инструмент получает события мыши от SceneView
и делает только своё дело.

Переключение: ToolManager.set_tool(tool_id)
SceneView всегда делегирует события активному инструменту.
"""
from __future__ import annotations
import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QPointF, QPoint, Signal, QObject
from PySide6.QtGui import (QColor, QPen, QBrush, QCursor, QPainter,
                            QMouseEvent, QWheelEvent)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsRectItem,
                                QGraphicsEllipseItem, QGraphicsLineItem,
                                QRubberBand, QAbstractItemView)
from ui.constants import C

if TYPE_CHECKING:
    from PySide6.QtCore import QRect
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController
    from rendering.scene_renderer import SceneItemRegistry
    from PySide6.QtWidgets import QGraphicsScene
    from ui.scene.scene_view import SceneView


# ---------------------------------------------------------------------------
# Tool IDs
# ---------------------------------------------------------------------------

TOOL_SELECT = "select"
TOOL_MOVE   = "move"
TOOL_ROTATE = "rotate"
TOOL_SCALE  = "scale"


# ---------------------------------------------------------------------------
# ToolContext — что доступно инструменту
# ---------------------------------------------------------------------------

class ToolContext:
    def __init__(self, store: "EditorStore", controller: "EditorController",
                 scene: "QGraphicsScene", registry: "SceneItemRegistry",
                 view: "SceneView"):
        self.store      = store
        self.controller = controller
        self.scene      = scene
        self.registry   = registry
        self.view       = view


# ---------------------------------------------------------------------------
# BaseTool
# ---------------------------------------------------------------------------

class BaseTool(ABC):
    tool_id: str = "base"
    cursor:  Qt.CursorShape = Qt.ArrowCursor

    def activate(self, ctx: ToolContext):
        ctx.view.setCursor(self.cursor)

    def deactivate(self, ctx: ToolContext):
        ctx.view.setCursor(Qt.ArrowCursor)

    def mouse_press(self, event: QMouseEvent, ctx: ToolContext): ...
    def mouse_move(self, event: QMouseEvent, ctx: ToolContext): ...
    def mouse_release(self, event: QMouseEvent, ctx: ToolContext): ...


# ---------------------------------------------------------------------------
# SelectTool — только rubber band выделение
# ---------------------------------------------------------------------------

class SelectTool(BaseTool):
    tool_id = TOOL_SELECT
    cursor  = Qt.ArrowCursor

    def __init__(self):
        self._rubber_band  = None
        self._rubber_start = QPoint()
        self._banding      = False

    def mouse_press(self, event: QMouseEvent, ctx: ToolContext):
        if event.button() != Qt.LeftButton:
            return
        multi = bool(event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier))
        pos_scene = ctx.view.mapToScene(event.pos())

        items = ctx.scene.items(pos_scene)
        overlay = ctx.view._overlay
        clickable = [i for i in items
                     if i is not overlay
                     and bool(i.flags() & QGraphicsItem.ItemIsSelectable)]
        if clickable:
            obj_id = ctx.registry.get_id(clickable[0])
            if obj_id:
                if multi:
                    ctx.controller.toggle_selection(obj_id)
                else:
                    ctx.controller.select_one(obj_id)
        else:
            if not multi:
                ctx.controller.clear_selection()
            self._banding = True
            self._rubber_start = event.pos()

    def mouse_move(self, event: QMouseEvent, ctx: ToolContext):
        if not self._banding:
            return
        from PySide6.QtCore import QRect
        from PySide6.QtWidgets import QRubberBand
        if self._rubber_band is None:
            self._rubber_band = QRubberBand(QRubberBand.Rectangle,
                                             ctx.view.viewport())
        rect = QRect(self._rubber_start, event.pos()).normalized()
        self._rubber_band.setGeometry(rect)
        self._rubber_band.show()

    def mouse_release(self, event: QMouseEvent, ctx: ToolContext):
        if self._banding and self._rubber_band:
            scene_rect = ctx.view.mapToScene(
                self._rubber_band.geometry()).boundingRect()
            self._rubber_band.hide()
            self._rubber_band = None
            items = ctx.scene.items(scene_rect, Qt.IntersectsItemShape)
            overlay = ctx.view._overlay
            ids = [ctx.registry.get_id(i) for i in items
                   if i is not overlay
                   and bool(i.flags() & QGraphicsItem.ItemIsSelectable)]
            ids = [i for i in ids if i]
            if ids:
                ctx.controller.select(ids)
        self._banding = False

    def deactivate(self, ctx: ToolContext):
        if self._rubber_band:
            self._rubber_band.hide()
            self._rubber_band = None
        self._banding = False
        super().deactivate(ctx)


# ---------------------------------------------------------------------------
# MoveTool — перемещение
# ---------------------------------------------------------------------------

class MoveTool(BaseTool):
    tool_id = TOOL_MOVE
    cursor  = Qt.SizeAllCursor

    def __init__(self):
        self._dragging    = False
        self._drag_start  = QPointF()
        self._origins: dict[str, QPointF] = {}
        # rubber band для выделения
        self._rubber_band  = None
        self._rubber_start = QPoint()
        self._banding      = False

    def mouse_press(self, event: QMouseEvent, ctx: ToolContext):
        if event.button() != Qt.LeftButton:
            return
        multi = bool(event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier))
        pos_scene = ctx.view.mapToScene(event.pos())

        items = ctx.scene.items(pos_scene)
        overlay = ctx.view._overlay
        clickable = [i for i in items
                     if i is not overlay
                     and bool(i.flags() & QGraphicsItem.ItemIsSelectable)]

        if clickable:
            obj_id = ctx.registry.get_id(clickable[0])
            if obj_id:
                if multi:
                    ctx.controller.toggle_selection(obj_id)
                elif obj_id not in ctx.store.selection.selected_ids:
                    ctx.controller.select_one(obj_id)

                # Подготовить drag origins
                self._dragging   = True
                self._drag_start = pos_scene
                self._origins.clear()
                canvas = ctx.store.active_canvas
                if canvas:
                    all_ids = _collect_with_children(
                        canvas, ctx.store.selection.selected_ids)
                    for sid in all_ids:
                        obj = canvas.objects.get(sid)
                        if obj:
                            self._origins[sid] = QPointF(
                                obj.transform.x, obj.transform.y)
        else:
            if not multi:
                ctx.controller.clear_selection()
            self._banding = True
            self._rubber_start = event.pos()

    def mouse_move(self, event: QMouseEvent, ctx: ToolContext):
        pos_scene = ctx.view.mapToScene(event.pos())

        if self._dragging and self._origins:
            delta = pos_scene - self._drag_start
            for obj_id, origin in self._origins.items():
                item = ctx.registry.get_item(obj_id)
                if item:
                    item.setPos(origin.x() + delta.x(),
                                origin.y() + delta.y())
            ctx.view._sync_selection_overlay_live()
            return

        if self._banding:
            from PySide6.QtCore import QRect
            from PySide6.QtWidgets import QRubberBand
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Rectangle,
                                                 ctx.view.viewport())
            rect = QRect(self._rubber_start, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)
            self._rubber_band.show()

    def mouse_release(self, event: QMouseEvent, ctx: ToolContext):
        if self._dragging and self._origins:
            pos_scene = ctx.view.mapToScene(event.pos())
            delta = pos_scene - self._drag_start
            canvas = ctx.store.active_canvas
            if canvas and (abs(delta.x()) > 1 or abs(delta.y()) > 1):
                top = _filter_top_level(canvas, set(ctx.store.selection.selected_ids))
                for obj_id in top:
                    origin = self._origins.get(obj_id)
                    if origin is None:
                        continue
                    obj = canvas.objects.get(obj_id)
                    if obj and not obj.locked:
                        ctx.controller.move_object(
                            obj_id,
                            round(origin.x() + delta.x(), 2),
                            round(origin.y() + delta.y(), 2))
        self._dragging = False
        self._origins.clear()

        if self._banding and self._rubber_band:
            scene_rect = ctx.view.mapToScene(
                self._rubber_band.geometry()).boundingRect()
            self._rubber_band.hide()
            self._rubber_band = None
            items = ctx.scene.items(scene_rect, Qt.IntersectsItemShape)
            overlay = ctx.view._overlay
            ids = [ctx.registry.get_id(i) for i in items
                   if i is not overlay
                   and bool(i.flags() & QGraphicsItem.ItemIsSelectable)]
            ids = [i for i in ids if i]
            if ids:
                ctx.controller.select(ids)
        self._banding = False

    def deactivate(self, ctx: ToolContext):
        self._dragging = False
        self._origins.clear()
        if self._rubber_band:
            self._rubber_band.hide()
            self._rubber_band = None
        self._banding = False
        super().deactivate(ctx)


# ---------------------------------------------------------------------------
# RotateTool — вращение вокруг центра объекта
# ---------------------------------------------------------------------------

class RotateTool(BaseTool):
    tool_id = TOOL_ROTATE
    cursor  = Qt.CrossCursor

    def __init__(self):
        self._rotating      = False
        self._obj_id        = ""
        self._center        = QPointF()
        self._start_angle   = 0.0
        self._orig_rotation = 0.0
        # Визуальный индикатор
        self._indicator: QGraphicsLineItem | None = None

    def activate(self, ctx: ToolContext):
        ctx.view.setCursor(Qt.CrossCursor)

    def deactivate(self, ctx: ToolContext):
        self._clear_indicator(ctx)
        self._rotating = False
        super().deactivate(ctx)

    def mouse_press(self, event: QMouseEvent, ctx: ToolContext):
        if event.button() != Qt.LeftButton:
            return
        pos_scene = ctx.view.mapToScene(event.pos())

        # Выбрать объект под курсором или использовать уже выделенный
        items = ctx.scene.items(pos_scene)
        overlay = ctx.view._overlay
        clickable = [i for i in items
                     if i is not overlay
                     and bool(i.flags() & QGraphicsItem.ItemIsSelectable)]

        if clickable:
            obj_id = ctx.registry.get_id(clickable[0])
        else:
            obj_id = ctx.store.selection.active_id

        if not obj_id:
            return

        canvas = ctx.store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(obj_id)
        if not obj or obj.locked:
            return

        ctx.controller.select_one(obj_id)
        self._obj_id = obj_id
        self._rotating = True
        t = obj.transform
        self._center = QPointF(t.x + t.width / 2, t.y + t.height / 2)
        self._start_angle   = _angle(self._center, pos_scene)
        self._orig_rotation = t.rotation
        self._draw_indicator(ctx, pos_scene)

    def mouse_move(self, event: QMouseEvent, ctx: ToolContext):
        if not self._rotating:
            return
        pos_scene = ctx.view.mapToScene(event.pos())
        current_angle = _angle(self._center, pos_scene)
        delta = current_angle - self._start_angle

        # Обновить визуально item напрямую
        item = ctx.registry.get_item(self._obj_id)
        if item:
            item.setTransformOriginPoint(
                item.boundingRect().center())
            canvas = ctx.store.active_canvas
            if canvas:
                obj = canvas.objects.get(self._obj_id)
                if obj:
                    new_rot = (self._orig_rotation + delta) % 360
                    item.setRotation(new_rot)
        self._update_indicator(ctx, pos_scene)

    def mouse_release(self, event: QMouseEvent, ctx: ToolContext):
        if not self._rotating:
            return
        pos_scene = ctx.view.mapToScene(event.pos())
        current_angle = _angle(self._center, pos_scene)
        delta = current_angle - self._start_angle
        new_rot = round((self._orig_rotation + delta) % 360, 2)

        ctx.controller.update_properties(
            self._obj_id, {"transform.rotation": new_rot})

        self._rotating = False
        self._clear_indicator(ctx)

    def _draw_indicator(self, ctx: ToolContext, pos: QPointF):
        self._clear_indicator(ctx)
        line = QGraphicsLineItem(
            self._center.x(), self._center.y(), pos.x(), pos.y())
        line.setPen(QPen(C.ROTATE_INDICATOR, 1.5, Qt.DashLine))
        line.setZValue(9998)
        ctx.scene.addItem(line)
        self._indicator = line

    def _update_indicator(self, ctx: ToolContext, pos: QPointF):
        if self._indicator:
            self._indicator.setLine(
                self._center.x(), self._center.y(), pos.x(), pos.y())

    def _clear_indicator(self, ctx: ToolContext):
        if self._indicator:
            try:
                ctx.scene.removeItem(self._indicator)
            except Exception:
                pass
            self._indicator = None


# ---------------------------------------------------------------------------
# ScaleTool — масштабирование (resize) тащим за угол/сторону
# ---------------------------------------------------------------------------

HANDLE_CURSORS = {
    "nw": Qt.SizeFDiagCursor, "ne": Qt.SizeBDiagCursor,
    "sw": Qt.SizeBDiagCursor, "se": Qt.SizeFDiagCursor,
    "n":  Qt.SizeVerCursor,   "s":  Qt.SizeVerCursor,
    "w":  Qt.SizeHorCursor,   "e":  Qt.SizeHorCursor,
}
HANDLE_SIZE = 10


class ScaleTool(BaseTool):
    tool_id = TOOL_SCALE
    cursor  = Qt.SizeAllCursor

    def __init__(self):
        self._resizing   = False
        self._obj_id     = ""
        self._handle     = ""
        self._start_pos  = QPointF()
        self._orig_rect  = (0.0, 0.0, 0.0, 0.0)   # x, y, w, h
        self._handles: list[QGraphicsRectItem] = []
        self._sel_slot = None  # ссылка на подключённый слот для дисконнекта

    def activate(self, ctx: ToolContext):
        ctx.view.setCursor(Qt.SizeAllCursor)
        # Сохраняем ссылку на слот чтобы потом дисконнектить ТОЛЬКО его
        self._sel_slot = lambda ids, aid: self._refresh_handles(ctx)
        ctx.store.selection_changed.connect(self._sel_slot)
        self._refresh_handles(ctx)

    def deactivate(self, ctx: ToolContext):
        self._clear_handles(ctx)
        self._resizing = False
        # Дисконнектим ТОЛЬКО свой слот, не все подписчики
        if self._sel_slot is not None:
            try:
                ctx.store.selection_changed.disconnect(self._sel_slot)
            except Exception:
                pass
            self._sel_slot = None
        super().deactivate(ctx)

    # ---- handles ----

    def _refresh_handles(self, ctx: ToolContext):
        self._clear_handles(ctx)
        aid = ctx.store.selection.active_id
        if not aid:
            return
        canvas = ctx.store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(aid)
        if not obj:
            return
        t = obj.transform
        self._draw_handles(ctx, t.x, t.y, t.width, t.height)

    def _draw_handles(self, ctx: ToolContext,
                      x: float, y: float, w: float, h: float):
        hs = HANDLE_SIZE
        positions = {
            "nw": (x - hs/2,      y - hs/2),
            "n":  (x + w/2 - hs/2, y - hs/2),
            "ne": (x + w - hs/2,  y - hs/2),
            "w":  (x - hs/2,      y + h/2 - hs/2),
            "e":  (x + w - hs/2,  y + h/2 - hs/2),
            "sw": (x - hs/2,      y + h - hs/2),
            "s":  (x + w/2 - hs/2, y + h - hs/2),
            "se": (x + w - hs/2,  y + h - hs/2),
        }
        for name, (hx, hy) in positions.items():
            h_item = QGraphicsRectItem(hx, hy, hs, hs)
            h_item.setBrush(QBrush(C.SCALE_HANDLE_BG))
            h_item.setPen(QPen(C.SCALE_HANDLE_FG, 1.5))
            h_item.setZValue(9998)
            h_item.setData(0, f"handle:{name}")
            ctx.scene.addItem(h_item)
            self._handles.append(h_item)

    def _clear_handles(self, ctx: ToolContext):
        for h in self._handles:
            try:
                ctx.scene.removeItem(h)
            except Exception:
                pass
        self._handles.clear()

    def _handle_at(self, pos: QPointF) -> str:
        """Возвращает имя ручки под курсором или ''."""
        for h in self._handles:
            if h.rect().contains(pos):
                data = h.data(0)
                if data and data.startswith("handle:"):
                    return data[7:]
        return ""

    # ---- mouse ----

    def mouse_press(self, event: QMouseEvent, ctx: ToolContext):
        if event.button() != Qt.LeftButton:
            return
        pos_scene = ctx.view.mapToScene(event.pos())

        handle = self._handle_at(pos_scene)
        if handle:
            aid = ctx.store.selection.active_id
            if not aid:
                return
            canvas = ctx.store.active_canvas
            obj = canvas.objects.get(aid) if canvas else None
            if not obj or obj.locked:
                return
            t = obj.transform
            self._resizing  = True
            self._obj_id    = aid
            self._handle    = handle
            self._start_pos = pos_scene
            self._orig_rect = (t.x, t.y, t.width, t.height)
            return

        # Нет ручки — попробовать выделить объект
        items = ctx.scene.items(pos_scene)
        overlay = ctx.view._overlay
        clickable = [i for i in items
                     if i is not overlay
                     and bool(i.flags() & QGraphicsItem.ItemIsSelectable)
                     and i not in self._handles]
        if clickable:
            obj_id = ctx.registry.get_id(clickable[0])
            if obj_id:
                ctx.controller.select_one(obj_id)
                self._refresh_handles(ctx)
        else:
            ctx.controller.clear_selection()
            self._clear_handles(ctx)

    def mouse_move(self, event: QMouseEvent, ctx: ToolContext):
        pos_scene = ctx.view.mapToScene(event.pos())

        # Обновить курсор при наведении на ручку
        handle = self._handle_at(pos_scene)
        if handle and not self._resizing:
            ctx.view.setCursor(HANDLE_CURSORS.get(handle, Qt.SizeAllCursor))
        elif not self._resizing:
            ctx.view.setCursor(Qt.ArrowCursor)

        if not self._resizing:
            return

        dx = pos_scene.x() - self._start_pos.x()
        dy = pos_scene.y() - self._start_pos.y()
        ox, oy, ow, oh = self._orig_rect
        nx, ny, nw, nh = ox, oy, ow, oh

        h = self._handle
        if "e" in h: nw = max(10, ow + dx)
        if "s" in h: nh = max(10, oh + dy)
        if "w" in h: nx = ox + dx; nw = max(10, ow - dx)
        if "n" in h: ny = oy + dy; nh = max(10, oh - dy)

        # Live preview: двигаем item напрямую
        item = ctx.registry.get_item(self._obj_id)
        if item:
            from domain.models import ObjectType
            canvas = ctx.store.active_canvas
            obj = canvas.objects.get(self._obj_id) if canvas else None
            if obj:
                item.setPos(nx, ny)
                from PySide6.QtCore import QRectF
                if hasattr(item, 'setRect'):
                    item.setRect(QRectF(0, 0, nw, nh))
                elif hasattr(item, 'setTextWidth'):
                    item.setTextWidth(nw)
        # Обновить ручки
        self._clear_handles(ctx)
        self._draw_handles(ctx, nx, ny, nw, nh)

    def mouse_release(self, event: QMouseEvent, ctx: ToolContext):
        if not self._resizing:
            return
        pos_scene = ctx.view.mapToScene(event.pos())
        dx = pos_scene.x() - self._start_pos.x()
        dy = pos_scene.y() - self._start_pos.y()
        ox, oy, ow, oh = self._orig_rect
        nx, ny, nw, nh = ox, oy, ow, oh

        h = self._handle
        if "e" in h: nw = max(10, ow + dx)
        if "s" in h: nh = max(10, oh + dy)
        if "w" in h: nx = ox + dx; nw = max(10, ow - dx)
        if "n" in h: ny = oy + dy; nh = max(10, oh - dy)

        ctx.controller.resize_object(
            self._obj_id, round(nx, 2), round(ny, 2),
            round(nw, 2), round(nh, 2))

        self._resizing = False
        self._refresh_handles(ctx)


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------

class ToolManager(QObject):
    tool_changed = Signal(str)   # новый tool_id

    def __init__(self):
        super().__init__()
        self._tools: dict[str, BaseTool] = {
            TOOL_SELECT: SelectTool(),
            TOOL_MOVE:   MoveTool(),
            TOOL_ROTATE: RotateTool(),
            TOOL_SCALE:  ScaleTool(),
        }
        self._active_id  = TOOL_MOVE
        self._ctx: ToolContext | None = None

    def set_context(self, ctx: ToolContext):
        self._ctx = ctx
        self.active_tool.activate(ctx)

    @property
    def active_tool(self) -> BaseTool:
        return self._tools[self._active_id]

    @property
    def active_tool_id(self) -> str:
        return self._active_id

    def set_tool(self, tool_id: str):
        if tool_id not in self._tools:
            return
        if self._ctx and self._active_id != tool_id:
            self.active_tool.deactivate(self._ctx)
        self._active_id = tool_id
        if self._ctx:
            self.active_tool.activate(self._ctx)
        self.tool_changed.emit(tool_id)
        # Всегда переэмитируем selection_changed — панель свойств
        # должна обновиться при смене инструмента (например Scale показывает
        # ручки, Rotate — другой курсор, и панель должна это отразить)
        if self._ctx:
            sel = self._ctx.store.selection
            self._ctx.store.selection_changed.emit(
                list(sel.selected_ids), sel.active_id)

    def mouse_press(self, event: QMouseEvent):
        if self._ctx:
            self.active_tool.mouse_press(event, self._ctx)

    def mouse_move(self, event: QMouseEvent):
        if self._ctx:
            self.active_tool.mouse_move(event, self._ctx)

    def mouse_release(self, event: QMouseEvent):
        if self._ctx:
            self.active_tool.mouse_release(event, self._ctx)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _angle(center: QPointF, point: QPointF) -> float:
    """Угол в градусах от center до point."""
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    return math.degrees(math.atan2(dy, dx))


def _collect_with_children(canvas, root_ids) -> list[str]:
    result = []; visited = set()
    def walk(oid):
        if oid in visited: return
        visited.add(oid); result.append(oid)
        obj = canvas.objects.get(oid)
        if obj:
            for cid in obj.children_ids: walk(cid)
    for oid in root_ids: walk(oid)
    return result


def _filter_top_level(canvas, selected_ids: set) -> list[str]:
    result = []
    for oid in selected_ids:
        obj = canvas.objects.get(oid)
        if not obj: continue
        ancestor = obj.parent_id; dominated = False
        while ancestor:
            if ancestor in selected_ids: dominated = True; break
            anc = canvas.objects.get(ancestor)
            ancestor = anc.parent_id if anc else None
        if not dominated: result.append(oid)
    return result
