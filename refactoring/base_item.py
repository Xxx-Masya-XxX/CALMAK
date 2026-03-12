"""Базовый графический элемент.

Архитектура:
- BaseGraphicsItem — владеет ВСЕЙ логикой: move, resize, selection, обводка выделения
- Внутри него есть _content_rect (QRectF) — область для рендеринга контента
- Подклассы реализуют только _paint_content(painter, rect) — рисуют себя в этом rect
- Никакой логики перемещения/resize/selection в подклассах нет
"""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject

from ....models.objects.base_object import BaseObject


# Минимальный размер при resize
MIN_SIZE = 10.0
# Зона захвата края для resize (px)
HANDLE_SIZE = 8.0
# Цвет рамки выделения
SELECTION_COLOR = "#2196F3"


class BaseGraphicsItem(QGraphicsItem):
    """Базовый графический элемент.

    Содержит:
    - Логику resize (все 8 ручек)
    - Синхронизацию позиции/размера с моделью
    - Рамку выделения
    - Испускание сигналов через сцену

    Подклассы переопределяют только:
    - _paint_content(painter, rect)  — рисуют контент в переданном rect
    """

    def __init__(self, obj: BaseObject, parent_item=None):
        super().__init__(parent_item)
        self.obj = obj

        # Resize state
        self._resizing = False
        self._resize_edge: str | None = None
        self._resize_start_scene: QPointF = QPointF()
        self._orig_x = obj.x
        self._orig_y = obj.y
        self._orig_w = obj.width
        self._orig_h = obj.height

        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self.setPos(obj.x, obj.y)
        if obj.rotation:
            self.setTransformOriginPoint(obj.width / 2, obj.height / 2)
            self.setRotation(obj.rotation)

    # ------------------------------------------------------------------
    # Геометрия
    # ------------------------------------------------------------------

    def _content_rect(self) -> QRectF:
        """Внутренняя область для рендеринга контента."""
        return QRectF(0, 0, self.obj.width, self.obj.height)

    def boundingRect(self) -> QRectF:
        # Расширяем на HANDLE_SIZE чтобы ручки resize попадали в bounding rect
        m = HANDLE_SIZE
        return QRectF(-m, -m, self.obj.width + m * 2, self.obj.height + m * 2)

    def sync_from_model(self):
        """Синхронизирует визуальное состояние из модели (вызывать после внешних изменений)."""
        self.prepareGeometryChange()
        self.setPos(self.obj.x, self.obj.y)
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        self.setRotation(self.obj.rotation)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not self.obj.locked)
        self.update()

    # ------------------------------------------------------------------
    # Рендеринг
    # ------------------------------------------------------------------

    def paint(self, painter: QPainter, option, widget=None):
        if not self.obj.visible:
            return

        painter.save()
        rect = self._content_rect()

        # Рисуем контент (реализуется в подклассах)
        self._paint_content(painter, rect)

        painter.restore()

        # Рамка выделения — поверх всего, не внутри save/restore контента
        if self.isSelected():
            self._paint_selection(painter, rect)

    def _paint_content(self, painter: QPainter, rect: QRectF):
        """Рисует контент объекта в переданном rect.

        Переопределить в подклассе. Не вызывать super().
        painter уже в save(), не нужно делать save/restore вокруг всего.
        """
        pass

    def _paint_selection(self, painter: QPainter, rect: QRectF):
        """Рисует рамку выделения."""
        painter.save()
        pen = QPen(QColor(SELECTION_COLOR), 1.5, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)  # толщина не масштабируется при зуме
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        # Рисуем точки на углах и серединах сторон
        handle_pen = QPen(QColor(SELECTION_COLOR), 1)
        handle_pen.setCosmetic(True)
        painter.setPen(handle_pen)
        painter.setBrush(QColor("white"))
        hs = 4.0  # половина размера квадратика

        for hx, hy in self._handle_positions(rect):
            painter.drawRect(QRectF(hx - hs, hy - hs, hs * 2, hs * 2))

        painter.restore()

    def _handle_positions(self, rect: QRectF) -> list[tuple[float, float]]:
        """Возвращает позиции 8 ручек resize."""
        l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
        cx, cy = rect.center().x(), rect.center().y()
        return [
            (l, t), (cx, t), (r, t),
            (l, cy),          (r, cy),
            (l, b), (cx, b), (r, b),
        ]

    # ------------------------------------------------------------------
    # Resize — определение зоны
    # ------------------------------------------------------------------

    def _get_resize_edge(self, pos: QPointF) -> str | None:
        rect = self._content_rect()
        m = HANDLE_SIZE

        left   = abs(pos.x() - rect.left())  < m
        right  = abs(pos.x() - rect.right()) < m
        top    = abs(pos.y() - rect.top())   < m
        bottom = abs(pos.y() - rect.bottom()) < m

        if top    and left:  return "top-left"
        if top    and right: return "top-right"
        if bottom and left:  return "bottom-left"
        if bottom and right: return "bottom-right"
        if left:             return "left"
        if right:            return "right"
        if top:              return "top"
        if bottom:           return "bottom"
        return None

    _CURSORS = {
        "top-left":     Qt.CursorShape.SizeFDiagCursor,
        "top-right":    Qt.CursorShape.SizeBDiagCursor,
        "bottom-left":  Qt.CursorShape.SizeBDiagCursor,
        "bottom-right": Qt.CursorShape.SizeFDiagCursor,
        "left":         Qt.CursorShape.SizeHorCursor,
        "right":        Qt.CursorShape.SizeHorCursor,
        "top":          Qt.CursorShape.SizeVerCursor,
        "bottom":       Qt.CursorShape.SizeVerCursor,
    }

    # ------------------------------------------------------------------
    # События мыши
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self.obj.locked:
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_scene = event.scenePos()
                self._orig_x = self.obj.x
                self._orig_y = self.obj.y
                self._orig_w = self.obj.width
                self._orig_h = self.obj.height
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.obj.locked:
            event.ignore()
            return

        if self._resizing and self._resize_edge:
            self._do_resize(event.scenePos())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_resizing = self._resizing

        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = None
            event.accept()

        super().mouseReleaseEvent(event)

        if was_resizing:
            self._emit_resized()

    def hoverMoveEvent(self, event):
        if not self._resizing:
            edge = self._get_resize_edge(event.pos())
            cursor = self._CURSORS.get(edge, Qt.CursorShape.ArrowCursor) if edge else Qt.CursorShape.ArrowCursor
            self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    # ------------------------------------------------------------------
    # Логика resize
    # ------------------------------------------------------------------

    def _do_resize(self, scene_pos: QPointF):
        delta = scene_pos - self._resize_start_scene
        edge = self._resize_edge

        new_x, new_y = self._orig_x, self._orig_y
        new_w, new_h = self._orig_w, self._orig_h

        if "left" in edge:
            new_w = self._orig_w - delta.x()
            if new_w >= MIN_SIZE:
                new_x = self._orig_x + delta.x()
            else:
                new_w = MIN_SIZE
                new_x = self._orig_x + self._orig_w - MIN_SIZE

        elif "right" in edge:
            new_w = max(MIN_SIZE, self._orig_w + delta.x())

        if "top" in edge:
            new_h = self._orig_h - delta.y()
            if new_h >= MIN_SIZE:
                new_y = self._orig_y + delta.y()
            else:
                new_h = MIN_SIZE
                new_y = self._orig_y + self._orig_h - MIN_SIZE

        elif "bottom" in edge:
            new_h = max(MIN_SIZE, self._orig_h + delta.y())

        # Обновляем модель
        self.obj.x = new_x
        self.obj.y = new_y
        self.obj.width = new_w
        self.obj.height = new_h

        # Обновляем визуал
        self.prepareGeometryChange()
        self.setPos(new_x, new_y)
        self.setTransformOriginPoint(new_w / 2, new_h / 2)
        self.update()

        # Сигнал real-time для панели свойств
        self._emit_geometry_changed()

    # ------------------------------------------------------------------
    # itemChange — синхронизация позиции при перетаскивании
    # ------------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if not self._resizing:
                pos = self.pos()
                self.obj.x = pos.x()
                self.obj.y = pos.y()
                self._emit_moved()

        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()

        return super().itemChange(change, value)

    # ------------------------------------------------------------------
    # Испускание сигналов через сцену
    # ------------------------------------------------------------------

    def _emit_moved(self):
        scene = self.scene()
        if scene and hasattr(scene, 'object_moved'):
            scene.object_moved.emit(self.obj)

    def _emit_resized(self):
        scene = self.scene()
        if scene and hasattr(scene, 'object_resized'):
            scene.object_resized.emit(self.obj)

    def _emit_geometry_changed(self):
        """Real-time обновление во время resize (для панели свойств)."""
        scene = self.scene()
        if scene and hasattr(scene, 'object_geometry_changed'):
            scene.object_geometry_changed.emit(self.obj)
