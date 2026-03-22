"""
CanvasExporter — экспортирует CanvasState в растровое изображение.
Независим от UI, работает через QPainter.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (QImage, QPainter, QColor, QBrush, QPen,
                            QFont, QPixmap, QFontMetrics)
from domain.models import (CanvasState, ObjectState, ObjectType,
                            TextPayload, ImagePayload, StyleState,
                            BezierPayload)
from PySide6.QtCore import Qt
from ui.constants import C


class CanvasExporter:

    @staticmethod
    def export(canvas: CanvasState, path: str, fmt: str = "PNG"):
        img = QImage(canvas.width, canvas.height, QImage.Format_ARGB32)
        img.fill(QColor(canvas.background))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Draw objects in z-order
        for obj_id in canvas.all_ids_ordered():
            obj = canvas.objects.get(obj_id)
            if obj and obj.visible:
                CanvasExporter._draw_object(painter, obj)

        painter.end()

        quality = 95 if fmt == "JPEG" else -1
        img.save(path, fmt, quality)

    @staticmethod
    def _draw_object(painter: QPainter, obj: ObjectState):
        t = obj.transform
        s = obj.style

        painter.save()
        painter.setOpacity(t.opacity)
        painter.translate(t.x, t.y)
        if t.rotation:
            painter.translate(t.width / 2, t.height / 2)
            painter.rotate(t.rotation)
            painter.translate(-t.width / 2, -t.height / 2)

        rect = QRectF(0, 0, t.width, t.height)

        def _color(hex_str):
            if hex_str == "transparent":
                return QColor(0, 0, 0, 0)
            return QColor(hex_str)

        if obj.type == ObjectType.RECT:
            painter.setBrush(QBrush(_color(s.fill_color)))
            pen = QPen(_color(s.stroke_color), s.stroke_width)
            painter.setPen(pen if s.stroke_width > 0 else Qt.NoPen)
            if s.corner_radius > 0:
                painter.drawRoundedRect(rect, s.corner_radius, s.corner_radius)
            else:
                painter.drawRect(rect)

        elif obj.type == ObjectType.ELLIPSE:
            painter.setBrush(QBrush(_color(s.fill_color)))
            pen = QPen(_color(s.stroke_color), s.stroke_width)
            painter.setPen(pen if s.stroke_width > 0 else Qt.NoPen)
            painter.drawEllipse(rect)

        elif obj.type == ObjectType.TEXT:
            payload = obj.payload
            if isinstance(payload, TextPayload):
                font = QFont(s.font_family, s.font_size)
                font.setBold(s.bold)
                font.setItalic(s.italic)
                painter.setFont(font)
                painter.setPen(QPen(_color(s.text_color)))
                painter.setBrush(Qt.NoBrush)
                flags = Qt.TextWordWrap
                if s.text_align == "center":
                    flags |= Qt.AlignHCenter
                elif s.text_align == "right":
                    flags |= Qt.AlignRight
                else:
                    flags |= Qt.AlignLeft
                painter.drawText(rect, flags, payload.text)

        elif obj.type == ObjectType.IMAGE:
            payload = obj.payload
            if isinstance(payload, ImagePayload) and payload.source_path:
                pix = QPixmap(payload.source_path)
                if not pix.isNull():
                    scaled = pix.scaled(
                        int(t.width), int(t.height),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    painter.drawPixmap(0, 0, scaled)
                    painter.restore()
                    return
            # Placeholder
            painter.setBrush(QBrush(C.PLACEHOLDER_FILL))
            painter.setPen(QPen(C.PLACEHOLDER_STROKE, 2))
            painter.drawRect(rect)
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())

        elif obj.type == ObjectType.BEZIER:
            from PySide6.QtGui import QPainterPath
            from PySide6.QtCore import QPointF as QF
            payload = obj.payload
            if isinstance(payload, BezierPayload) and payload.points:
                pts  = payload.points
                path = QPainterPath(QF(pts[0].x - t.x, pts[0].y - t.y))
                for i in range(1, len(pts)):
                    prev = pts[i - 1]; cur = pts[i]
                    path.cubicTo(
                        QF(prev.cx2 - t.x, prev.cy2 - t.y),
                        QF(cur.cx1  - t.x, cur.cy1  - t.y),
                        QF(cur.x    - t.x, cur.y    - t.y),
                    )
                if payload.closed and len(pts) > 1:
                    first = pts[0]; last = pts[-1]
                    path.cubicTo(
                        QF(last.cx2  - t.x, last.cy2  - t.y),
                        QF(first.cx1 - t.x, first.cy1 - t.y),
                        QF(first.x   - t.x, first.y   - t.y),
                    )
                    path.closeSubpath()
                painter.setBrush(QBrush(_color(s.fill_color)))
                pen = QPen(_color(s.stroke_color), s.stroke_width)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(path)

        painter.restore()
