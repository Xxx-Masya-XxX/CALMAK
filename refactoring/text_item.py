"""Графический элемент для текста (TextObject).

Реализует только _paint_content() — вся логика в BaseGraphicsItem.
Текст рендерится строго внутри content_rect с учётом padding.
"""

from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetricsF,
    QPainterPath, QPen, QTextOption, QTextDocument,
    QTextCursor, QTextCharFormat, QTextBlockFormat
)
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.text_object import TextObject
from .base_item import BaseGraphicsItem


_H_ALIGN = {
    "left":   Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right":  Qt.AlignmentFlag.AlignRight,
}


class TextGraphicsItem(BaseGraphicsItem):
    """Рендерит текст внутри базового квадрата.

    Текстовая область = content_rect минус padding.
    Если auto_height=True — высота объекта подстраивается под содержимое.
    """

    def __init__(self, obj: TextObject, parent_item=None):
        super().__init__(obj, parent_item)
        self.obj: TextObject = obj

    # ------------------------------------------------------------------
    # Публичные методы обновления (вызываются из scene.update_object)
    # ------------------------------------------------------------------

    def update_font(self):
        self.prepareGeometryChange()
        if self.obj.auto_height:
            self._recalc_height()
        self.update()

    def update_colors(self):
        self.update()

    # ------------------------------------------------------------------
    # Внутренние вычисления
    # ------------------------------------------------------------------

    def _text_rect(self) -> QRectF:
        """Область текста внутри content_rect с учётом padding."""
        o = self.obj
        return QRectF(
            o.padding_left,
            o.padding_top,
            o.width  - o.padding_left - o.padding_right,
            o.height - o.padding_top  - o.padding_bottom,
        )

    def _make_font(self) -> QFont:
        o = self.obj
        font = QFont(o.font_family, int(o.font_size))
        font.setBold(o.font_bold)
        font.setItalic(o.font_italic)
        font.setUnderline(o.font_underline)
        return font

    def _make_document(self) -> QTextDocument:
        o = self.obj
        doc = QTextDocument()
        doc.setDefaultFont(self._make_font())

        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(_H_ALIGN.get(o.text_align_h, Qt.AlignmentFlag.AlignLeft))
        block_fmt.setLineHeight(o.line_height * 100, 1)  # ProportionalHeight

        char_fmt = QTextCharFormat()
        char_fmt.setForeground(QColor(o.text_color))
        char_fmt.setFont(self._make_font())

        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(block_fmt)
        cursor.setCharFormat(char_fmt)
        cursor.insertText(o.text)

        return doc

    def _recalc_height(self):
        """Подстраивает высоту под содержимое текста."""
        o = self.obj
        doc = self._make_document()
        doc.setTextWidth(o.width - o.padding_left - o.padding_right)
        new_h = doc.size().height() + o.padding_top + o.padding_bottom
        if abs(new_h - o.height) > 0.5:
            o.height = new_h

    # ------------------------------------------------------------------
    # Рендеринг контента
    # ------------------------------------------------------------------

    def _paint_content(self, painter: QPainter, rect: QRectF):
        o = self.obj

        # auto_height перед отрисовкой
        if o.auto_height:
            self._recalc_height()

        # Фон блока
        if o.color and o.color != "transparent":
            painter.fillRect(rect, QColor(o.color))

        text_rect = self._text_rect()

        if o.stroke_enabled:
            # Outline букв через QPainterPath
            self._paint_text_stroke(painter, text_rect)
        else:
            # Обычный текст через QTextDocument
            self._paint_text_plain(painter, text_rect)

    def _paint_text_plain(self, painter: QPainter, text_rect: QRectF):
        doc = self._make_document()
        doc.setTextWidth(text_rect.width())
        doc_h = doc.size().height()

        v_offset = self._v_offset(text_rect.height(), doc_h)

        painter.save()
        painter.translate(text_rect.x(), text_rect.y() + v_offset)
        painter.setClipRect(QRectF(0, 0, text_rect.width(), text_rect.height()))
        doc.drawContents(painter)
        painter.restore()

    def _paint_text_stroke(self, painter: QPainter, text_rect: QRectF):
        """Рисует текст с outline каждой буквы через QPainterPath + QTextLayout."""
        from PySide6.QtGui import QTextLayout

        o = self.obj
        font = self._make_font()
        metrics = QFontMetricsF(font)
        halign = _H_ALIGN.get(o.text_align_h, Qt.AlignmentFlag.AlignLeft)

        # Собираем все строки с учётом word_wrap
        lines_data = self._layout_lines(font, text_rect.width())
        total_h = sum(h for _, h in lines_data)

        v_offset = self._v_offset(text_rect.height(), total_h)

        painter.save()
        painter.translate(text_rect.x(), text_rect.y() + v_offset)
        painter.setClipRect(QRectF(0, 0, text_rect.width(), text_rect.height()))

        pen = QPen(QColor(o.stroke_color), o.stroke_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        y = 0.0
        for line_text, line_h in lines_data:
            line_w = metrics.horizontalAdvance(line_text)

            if halign == Qt.AlignmentFlag.AlignHCenter:
                x_off = (text_rect.width() - line_w) / 2
            elif halign == Qt.AlignmentFlag.AlignRight:
                x_off = text_rect.width() - line_w
            else:
                x_off = 0.0

            path = QPainterPath()
            path.addText(x_off, y + metrics.ascent(), font, line_text)
            painter.strokePath(path, pen)
            painter.fillPath(path, QColor(o.text_color))

            y += line_h

        painter.restore()

    def _layout_lines(self, font: QFont, width: float) -> list[tuple[str, float]]:
        """Разбивает текст на строки с учётом \\n и word_wrap.

        Возвращает список (текст_строки, высота_строки).
        """
        from PySide6.QtGui import QTextLayout, QTextOption

        o = self.obj
        metrics = QFontMetricsF(font)
        result = []

        for paragraph in o.text.split("\n"):
            if not paragraph:
                result.append(("", metrics.height() * o.line_height))
                continue

            layout = QTextLayout(paragraph, font)
            opt = QTextOption()
            opt.setWrapMode(
                QTextOption.WrapMode.WordWrap if o.word_wrap
                else QTextOption.WrapMode.NoWrap
            )
            layout.setTextOption(opt)
            layout.beginLayout()

            while True:
                line = layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(width)

            layout.endLayout()

            for i in range(layout.lineCount()):
                line = layout.lineAt(i)
                text = paragraph[line.textStart(): line.textStart() + line.textLength()]
                result.append((text, line.height() * o.line_height))

        return result

    def _v_offset(self, container_h: float, content_h: float) -> float:
        """Вертикальное смещение по выравниванию."""
        if self.obj.text_align_v == "middle":
            return max(0.0, (container_h - content_h) / 2)
        if self.obj.text_align_v == "bottom":
            return max(0.0, container_h - content_h)
        return 0.0
