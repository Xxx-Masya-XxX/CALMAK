from .base_object import BaseGraphicsItem
from ...models import ShapeObject

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject


class ShapeGraphicsItem(BaseGraphicsItem):
    """Графический элемент для отображения ShapeObject на сцене."""

    def __init__(self, shape_object: ShapeObject, parent=None):
        super().__init__(shape_object, parent)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )
        self.setAcceptHoverEvents(True)

    # def boundingRect(self) -> QRectF:
    #     """Возвращает границы фигуры для рендеринга и взаимодействия."""
    #     return QRectF(0, 0, self.obj.width, self.obj.height)

    def _paint_content(self, painter: QPainter, rect: QRectF):
        """Рисует фигуру на сцене."""
        color = QColor(self.obj.color)
        painter.setBrush(QBrush(color))
        pen = QPen(Qt.GlobalColor.black, 1)
        painter.setPen(pen)
        if self.obj.shape_type == 'triangle':
            painter.drawPolygon([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.left(), rect.bottom()),
                QPointF(rect.right(), rect.bottom())
            ])
        elif self.obj.shape_type == 'ellipse':
            painter.drawEllipse(rect)
        else:
            # Если тип фигуры неизвестен, рисуем прямоугольник по умолчанию
            painter.drawRect(rect)