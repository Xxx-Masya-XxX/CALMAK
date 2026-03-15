"""Графический элемент для TextObject."""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetricsF
from PySide6.QtCore import Qt, QRectF

from .base_object import BaseGraphicsItem
from ...models.objects.text_object import TextObject


class TextGraphicsItem(BaseGraphicsItem):
    """Рисует TextObject на сцене."""

    def __init__(self, obj: TextObject, parent_item=None):
        super().__init__(obj, parent_item)

    def _paint_content(self, painter: QPainter, rect: QRectF):
        obj: TextObject = self.obj

        # Фон (полупрозрачный, чтобы было видно границы)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)

        # Обводка
        if obj.stroke_enabled:
            pen = QPen(QColor(obj.stroke_color), obj.stroke_width)
            painter.setPen(pen)
            painter.drawRect(rect)

        # Шрифт
        font = QFont(obj.font_family, int(obj.font_size))
        font.setBold(obj.font_bold)
        font.setItalic(obj.font_italic)
        font.setUnderline(obj.font_underline)
        painter.setFont(font)
        painter.setPen(QColor(obj.text_color))

        # Выравнивание по горизонтали
        h_flags = {
            "left":   Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignHCenter,
            "right":  Qt.AlignmentFlag.AlignRight,
        }.get(obj.text_align_h, Qt.AlignmentFlag.AlignLeft)

        # Выравнивание по вертикали
        v_flags = {
            "top":    Qt.AlignmentFlag.AlignTop,
            "middle": Qt.AlignmentFlag.AlignVCenter,
            "bottom": Qt.AlignmentFlag.AlignBottom,
        }.get(obj.text_align_v, Qt.AlignmentFlag.AlignTop)

        flags = h_flags | v_flags
        if obj.word_wrap:
            flags |= Qt.TextFlag.TextWordWrap

        painter.drawText(rect, flags, obj.text)