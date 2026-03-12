"""Графический элемент для фигуры."""

from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QPainterPath, QImage
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.base_object import BaseObject
from .base_item import ResizeMixin


class ShapeGraphicsItem(ResizeMixin, QGraphicsRectItem):
    """Графический элемент для фигуры с поддержкой изменения размера."""

    def __init__(self, obj: BaseObject, parent_item=None):
        QGraphicsRectItem.__init__(self, 0, 0, obj.width, obj.height, parent_item)
        self.obj = obj
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        # Параметры изменения размера
        self._resizing = False
        self._resize_handle_size = 8.0
        self._resize_edge = None
        self._resize_start_pos = QPointF(0, 0)
        self._original_x = 0.0
        self._original_y = 0.0
        self._original_width = 0.0
        self._original_height = 0.0
        self._current_cursor = None

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
        else:
            clip_path.addRect(rect)

        # Рисуем изображение если включено
        if self.obj.image_fill and self.obj.image_path:
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
            from .stroke_renderer import draw_stroke
            draw_stroke(painter, self.obj)
    def mouseReleaseEvent(self, event):
        was_resizing = self._resizing  # запоминаем ДО вызова resize_mouse_release
        self.resize_mouse_release(event)
        super().mouseReleaseEvent(event)

        if was_resizing:
            scene = self.scene()
            if scene and hasattr(scene, 'object_resized'):
                scene.object_resized.emit(self.obj)
    def hoverMoveEvent(self, event):
        """Обработка наведения мыши."""
        if self.resize_hover_move(event):
            return
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Обработка нажатия мыши."""
        if self.resize_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши."""
        if self.resize_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши."""
        self.resize_mouse_release(event)
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
                # Обновляем позиции дочерних элементов
                if hasattr(scene, '_update_children_positions'):
                    scene._update_children_positions(self.obj)
                if hasattr(scene, 'object_moved'):
                    scene.object_moved.emit(self.obj)

            return new_pos
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_appearance()

        return super().itemChange(change, value)
