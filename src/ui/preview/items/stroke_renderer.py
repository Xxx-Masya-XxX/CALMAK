"""Утилита рендеринга обводки для QGraphicsItem.

Использование в paint() любого графического элемента:

    from src.ui.preview.items.stroke_renderer import draw_stroke
    draw_stroke(painter, self.obj)

Учитывает stroke_style, stroke_position, stroke_color, stroke_width.
"""

from PySide6.QtGui import QPen, QColor, QPainter
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.base_object import BaseObject


_QT_PEN_STYLES = {
    "solid":    Qt.PenStyle.SolidLine,
    "dash":     Qt.PenStyle.DashLine,
    "dot":      Qt.PenStyle.DotLine,
    "dash_dot": Qt.PenStyle.DashDotLine,
}


def make_stroke_pen(obj: BaseObject) -> QPen:
    """Создаёт QPen с учётом stroke_style и stroke_color/width."""
    pen = QPen(QColor(obj.stroke_color), obj.stroke_width)
    pen.setStyle(_QT_PEN_STYLES.get(obj.stroke_style, Qt.PenStyle.SolidLine))
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    return pen


def stroke_rect(obj: BaseObject) -> QRectF:
    """Возвращает QRectF для рисования с учётом stroke_position.

    Qt рисует линию по центру — смещаем rect на half_width
    чтобы получить inside/outside.
    """
    half = obj.stroke_width / 2
    w, h = obj.width, obj.height

    if obj.stroke_position == "inside":
        return QRectF(half, half, w - obj.stroke_width, h - obj.stroke_width)
    elif obj.stroke_position == "outside":
        return QRectF(-half, -half, w + obj.stroke_width, h + obj.stroke_width)
    else:  # center
        return QRectF(0, 0, w, h)


def draw_stroke(painter: QPainter, obj: BaseObject):
    """Рисует обводку объекта если включена.

    Поддерживает shape_type: rect, ellipse, triangle.
    Вызывать внутри paint() после отрисовки фона.
    """
    if not obj.stroke_enabled:
        return

    painter.save()
    pen = make_stroke_pen(obj)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    rect = stroke_rect(obj)

    if obj.shape_type == "ellipse":
        painter.drawEllipse(rect)
    elif obj.shape_type == "triangle":
        from PySide6.QtGui import QPolygonF
        poly = QPolygonF([
            QPointF(rect.left() + rect.width() / 2, rect.top()),
            QPointF(rect.right(), rect.bottom()),
            QPointF(rect.left(), rect.bottom()),
        ])
        painter.drawPolygon(poly)
    else:
        painter.drawRect(rect)

    painter.restore()
