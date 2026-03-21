"""
SceneView — интерактивный холст с правильной навигацией.

Навигация:
  • Scroll колёсико         — зум к позиции курсора (без Ctrl)
  • Ctrl+Scroll             — зум к позиции курсора (совместимость)
  • Средняя кнопка / Alt+drag — pan
  • Ctrl+0 / кнопка Fit     — вписать канвас в окно
  • Слайдеры               — всегда видимы, перемещение по сцене

Поведение зума:
  • Зум всегда к курсору мыши
  • Позиция не сбрасывается
  • Если канвас меньше viewport — центрируется
  • Если канвас больше viewport — можно прокручивать слайдерами
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QRectF, QPointF, QPoint, QTimer
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush,
                            QWheelEvent, QMouseEvent, QTransform)
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem,
                                QGraphicsRectItem, QSizePolicy)

from domain.models import ObjectType
from rendering.scene_renderer import SceneRenderer, SceneItemRegistry
from tools.tool_manager import ToolManager, ToolContext
from ui.constants import C, menu_stylesheet
from ui.theme import theme_manager

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
        self.setPen(QPen(C.SELECTION_BOX, 1.5, Qt.DashLine))
        self.setBrush(QBrush(Qt.transparent))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setVisible(False)


# ---------------------------------------------------------------------------
# SceneView
# ---------------------------------------------------------------------------

class SceneView(QGraphicsView):

    # Пределы зума
    MIN_ZOOM = 0.05   #  5%
    MAX_ZOOM = 32.0   # 3200%
    ZOOM_STEP = 1.12  # ~12% за шаг колеса

    def __init__(self, store: "EditorStore",
                 controller: "EditorController",
                 tool_manager: ToolManager):
        super().__init__()
        self._store        = store
        self._controller   = controller
        self._tool_manager = tool_manager

        self._scene    = QGraphicsScene(self)
        self._registry = SceneItemRegistry()
        self.setScene(self._scene)

        self._setup_view()

        # Pan state
        self._panning   = False
        self._pan_start = QPoint()

        # Overlay ДО renderer
        self._overlay = SelectionOverlay()
        self._scene.addItem(self._overlay)

        # Renderer
        self._renderer = SceneRenderer(
            self._scene, self._registry, store, overlay=self._overlay)

        # Tool context
        ctx = ToolContext(store, controller, self._scene, self._registry, self)
        tool_manager.set_context(ctx)

        # Store signals
        store.document_changed.connect(self._on_document_changed)
        store.selection_changed.connect(self._on_selection_changed)
        store.canvas_switched.connect(self._on_canvas_switched)

        # Theme signal
        theme_manager.theme_changed.connect(self._on_theme_changed)

        # Первый рендер и центрирование
        self._renderer.full_sync()
        self._fit_canvas()

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------

    def _setup_view(self):
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.TextAntialiasing)

        self.setDragMode(QGraphicsView.NoDrag)

        # ВАЖНО: AnchorUnderMouse — зум всегда к курсору
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # Слайдеры всегда видимы
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.setBackgroundBrush(QBrush(C.SCENE_BG))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Большой scene rect — чтобы было куда двигаться
        self._scene_margin = 4000
        self._update_scene_rect()

    def _update_scene_rect(self):
        """
        Устанавливает sceneRect с запасом вокруг канваса.
        Это определяет диапазон слайдеров.
        """
        canvas = self._store.active_canvas
        m = self._scene_margin
        if canvas:
            self._scene.setSceneRect(
                -m, -m,
                canvas.width  + m * 2,
                canvas.height + m * 2)
        else:
            self._scene.setSceneRect(-m, -m, m * 2, m * 2)

    # -----------------------------------------------------------------------
    # Fit / Center
    # -----------------------------------------------------------------------

    def _fit_canvas(self):
        """Вписывает канвас в видимую область с небольшим отступом."""
        canvas = self._store.active_canvas
        if not canvas:
            return
        margin = 60
        fit_rect = QRectF(
            -margin, -margin,
            canvas.width  + margin * 2,
            canvas.height + margin * 2)
        self.fitInView(fit_rect, Qt.KeepAspectRatio)
        self._clamp_zoom()
        self._center_if_small()

    def _center_if_small(self):
        """
        Если канвас помещается в viewport целиком — центрируем его.
        Иначе оставляем текущую позицию.
        """
        canvas = self._store.active_canvas
        if not canvas:
            return
        # Размер канваса в экранных пикселях
        scale = self.transform().m11()  # текущий масштаб
        canvas_w_px = canvas.width  * scale
        canvas_h_px = canvas.height * scale
        vp = self.viewport().size()

        if canvas_w_px <= vp.width() and canvas_h_px <= vp.height():
            # Канвас меньше viewport — центрируем
            self.centerOn(QPointF(canvas.width / 2, canvas.height / 2))

    def _clamp_zoom(self):
        """Ограничивает масштаб в пределах MIN_ZOOM..MAX_ZOOM."""
        scale = self.transform().m11()
        if scale < self.MIN_ZOOM:
            factor = self.MIN_ZOOM / scale
            self.scale(factor, factor)
        elif scale > self.MAX_ZOOM:
            factor = self.MAX_ZOOM / scale
            self.scale(factor, factor)

    # -----------------------------------------------------------------------
    # Zoom — к курсору мыши
    # -----------------------------------------------------------------------

    def _zoom_at(self, factor: float, anchor_pos: QPoint):
        """
        Масштабирует сцену с якорем в точке anchor_pos (viewport coords).
        Позиция под курсором остаётся на месте.
        """
        current_scale = self.transform().m11()
        new_scale = current_scale * factor

        # Ограничиваем
        if new_scale < self.MIN_ZOOM:
            factor = self.MIN_ZOOM / current_scale
        elif new_scale > self.MAX_ZOOM:
            factor = self.MAX_ZOOM / current_scale

        if abs(factor - 1.0) < 1e-6:
            return

        # Запоминаем scene-позицию под курсором
        scene_pos_before = self.mapToScene(anchor_pos)

        self.scale(factor, factor)

        # Восстанавливаем: двигаем view так чтобы та же scene-точка
        # оказалась под курсором
        scene_pos_after = self.mapToScene(anchor_pos)
        delta = scene_pos_after - scene_pos_before
        self.translate(delta.x(), delta.y())

        self._center_if_small()

    def current_zoom_percent(self) -> int:
        return round(self.transform().m11() * 100)

    # -----------------------------------------------------------------------
    # Store slots
    # -----------------------------------------------------------------------

    def _on_theme_changed(self, name: str, t: dict):
        """Обновляет фон сцены при смене темы."""
        from PySide6.QtGui import QColor, QBrush
        self.setBackgroundBrush(QBrush(QColor(t.get("scene_bg", "#2D2D3A"))))
        self._scene.update()

    def _on_document_changed(self):
        self._renderer.full_sync()
        self._update_scene_rect()
        self._sync_selection_overlay()
        self._scene.update()

    def _on_selection_changed(self, ids, active_id):
        for obj_id, item in self._registry._id_to_item.items():
            item.setSelected(obj_id in ids)
        self._sync_selection_overlay()

    def _on_canvas_switched(self, canvas_id):
        self._renderer.full_sync()
        self._update_scene_rect()
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
        ids    = self._store.selection.selected_ids
        canvas = self._store.active_canvas
        if not ids or not canvas:
            self._overlay.setVisible(False)
            return
        xs, ys, x2s, y2s = [], [], [], []
        for oid in ids:
            obj = canvas.objects.get(oid)
            if obj:
                t = obj.transform
                xs.append(t.x);             ys.append(t.y)
                x2s.append(t.x + t.width); y2s.append(t.y + t.height)
        if not xs:
            self._overlay.setVisible(False)
            return
        pad = 3
        self._overlay.setRect(
            min(xs)-pad, min(ys)-pad,
            max(x2s)-min(xs)+pad*2, max(y2s)-min(ys)+pad*2)
        self._overlay.setVisible(True)

    def _sync_selection_overlay_live(self):
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
            self._overlay.setRect(
                min(xs)-pad, min(ys)-pad,
                max(x2s)-min(xs)+pad*2, max(y2s)-min(ys)+pad*2)
            self._overlay.setVisible(True)

    # -----------------------------------------------------------------------
    # Mouse
    # -----------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
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

    def contextMenuEvent(self, event):
        """Контекстное меню на сцене."""
        from PySide6.QtWidgets import QMenu
        pos_scene = self.mapToScene(event.pos())
        items = self._scene.items(pos_scene)
        overlay = self._overlay

        clickable = [i for i in items
                     if i is not overlay
                     and bool(i.flags() & QGraphicsItem.ItemIsSelectable)]

        menu = QMenu(self)
        menu.setStyleSheet(menu_stylesheet())

        if clickable:
            obj_id = self._registry.get_id(clickable[0])
            canvas = self._store.active_canvas
            obj    = canvas.objects.get(obj_id) if canvas else None

            if obj_id and obj_id not in self._store.selection.selected_ids:
                self._controller.select_one(obj_id)

            sel_count = len(self._store.selection.selected_ids)
            label = (obj.name if obj and sel_count == 1
                     else f"{sel_count} objects")

            title = menu.addAction(label)
            title.setEnabled(False)
            menu.addSeparator()

            menu.addAction("✂  Duplicate", self._controller.duplicate_selected)
            menu.addAction("🗑  Delete",   self._controller.delete_selected)
            menu.addSeparator()

            a_lock = menu.addAction("🔒  Lock")
            a_lock.setCheckable(True)
            if obj:
                a_lock.setChecked(obj.locked)
                a_lock.triggered.connect(
                    lambda c, oid=obj_id: self._controller.update_properties(
                        oid, {"locked": c}))

            a_vis = menu.addAction("👁  Visible")
            a_vis.setCheckable(True)
            if obj:
                a_vis.setChecked(obj.visible)
                a_vis.triggered.connect(
                    lambda c, oid=obj_id: self._controller.update_properties(
                        oid, {"visible": c}))

            menu.addSeparator()
            menu.addAction("⬆  Bring Forward",
                           lambda: self._controller.bring_forward(
                               self._store.selection.active_id))
            menu.addAction("⬇  Send Backward",
                           lambda: self._controller.send_backward(
                               self._store.selection.active_id))
            menu.addSeparator()

            if sel_count >= 2:
                align_menu = menu.addMenu("⚖  Align")
                for mode, label_a in [
                    ("left",     "Align Left"),
                    ("right",    "Align Right"),
                    ("top",      "Align Top"),
                    ("bottom",   "Align Bottom"),
                    ("center_h", "Center Horizontal"),
                    ("center_v", "Center Vertical"),
                ]:
                    align_menu.addAction(
                        label_a,
                        lambda _, m=mode: self._controller.align_objects(m))

        else:
            # Click on empty area
            self._controller.clear_selection()
            menu.addAction("▭  Add Rect",
                           lambda: self._controller.add_rect(
                               int(pos_scene.x()), int(pos_scene.y())))
            menu.addAction("◯  Add Ellipse",
                           lambda: self._controller.add_ellipse(
                               int(pos_scene.x()), int(pos_scene.y())))
            menu.addAction("T  Add Text",
                           lambda: self._controller.add_text(
                               int(pos_scene.x()), int(pos_scene.y())))
            menu.addAction("🖼  Add Image",
                           lambda: self._controller.add_image_from_dialog())

        if not menu.isEmpty():
            menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        pos_scene = self.mapToScene(event.pos())
        for item in self._scene.items(pos_scene):
            if item is self._overlay:
                continue
            obj_id = self._registry.get_id(item)
            if obj_id:
                canvas = self._store.active_canvas
                obj    = canvas.objects.get(obj_id) if canvas else None
                if obj and obj.type == ObjectType.TEXT:
                    from ui.dialogs.text_dialog import TextEditDialog
                    dlg = TextEditDialog(obj, self)
                    if dlg.exec():
                        self._controller.update_properties(
                            obj_id, {"payload_text": dlg.get_text()})
                break
        event.accept()

    # -----------------------------------------------------------------------
    # Wheel — зум к курсору, без Ctrl тоже работает
    # -----------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent):
        # Если Alt зажат — не зумим (это pan режим через mouseMoveEvent)
        if event.modifiers() & Qt.AltModifier:
            event.ignore()
            return

        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return

        # Зум к позиции курсора
        factor = self.ZOOM_STEP if delta > 0 else 1.0 / self.ZOOM_STEP
        self._zoom_at(factor, event.position().toPoint())
        event.accept()

    # -----------------------------------------------------------------------
    # Resize — центрируем если канвас умещается
    # -----------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_if_small()

    # -----------------------------------------------------------------------
    # Key events
    # -----------------------------------------------------------------------

    def keyPressEvent(self, event):
        step   = 10 if event.modifiers() & Qt.ShiftModifier else 1
        canvas = self._store.active_canvas
        ids    = list(self._store.selection.selected_ids)

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

        elif (event.key() == Qt.Key_0 and
              event.modifiers() & Qt.ControlModifier):
            self._fit_canvas()

        # Zoom hotkeys
        elif (event.key() in (Qt.Key_Equal, Qt.Key_Plus) and
              event.modifiers() & Qt.ControlModifier):
            vp_center = QPoint(self.viewport().width() // 2,
                               self.viewport().height() // 2)
            self._zoom_at(self.ZOOM_STEP, vp_center)

        elif (event.key() == Qt.Key_Minus and
              event.modifiers() & Qt.ControlModifier):
            vp_center = QPoint(self.viewport().width() // 2,
                               self.viewport().height() // 2)
            self._zoom_at(1.0 / self.ZOOM_STEP, vp_center)

        else:
            super().keyPressEvent(event)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def fit_view(self):
        self._fit_canvas()

    def zoom_in(self):
        center = QPoint(self.viewport().width() // 2,
                        self.viewport().height() // 2)
        self._zoom_at(self.ZOOM_STEP ** 2, center)

    def zoom_out(self):
        center = QPoint(self.viewport().width() // 2,
                        self.viewport().height() // 2)
        self._zoom_at(1.0 / (self.ZOOM_STEP ** 2), center)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_top_level(canvas, selected_ids: set) -> list[str]:
    result = []
    for oid in selected_ids:
        obj = canvas.objects.get(oid)
        if not obj:
            continue
        ancestor   = obj.parent_id
        dominated  = False
        while ancestor:
            if ancestor in selected_ids:
                dominated = True
                break
            anc      = canvas.objects.get(ancestor)
            ancestor = anc.parent_id if anc else None
        if not dominated:
            result.append(oid)
    return result
