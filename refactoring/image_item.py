"""Графический элемент для изображения (ImageObject).

Реализует только _paint_content() — вся логика в BaseGraphicsItem.
"""

from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.image_object import ImageObject
from .base_item import BaseGraphicsItem
from .stroke_renderer import draw_stroke


class ImageGraphicsItem(BaseGraphicsItem):
    """Рендерит изображение внутри базового квадрата."""

    def _paint_content(self, painter: QPainter, rect: QRectF):
        clip = QPainterPath()
        clip.addRect(rect)

        if self.obj.image_path:
            img = QImage(self.obj.image_path)
            if not img.isNull():
                painter.save()
                painter.setClipPath(clip)

                scale_mode = getattr(self.obj, 'image_scale_mode', 'stretch')

                if scale_mode == "preserve_aspect":
                    scaled = img.scaled(
                        int(rect.width()), int(rect.height()),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    x_off = (rect.width()  - scaled.width())  / 2
                    y_off = (rect.height() - scaled.height()) / 2
                    painter.drawImage(QPointF(x_off, y_off), scaled)

                elif scale_mode == "crop":
                    scaled = img.scaled(
                        int(rect.width()), int(rect.height()),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    x_off = (rect.width()  - scaled.width())  / 2
                    y_off = (rect.height() - scaled.height()) / 2
                    painter.drawImage(QPointF(x_off, y_off), scaled)

                else:  # stretch
                    painter.drawImage(rect, img)

                painter.restore()
                draw_stroke(painter, self.obj, clip)
                return

        # Заглушка если изображения нет
        painter.setBrush(QBrush(QColor(self.obj.color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)
        draw_stroke(painter, self.obj, clip)
