"""Графический элемент для фигуры."""

from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.base_object import BaseObject


class ShapeGraphicsItem(QGraphicsRectItem):
    """Графический элемент для фигуры с поддержкой изменения размера."""

    def __init__(self, obj: BaseObject, parent_item=None):
        super().__init__(0, 0, obj.width, obj.height, parent_item)
        self.obj = obj
        # Устанавливаем флаги в зависимости от блокировки
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._resizing = False
        self._resize_handle_size = 8.0
        self._resize_edge = None

        self.update_geometry()
        self.update_appearance()

    def update_geometry(self):
        """Обновляет геометрию из модели."""
        self.setRect(QRectF(0, 0, self.obj.width, self.obj.height))
        self.setPos(self.obj.x, self.obj.y)
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        self.setRotation(self.obj.rotation)

    def update_appearance(self):
        """Обновляет внешний вид."""
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, not self.obj.locked)
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        self.setRotation(self.obj.rotation)
        self.update()

    def paint(self, painter: QPainter, option, widget):
        """Рисует фигуру с обводкой и изображением."""
        painter.save()

        rect = self.rect()
        shape_type = self.obj.shape_type

        # Создаём путь для обрезки изображения по форме фигуры
        clip_path = QPainterPath()
        if shape_type == "ellipse":
            clip_path.addEllipse(rect)
        elif shape_type == "triangle":
            polygon = QPolygonF([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.bottomRight()),
                QPointF(rect.bottomLeft())
            ])
            clip_path.addPolygon(polygon)
        else:  # rect
            clip_path.addRect(rect)

        # Добавляем обрезку по границам родительского элемента (канваса)
        parent_clip_path = QPainterPath()
        if self.parentItem():
            parent_rect = self.parentItem().boundingRect()
            parent_clip_path.addRect(parent_rect)
            clip_path = clip_path.intersected(parent_clip_path)

        # Рисуем изображение если включено
        if self.obj.image_fill and self.obj.image_path:
            from PySide6.QtGui import QImage
            image = QImage(self.obj.image_path)
            if not image.isNull():
                painter.save()
                painter.setClipPath(clip_path)
                painter.drawImage(rect, image)
                painter.restore()

                if self.obj.stroke_enabled:
                    pen = QPen(QColor(self.obj.stroke_color), self.obj.stroke_width)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(clip_path)

                if self.isSelected():
                    painter.save()
                    pen = QPen(QColor(Qt.GlobalColor.blue), 2)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(clip_path)
                    painter.restore()
                painter.restore()
                return

        # Рисуем заливку цветом
        color = QColor(self.obj.color)
        painter.setBrush(QBrush(color))

        if self.obj.stroke_enabled:
            pen = QPen(QColor(self.obj.stroke_color), self.obj.stroke_width)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        if shape_type == "ellipse":
            painter.drawEllipse(rect)
        elif shape_type == "triangle":
            polygon = QPolygonF([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.bottomRight()),
                QPointF(rect.bottomLeft())
            ])
            painter.drawPolygon(polygon)
        else:
            painter.drawRect(rect)

        painter.restore()

        if self.isSelected():
            painter.save()
            pen = QPen(QColor(Qt.GlobalColor.blue), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            painter.restore()

    def _get_resize_edge(self, pos: QPointF) -> str | None:
        """Определяет край для изменения размера."""
        rect = self.rect()
        margin = self._resize_handle_size

        left = abs(pos.x() - rect.left()) < margin
        right = abs(pos.x() - rect.right()) < margin
        top = abs(pos.y() - rect.top()) < margin
        bottom = abs(pos.y() - rect.bottom()) < margin

        if top and left:
            return "top-left"
        elif top and right:
            return "top-right"
        elif bottom and left:
            return "bottom-left"
        elif bottom and right:
            return "bottom-right"
        elif left:
            return "left"
        elif right:
            return "right"
        elif top:
            return "top"
        elif bottom:
            return "bottom"
        return None

    def _get_cursor_for_edge(self, edge: str) -> Qt.CursorShape:
        """Возвращает курсор для края."""
        cursors = {
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
        }
        return cursors.get(edge, Qt.CursorShape.ArrowCursor)

    def hoverMoveEvent(self, event):
        """Обработка наведения мыши."""
        if self._resizing:
            event.ignore()
            return

        local_pos = event.pos()
        edge = self._get_resize_edge(local_pos)

        if edge:
            self.setCursor(self._get_cursor_for_edge(edge))
            self._current_cursor = edge
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._current_cursor = None

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Обработка нажатия мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            local_pos = event.pos()
            edge = self._get_resize_edge(local_pos)

            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_pos = event.scenePos()
                self._original_x = self.obj.x
                self._original_y = self.obj.y
                self._original_width = self.obj.width
                self._original_height = self.obj.height
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши."""
        if self._resizing and self._resize_edge:
            delta = event.scenePos() - self._resize_start_pos
            edge = self._resize_edge

            if "left" in edge:
                new_x = self._original_x + delta.x()
                new_width = self._original_width - delta.x()
                if new_width >= 10:
                    self.obj.x = new_x
                    self.obj.width = new_width
            elif "right" in edge:
                new_width = self._original_width + delta.x()
                if new_width >= 10:
                    self.obj.width = new_width

            if "top" in edge:
                new_y = self._original_y + delta.y()
                new_height = self._original_height - delta.y()
                if new_height >= 10:
                    self.obj.y = new_y
                    self.obj.height = new_height
            elif "bottom" in edge:
                new_height = self._original_height + delta.y()
                if new_height >= 10:
                    self.obj.height = new_height

            self.update_geometry()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = None
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        """Обработка изменений элемента."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._resizing:
                return QPointF(0, 0)

            new_pos = value.toPoint()
            self.obj.x = new_pos.x()
            self.obj.y = new_pos.y()

            if hasattr(self, 'scene') and self.scene():
                scene = self.scene()
                if hasattr(scene, 'object_moved'):
                    scene.object_moved.emit(self.obj)

            return new_pos
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_appearance()

        return super().itemChange(change, value)
