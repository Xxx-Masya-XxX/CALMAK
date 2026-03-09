"""Графический элемент для текста."""

from PySide6.QtWidgets import QGraphicsTextItem
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.text_object import TextObject


class TextGraphicsItem(QGraphicsTextItem):
    """Текстовый элемент с поддержкой изменения размера."""

    def __init__(self, obj: TextObject, parent_item=None):
        super().__init__(obj.text, parent_item)
        self.obj = obj
        # Устанавливаем флаги в зависимости от блокировки
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self._resizing = False
        self._resize_handle_size = 8.0
        self._resize_edge = None

        self.setPos(obj.x, obj.y)
        self.update_font()
        self.update_colors()

    def update_font(self):
        """Обновляет шрифт."""
        font = QFont(self.obj.font_family, self.obj.font_size)
        font.setBold(self.obj.font_bold)
        font.setItalic(self.obj.font_italic)
        font.setUnderline(self.obj.font_underline)
        self.setFont(font)
        self.setPlainText(self.obj.text)
        self.setTextWidth(self.obj.width)

        # Выравнивание текста по горизонтали
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

        # Обновляем высоту объекта
        doc_height = self.document().size().height()
        self.obj.height = max(self.obj.height, doc_height)

        # Смещаем центр вращения в центр объекта
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
        doc_rect = (self.document().idealWidth(), self.document().size().height())
        base_rect = QRectF(0, 0, self.obj.width, max(self.obj.height, doc_rect[1]))
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

        # Рисуем обводку текста если включена
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

        # Рисуем рамку выделения
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

    def _get_resize_edge(self, pos: QPointF) -> str | None:
        """Определяет край для изменения размера."""
        rect = QRectF(0, 0, self.obj.width, self.obj.height)
        margin = self._resize_handle_size

        left = abs(pos.x() - rect.left()) < margin
        right = abs(pos.x() - rect.right()) < margin
        top = abs(pos.y() - rect.top()) < margin
        bottom = abs(pos.y() - rect.bottom()) < margin

        if top and left:
            return "top-left"
        elif top and right:
            return "top-right"
        elif bottom and left:
            return "bottom-left"
        elif bottom and right:
            return "bottom-right"
        elif left:
            return "left"
        elif right:
            return "right"
        elif top:
            return "top"
        elif bottom:
            return "bottom"
        return None

    def _get_cursor_for_edge(self, edge: str) -> Qt.CursorShape:
        """Возвращает курсор для края."""
        cursors = {
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
        }
        return cursors.get(edge, Qt.CursorShape.ArrowCursor)

    def hoverMoveEvent(self, event):
        """Обработка наведения мыши."""
        if self._resizing:
            event.ignore()
            return

        local_pos = event.pos()
        edge = self._get_resize_edge(local_pos)

        if edge:
            self.setCursor(self._get_cursor_for_edge(edge))
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Обработка нажатия мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            local_pos = event.pos()
            edge = self._get_resize_edge(local_pos)

            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_pos = event.scenePos()
                self._original_width = self.obj.width
                self._original_height = self.obj.height
                self._original_x = self.obj.x
                self._original_y = self.obj.y
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши."""
        if self._resizing and self._resize_edge:
            delta = event.scenePos() - self._resize_start_pos
            edge = self._resize_edge

            if "left" in edge:
                new_x = self._original_x + delta.x()
                new_width = self._original_width - delta.x()
                if new_width >= 10:
                    self.obj.x = new_x
                    self.obj.width = new_width
            elif "right" in edge:
                new_width = self._original_width + delta.x()
                if new_width >= 10:
                    self.obj.width = new_width

            if "top" in edge:
                new_y = self._original_y + delta.y()
                new_height = self._original_height - delta.y()
                if new_height >= 10:
                    self.obj.y = new_y
                    self.obj.height = new_height
            elif "bottom" in edge:
                new_height = self._original_height + delta.y()
                if new_height >= 10:
                    self.obj.height = new_height

            self.update_font()
            self.setPos(self.obj.x, self.obj.y)
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = None
        super().mouseReleaseEvent(event)

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
                if hasattr(scene, 'object_moved'):
                    scene.object_moved.emit(self.obj)

            return new_pos
        elif change == QGraphicsTextItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()

        return super().itemChange(change, value)
