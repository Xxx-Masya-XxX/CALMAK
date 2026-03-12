"""Графический элемент для текстового объекта."""

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PySide6.QtGui import (
    QPainter, QFont, QColor, QPen, QBrush, QTextOption,
    QFontMetricsF, QTextDocument
)
from PySide6.QtCore import Qt, QRectF, QPointF

from .base_item import ResizeMixin
from ....models.objects.text_object import TextObject


# Маппинг выравнивания
_HALIGN = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
}

_VALIGN = {
    "top": Qt.AlignmentFlag.AlignTop,
    "middle": Qt.AlignmentFlag.AlignVCenter,
    "bottom": Qt.AlignmentFlag.AlignBottom,
}


class TextGraphicsItem(ResizeMixin, QGraphicsItem):
    """Графический элемент для отображения и редактирования TextObject.

    Поддерживает:
    - Многострочный текст с переносом слов
    - Форматирование: bold, italic, underline
    - Горизонтальное и вертикальное выравнивание
    - Изменение размера через ResizeMixin
    - auto_height: подстройка высоты под содержимое
    """

    def __init__(self, obj: TextObject, parent=None):
        QGraphicsItem.__init__(self, parent)
        self.obj = obj

        # Состояние ResizeMixin
        self._resizing = False
        self._resize_handle_size = 8.0
        self._resize_edge: str | None = None
        self._resize_start_pos = QPointF()
        self._original_x = obj.x
        self._original_y = obj.y
        self._original_width = obj.width
        self._original_height = obj.height
        self._current_cursor: str | None = None

        self.setPos(obj.x, obj.y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        if obj.rotation != 0.0:
            self.setRotation(obj.rotation)

    # ------------------------------------------------------------------
    # Геометрия
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        margin = self._resize_handle_size
        return QRectF(
            -margin, -margin,
            self.obj.width + margin * 2,
            self.obj.height + margin * 2,
        )

    def rect(self) -> QRectF:
        return QRectF(0, 0, self.obj.width, self.obj.height)

    def update_geometry(self):
        """Обновляет геометрию после изменения размера."""
        self.prepareGeometryChange()
        self.setPos(self.obj.x, self.obj.y)
        if self.obj.auto_height:
            self._adjust_height()
        self.update()

    def _adjust_height(self):
        """Подстраивает высоту блока под содержимое текста."""
        doc = self._make_document()
        doc.setTextWidth(self.obj.width - self.obj.padding_left - self.obj.padding_right)
        content_height = doc.size().height()
        new_height = content_height + self.obj.padding_top + self.obj.padding_bottom
        if abs(new_height - self.obj.height) > 0.5:  # избегаем лишних обновлений
            self.prepareGeometryChange()
            self.obj.height = new_height

    # ------------------------------------------------------------------
    # Построение QTextDocument (шрифт, выравнивание, перенос)
    # ------------------------------------------------------------------

    def _make_font(self) -> QFont:
        font = QFont(self.obj.font_family, int(self.obj.font_size))
        font.setBold(self.obj.font_bold)
        font.setItalic(self.obj.font_italic)
        font.setUnderline(self.obj.font_underline)
        return font
    def update_font(self):
        """Обновляет отображение после изменения шрифта или текста."""
        self.prepareGeometryChange()
        if self.obj.auto_height:
            self._adjust_height()
        self.update()
    def _make_document(self) -> 'QTextDocument':
        """Создаёт QTextDocument с текстом и форматированием объекта."""
        from PySide6.QtGui import QTextDocument, QTextCursor, QTextCharFormat, QTextBlockFormat

        doc = QTextDocument()
        doc.setDefaultFont(self._make_font())

        # Настройка блочного формата (выравнивание, межстрочный интервал)
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(_HALIGN.get(self.obj.text_align_h, Qt.AlignmentFlag.AlignLeft))
        block_fmt.setLineHeight(
            self.obj.line_height * 100,
            1,  # ProportionalHeight
        )

        # Символьный формат (цвет)
        char_fmt = QTextCharFormat()
        char_fmt.setForeground(QColor(self.obj.text_color))
        char_fmt.setFont(self._make_font())

        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(block_fmt)
        cursor.setCharFormat(char_fmt)
        cursor.insertText(self.obj.text)

        if not self.obj.word_wrap:
            doc.setTextWidth(-1)

        return doc

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def update_colors(self):
        """Обновляет цвета после изменения в модели."""
        self.update()
    def paint(self, painter: QPainter, option, widget=None):
        if not self.obj.visible:
            return

        # auto_height пересчитываем перед отрисовкой
        if self.obj.auto_height:
            self._adjust_height()

        painter.save()  # ← было пропущено

        content_rect = QRectF(0, 0, self.obj.width, self.obj.height)  # ← не было определено

        # Фон
        if self.obj.color and self.obj.color != "transparent":
            painter.fillRect(content_rect, QColor(self.obj.color))

        # Область текста с учётом padding
        text_rect = QRectF(
            self.obj.padding_left,
            self.obj.padding_top,
            self.obj.width - self.obj.padding_left - self.obj.padding_right,
            self.obj.height - self.obj.padding_top - self.obj.padding_bottom,
        )

        # Текст с outline букв (если stroke_enabled) или обычный
        self._draw_text_with_stroke(painter, text_rect)

        painter.restore()

        # Рамка выделения
        if self.isSelected():
            pen = QPen(QColor("#2196F3"), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(content_rect)

    def _draw_text_with_stroke(self, painter: QPainter, text_rect: QRectF):
        """Рисует текст — с outline букв если stroke_enabled, иначе обычно."""
        from PySide6.QtGui import QPainterPath, QTextLayout, QTextOption

        doc = self._make_document()
        doc.setTextWidth(text_rect.width())
        doc_height = doc.size().height()

        # Вертикальное выравнивание
        v_offset = 0.0
        if self.obj.text_align_v == "middle":
            v_offset = max(0.0, (text_rect.height() - doc_height) / 2)
        elif self.obj.text_align_v == "bottom":
            v_offset = max(0.0, text_rect.height() - doc_height)

        painter.save()
        painter.translate(text_rect.x(), text_rect.y() + v_offset)
        painter.setClipRect(QRectF(0, 0, text_rect.width(), text_rect.height()))

        if self.obj.stroke_enabled:
            font = self._make_font()
            metrics = QFontMetricsF(font)
            halign = _HALIGN.get(self.obj.text_align_h, Qt.AlignmentFlag.AlignLeft)

            y = 0.0
            # Итерируемся по параграфам (разбитым по \n)
            for paragraph in self.obj.text.split("\n"):
                if not paragraph:
                    # Пустая строка — просто смещаемся вниз
                    y += metrics.height() * self.obj.line_height
                    continue

                # QTextLayout для корректного word_wrap внутри параграфа
                layout = QTextLayout(paragraph, font)
                opt = QTextOption()
                opt.setWrapMode(
                    QTextOption.WrapMode.WordWrap if self.obj.word_wrap
                    else QTextOption.WrapMode.NoWrap
                )
                opt.setAlignment(halign)
                layout.setTextOption(opt)
                layout.beginLayout()

                while True:
                    line = layout.createLine()
                    if not line.isValid():
                        break
                    line.setLineWidth(text_rect.width())
                    line.setPosition(QPointF(0, y))
                    y += line.height() * self.obj.line_height

                layout.endLayout()

                # Рисуем каждую линию через QPainterPath (для outline)
                for i in range(layout.lineCount()):
                    line = layout.lineAt(i)
                    line_text = paragraph[line.textStart(): line.textStart() + line.textLength()]

                    # Позиция X по выравниванию
                    line_w = metrics.horizontalAdvance(line_text)
                    if halign == Qt.AlignmentFlag.AlignHCenter:
                        x_off = (text_rect.width() - line_w) / 2
                    elif halign == Qt.AlignmentFlag.AlignRight:
                        x_off = text_rect.width() - line_w
                    else:
                        x_off = 0.0

                    path = QPainterPath()
                    path.addText(
                        x_off,
                        line.position().y() + metrics.ascent(),
                        font,
                        line_text,
                    )

                    # Обводка поверх заливки — сначала stroke, потом fill
                    pen = QPen(QColor(self.obj.stroke_color), self.obj.stroke_width)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.strokePath(path, pen)
                    painter.fillPath(path, QColor(self.obj.text_color))
        else:
            doc.drawContents(painter)

        painter.restore()
    # ------------------------------------------------------------------
    # События мыши — делегируем в ResizeMixin
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self.obj.locked:
            event.ignore()
            return
        if not self.resize_mouse_press(event):
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.obj.locked:
            event.ignore()
            return
        if not self.resize_mouse_move(event):
            super().mouseMoveEvent(event)
            # Синхронизируем позицию в модель при перемещении
            pos = self.pos()
            self.obj.x = pos.x()
            self.obj.y = pos.y()

    def mouseReleaseEvent(self, event):
        self.resize_mouse_release(event)
        super().mouseReleaseEvent(event)

    def hoverMoveEvent(self, event):
        self.resize_hover_move(event)
        super().hoverMoveEvent(event)

    # ------------------------------------------------------------------
    # ResizeMixin callback
    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        was_resizing = self._resizing  # запоминаем ДО вызова resize_mouse_release
        self.resize_mouse_release(event)
        super().mouseReleaseEvent(event)

        if was_resizing:
            scene = self.scene()
            if scene and hasattr(scene, 'object_resized'):
                scene.object_resized.emit(self.obj)
    def on_resize(self):
        """После resize обновляем auto_height если включён."""
        if self.obj.auto_height:
            self._adjust_height()