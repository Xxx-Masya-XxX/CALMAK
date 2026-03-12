"""Утилита рендеринга обводки.

Используется только shape_item и image_item.
text_item рисует outline букв самостоятельно через QPainterPath.
"""

from PySide6.QtGui import QPen, QColor, QPainter, QPainterPath, QPolygonF
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.base_object import BaseObject


_QT_STYLES = {
    "solid":    Qt.PenStyle.SolidLine,
    "dash":     Qt.PenStyle.DashLine,
    "dot":      Qt.PenStyle.DotLine,
    "dash_dot": Qt.PenStyle.DashDotLine,
}


def _shape_path(obj: BaseObject, rect: QRectF) -> QPainterPath:
    """Строит QPainterPath по форме объекта."""
    path = QPainterPath()
    if obj.shape_type == "ellipse":
        path.addEllipse(rect)
    elif obj.shape_type == "triangle":
        path.addPolygon(QPolygonF([
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.right(), rect.bottom()),
            QPointF(rect.left(), rect.bottom()),
        ]))
    else:
        path.addRect(rect)
    return path


def _stroke_rect(obj: BaseObject) -> QRectF:
    """QRectF с учётом stroke_position (inside / outside / center)."""
    half = obj.stroke_width / 2
    w, h = obj.width, obj.height

    pos = getattr(obj, 'stroke_position', 'center')
    if pos == "inside":
        return QRectF(half, half, w - obj.stroke_width, h - obj.stroke_width)
    if pos == "outside":
        return QRectF(-half, -half, w + obj.stroke_width, h + obj.stroke_width)
    return QRectF(0, 0, w, h)  # center


def draw_stroke(painter: QPainter, obj: BaseObject, clip_path: QPainterPath | None = None):
    """Рисует обводку объекта если включена.

    Args:
        painter:   активный QPainter
        obj:       модель объекта
        clip_path: если передан — используется для clip (для ellipse/triangle)
    """
    if not obj.stroke_enabled:
        return

    painter.save()

    pen = QPen(QColor(obj.stroke_color), obj.stroke_width)
    pen.setStyle(_QT_STYLES.get(getattr(obj, 'stroke_style', 'solid'), Qt.PenStyle.SolidLine))
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    rect = _stroke_rect(obj)
    path = _shape_path(obj, rect)
    painter.drawPath(path)

    painter.restore()
