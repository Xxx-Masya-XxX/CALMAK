"""Графический элемент для фигуры (ShapeObject).

Реализует только _paint_content() — вся логика в BaseGraphicsItem.
"""

from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QPainterPath, QImage
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.base_object import BaseObject
from .base_item import BaseGraphicsItem
from .stroke_renderer import draw_stroke


class ShapeGraphicsItem(BaseGraphicsItem):
    """Рендерит фигуру (rect / ellipse / triangle) внутри базового квадрата."""

    def _paint_content(self, painter: QPainter, rect: QRectF):
        shape = self.obj.shape_type

        # --- clip path по форме ---
        clip = QPainterPath()
        if shape == "ellipse":
            clip.addEllipse(rect)
        elif shape == "triangle":
            clip.addPolygon(QPolygonF([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.right(), rect.bottom()),
                QPointF(rect.left(), rect.bottom()),
            ]))
        else:
            clip.addRect(rect)

        # --- изображение ---
        if self.obj.image_fill and self.obj.image_path:
            img = QImage(self.obj.image_path)
            if not img.isNull():
                painter.save()
                painter.setClipPath(clip)
                painter.drawImage(rect, img)
                painter.restore()
                draw_stroke(painter, self.obj, clip)
                return

        # --- цветовая заливка ---
        painter.setBrush(QBrush(QColor(self.obj.color)))
        painter.setPen(Qt.PenStyle.NoPen)

        if shape == "ellipse":
            painter.drawEllipse(rect)
        elif shape == "triangle":
            painter.drawPolygon(QPolygonF([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.right(), rect.bottom()),
                QPointF(rect.left(), rect.bottom()),
            ]))
        else:
            painter.drawRect(rect)

        # --- обводка ---
        draw_stroke(painter, self.obj, clip)
