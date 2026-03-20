"""
CanvasExporter — экспортирует CanvasState в растровое изображение.
Независим от UI, работает через QPainter.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (QImage, QPainter, QColor, QBrush, QPen,
                            QFont, QPixmap, QFontMetrics)
from domain.models import (CanvasState, ObjectState, ObjectType,
                            TextPayload, ImagePayload, StyleState)


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
            painter.setBrush(QBrush(QColor("#CCCCCC")))
            painter.setPen(QPen(QColor("#888888"), 2))
            painter.drawRect(rect)
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())

        painter.restore()
