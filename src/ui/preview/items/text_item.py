"""Графический элемент для текста."""

from PySide6.QtWidgets import QGraphicsTextItem
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.text_object import TextObject
from .base_item import ResizeMixin


class TextGraphicsItem(ResizeMixin, QGraphicsTextItem):
    """Текстовый элемент с поддержкой изменения размера."""

    def __init__(self, obj: TextObject, parent_item=None):
        QGraphicsTextItem.__init__(self, obj.text, parent_item)
        self.obj = obj
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self._resizing = False
        self._resize_handle_size = 8.0
        self._resize_edge = None
        self._resize_start_pos = QPointF(0, 0)
        self._original_x = 0.0
        self._original_y = 0.0
        self._original_width = 0.0
        self._original_height = 0.0
        self._current_cursor = None

        self.setPos(obj.x, obj.y)
        self.update_font()
        self.update_colors()

    def bounding_rect_for_resize(self) -> QRectF:
        """Возвращает границы для изменения размера."""
        doc_height = self.document().size().height()
        return QRectF(0, 0, self.obj.width, max(self.obj.height, doc_height))

    def update_font(self):
        """Обновляет шрифт."""
        font = QFont(self.obj.font_family, self.obj.font_size)
        font.setBold(self.obj.font_bold)
        font.setItalic(self.obj.font_italic)
        font.setUnderline(self.obj.font_underline)
        self.setFont(font)
        self.setPlainText(self.obj.text)
        self.setTextWidth(self.obj.width)

        doc = self.document()
        block = doc.firstBlock()
        block_format = block.blockFormat()

        if self.obj.text_align_h == "center":
            block_format.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        elif self.obj.text_align_h == "right":
            block_format.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)

        cursor = self.textCursor()
        cursor.setBlockFormat(block_format)

        doc_height = self.document().size().height()
        self.obj.height = max(self.obj.height, doc_height)

        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        self.setRotation(self.obj.rotation)

    def update_colors(self):
        """Обновляет цвета текста и обводки."""
        self.setDefaultTextColor(QColor(self.obj.text_color))
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, not self.obj.locked)
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        self.setRotation(self.obj.rotation)
        self.update()

    def boundingRect(self) -> QRectF:
        """Переопределённая граница для обработки изменения размера."""
        doc_height = self.document().size().height()
        base_rect = QRectF(0, 0, self.obj.width, max(self.obj.height, doc_height))
        return base_rect.adjusted(
            -self._resize_handle_size,
            -self._resize_handle_size,
            self._resize_handle_size,
            self._resize_handle_size
        )

    def paint(self, painter: QPainter, option, widget):
        """Рисует текст с обводкой и выравниванием."""
        doc_height = self.document().size().height()
        y_offset = 0

        if self.obj.text_align_v == "center":
            y_offset = (self.obj.height - doc_height) / 2
        elif self.obj.text_align_v == "bottom":
            y_offset = self.obj.height - doc_height

        if y_offset != 0:
            painter.save()
            painter.translate(0, y_offset)

        if self.obj.stroke_enabled:
            painter.save()
            pen = QPen(QColor(self.obj.stroke_color), self.obj.stroke_width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            font = self.font()
            painter.setFont(font)

            doc = self.document()
            block = doc.firstBlock()

            while block.isValid():
                layout = block.layout()
                if layout:
                    block_text = block.text()
                    for line_idx in range(layout.lineCount()):
                        line = layout.lineAt(line_idx)
                        start = line.textStart()
                        length = line.textLength()
                        if length > 0:
                            line_text = block_text[start:start + length]
                            if line_text.endswith('\n'):
                                line_text = line_text[:-1]
                            if line_text:
                                path = QPainterPath()
                                path.addText(line.x(), line.y() + font.pointSize(), font, line_text)
                                painter.drawPath(path)
                block = block.next()

            painter.restore()

        super().paint(painter, option, widget)

        if self.isSelected():
            painter.save()
            pen = QPen(QColor(Qt.GlobalColor.blue), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(0, 0, self.obj.width, self.obj.height)
            painter.drawRect(rect)
            painter.restore()

        if y_offset != 0:
            painter.restore()

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

    def on_resize(self):
        """Вызывается после изменения размера для обновления текста."""
        self.update_font()
        self.setPos(self.obj.x, self.obj.y)
        self.update()

    def itemChange(self, change, value):
        """Обработка изменений элемента."""
        if change == QGraphicsTextItem.GraphicsItemChange.ItemPositionHasChanged:
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
        elif change == QGraphicsTextItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()

        return super().itemChange(change, value)
