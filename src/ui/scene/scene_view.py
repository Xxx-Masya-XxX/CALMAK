"""
SceneView — интерактивный холст.
Делегирует ВСЕ события мыши активному инструменту через ToolManager.
Сам не содержит логики перемещения/вращения/масштабирования.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QRectF, QPointF, QPoint
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem,
                                QGraphicsRectItem, QSizePolicy)

from domain.models import ObjectType
from rendering.scene_renderer import SceneRenderer, SceneItemRegistry
from tools.tool_manager import ToolManager, ToolContext, TOOL_MOVE

if TYPE_CHECKING:
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController


# ---------------------------------------------------------------------------
# Selection overlay
# ---------------------------------------------------------------------------

class SelectionOverlay(QGraphicsRectItem):
    def __init__(self):
        super().__init__()
        self.setZValue(9999)
        # self.setPen(QPen(QColor("#4A9EFF"), 1.5, Qt.DashLine))
        # self.setBrush(QBrush(Qt.transparent))
        # self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        # self.setFlag(QGraphicsItem.ItemIsMovable, False)
        # self.setVisible(False)


# ---------------------------------------------------------------------------
# SceneView
# ---------------------------------------------------------------------------

class SceneView(QGraphicsView):
    def __init__(self, store: "EditorStore",
                 controller: "EditorController",
                 tool_manager: ToolManager):
        super().__init__()
        self._store       = store
        self._controller  = controller
        self._tool_manager = tool_manager

        self._scene    = QGraphicsScene(self)
        self._registry = SceneItemRegistry()

        self.setScene(self._scene)
        self._setup_view()

        # Pan state (средняя кнопка / Alt — всегда работает независимо от инструмента)
        self._panning   = False
        self._pan_start = QPoint()

        # Overlay создаётся ДО renderer
        self._overlay = SelectionOverlay()
        self._scene.addItem(self._overlay)

        # Renderer
        self._renderer = SceneRenderer(self._scene, self._registry, store,
                                       overlay=self._overlay)

        # Передаём контекст в ToolManager
        ctx = ToolContext(store, controller, self._scene, self._registry, self)
        tool_manager.set_context(ctx)

        # Store signals
        store.document_changed.connect(self._on_document_changed)
        store.selection_changed.connect(self._on_selection_changed)
        store.canvas_switched.connect(self._on_canvas_switched)

        self._renderer.full_sync()
        self._fit_canvas()

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------

    def _setup_view(self):
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform |
                            QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor("#2D2D3A")))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _fit_canvas(self):
        canvas = self._store.active_canvas
        if canvas:
            m = 60
            self.fitInView(QRectF(-m, -m, canvas.width + m*2, canvas.height + m*2),
                           Qt.KeepAspectRatio)

    # -----------------------------------------------------------------------
    # Store slots
    # -----------------------------------------------------------------------

    def _on_document_changed(self):
        self._renderer.full_sync()
        self._sync_selection_overlay()
        self._scene.update()

    def _on_selection_changed(self, ids, active_id):
        for obj_id, item in self._registry._id_to_item.items():
            item.setSelected(obj_id in ids)
        self._sync_selection_overlay()

    def _on_canvas_switched(self, canvas_id):
        self._renderer.full_sync()
        self._fit_canvas()

    # -----------------------------------------------------------------------
    # Selection overlay
    # -----------------------------------------------------------------------

    def _overlay_alive(self) -> bool:
        try:
            self._overlay.scene()
            return True
        except RuntimeError:
            return False

    def _sync_selection_overlay(self):
        if not self._overlay_alive():
            return
        ids = self._store.selection.selected_ids
        canvas = self._store.active_canvas
        if not ids or not canvas:
            self._overlay.setVisible(False)
            return
        xs, ys, x2s, y2s = [], [], [], []
        for oid in ids:
            obj = canvas.objects.get(oid)
            if obj:
                t = obj.transform
                xs.append(t.x);            ys.append(t.y)
                x2s.append(t.x + t.width); y2s.append(t.y + t.height)
        if not xs:
            self._overlay.setVisible(False)
            return
        pad = 3
        self._overlay.setRect(min(xs)-pad, min(ys)-pad,
                               max(x2s)-min(xs)+pad*2, max(y2s)-min(ys)+pad*2)
        self._overlay.setVisible(True)

    def _sync_selection_overlay_live(self):
        """Для live drag — читаем позиции из items."""
        if not self._overlay_alive():
            return
        ids = self._store.selection.selected_ids
        if not ids:
            self._overlay.setVisible(False)
            return
        xs, ys, x2s, y2s = [], [], [], []
        for oid in ids:
            item = self._registry.get_item(oid)
            if item:
                r = item.boundingRect()
                p = item.pos()
                xs.append(p.x());               ys.append(p.y())
                x2s.append(p.x()+r.width()); y2s.append(p.y()+r.height())
        if xs:
            pad = 3
            self._overlay.setRect(min(xs)-pad, min(ys)-pad,
                                   max(x2s)-min(xs)+pad*2, max(y2s)-min(ys)+pad*2)
            self._overlay.setVisible(True)

    # -----------------------------------------------------------------------
    # Mouse — делегируем ToolManager. Pan всегда работает поверх.
    # -----------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        # Средняя кнопка / Alt = pan (всегда, независимо от инструмента)
        if (event.button() == Qt.MiddleButton or
                event.modifiers() & Qt.AltModifier):
            self._panning   = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        self._tool_manager.mouse_press(event)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        self._tool_manager.mouse_move(event)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton or self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        self._tool_manager.mouse_release(event)
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        pos_scene = self.mapToScene(event.pos())
        for item in self._scene.items(pos_scene):
            if item is self._overlay:
                continue
            obj_id = self._registry.get_id(item)
            if obj_id:
                canvas = self._store.active_canvas
                obj = canvas.objects.get(obj_id) if canvas else None
                if obj and obj.type == ObjectType.TEXT:
                    from ui.dialogs.text_dialog import TextEditDialog
                    dlg = TextEditDialog(obj, self)
                    if dlg.exec():
                        self._controller.update_properties(
                            obj_id, {"payload_text": dlg.get_text()})
                break
        event.accept()

    # -----------------------------------------------------------------------
    # Wheel = zoom
    # -----------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    # -----------------------------------------------------------------------
    # Key events
    # -----------------------------------------------------------------------

    def keyPressEvent(self, event):
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        canvas = self._store.active_canvas
        ids = list(self._store.selection.selected_ids)

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._controller.delete_selected()

        elif event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            if canvas:
                top = _filter_top_level(canvas, set(ids))
                for oid in top:
                    obj = canvas.objects.get(oid)
                    if obj and not obj.locked:
                        dx = (-step if event.key() == Qt.Key_Left else
                               step if event.key() == Qt.Key_Right else 0)
                        dy = (-step if event.key() == Qt.Key_Up else
                               step if event.key() == Qt.Key_Down else 0)
                        self._controller.move_object(
                            oid, obj.transform.x + dx, obj.transform.y + dy)

        elif event.key() == Qt.Key_0 and event.modifiers() & Qt.ControlModifier:
            self._fit_canvas()

        else:
            super().keyPressEvent(event)

    # -----------------------------------------------------------------------
    # Public helpers
    # -----------------------------------------------------------------------

    def fit_view(self):   self._fit_canvas()
    def zoom_in(self):    self.scale(1.2, 1.2)
    def zoom_out(self):   self.scale(1/1.2, 1/1.2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_top_level(canvas, selected_ids: set) -> list[str]:
    result = []
    for oid in selected_ids:
        obj = canvas.objects.get(oid)
        if not obj:
            continue
        ancestor = obj.parent_id
        dominated = False
        while ancestor:
            if ancestor in selected_ids:
                dominated = True
                break
            anc = canvas.objects.get(ancestor)
            ancestor = anc.parent_id if anc else None
        if not dominated:
            result.append(oid)
    return result
