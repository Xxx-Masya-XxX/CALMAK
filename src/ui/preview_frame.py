"""Панель превью - рендер объектов с поддержкой иерархии."""

from PySide6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QCursor, QFont, QImage, QPolygonF, QPainterPath
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal

from ..models import BaseObject, Canvas, TextObject


class ClippedGraphicsView(QGraphicsView):
    """QGraphicsView с обрезкой рендеринга по границам сцены и поддержкой зума."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_factor = 1.0
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        # Включаем зум колесом мыши
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event):
        """Обработка колеса мыши для зума."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Зум колесом при зажатом Ctrl
            delta = event.angleDelta().y()
            if delta > 0:
                self.scale(1.1, 1.1)
                self._zoom_factor *= 1.1
            else:
                self.scale(1 / 1.1, 1 / 1.1)
                self._zoom_factor /= 1.1
            event.accept()
            return
        super().wheelEvent(event)

    def reset_zoom(self):
        """Сбрасывает зум к 100%."""
        self.resetTransform()
        self._zoom_factor = 1.0

    def get_zoom_factor(self) -> float:
        """Возвращает текущий фактор зума."""
        return self._zoom_factor


class CanvasRectItem(QGraphicsRectItem):
    """Визуальное представление канваса с обрезкой дочерних элементов."""

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(0, 0, canvas.width, canvas.height, parent)
        self.canvas = canvas
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(False)
        # Включаем обрезку дочерних элементов по границам этого элемента
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemClipsChildrenToShape)
        self.update_appearance()

    def update_appearance(self):
        """Обновляет внешний вид канваса."""
        color = QColor(self.canvas.background_color)
        self.setBrush(QBrush(color))
        pen = QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashLine)
        self.setPen(pen)

    def update_size(self):
        """Обновляет размер канваса."""
        self.setRect(QRectF(0, 0, self.canvas.width, self.canvas.height))


class ResizableRectItem(QGraphicsRectItem):
    """Прямоугольник с поддержкой изменения размера."""

    def __init__(self, obj: BaseObject, parent_item: QGraphicsRectItem = None):
        super().__init__(0, 0, obj.width, obj.height, parent_item)
        self.obj = obj
        # Устанавливаем флаги в зависимости от блокировки
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._resizing = False
        self._resize_handle_size = 8.0
        self._current_cursor = None
        self._resize_edge = None

        self.update_geometry()
        self.update_appearance()

    def update_geometry(self):
        """Обновляет геометрию из модели."""
        self.setRect(0, 0, self.obj.width, self.obj.height)
        # Позиция устанавливается через setPos - локальные координаты
        self.setPos(self.obj.x, self.obj.y)
        # Смещаем центр вращения в центр объекта
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        # Поворот
        self.setRotation(self.obj.rotation)

    def update_appearance(self):
        """Обновляет внешний вид."""
        color = QColor(self.obj.color)
        self.setBrush(QBrush(color))
        # Обновляем флаг перемещения при изменении locked
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, not self.obj.locked)
        # Смещаем центр вращения в центр объекта
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        # Обновляем поворот
        self.setRotation(self.obj.rotation)
        self.update()

    def paint(self, painter: QPainter, option, widget):
        """Рисует фигуру с обводкой и изображением."""
        painter.save()

        rect = self.rect()
        shape_type = self.obj.shape_type

        # Создаём путь для обрезки изображения по форме фигуры
        clip_path = QPainterPath()
        if shape_type == "ellipse":
            clip_path.addEllipse(rect)
        elif shape_type == "triangle":
            polygon = QPolygonF([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.bottomRight()),
                QPointF(rect.bottomLeft())
            ])
            clip_path.addPolygon(polygon)
        else:  # rect
            clip_path.addRect(rect)

        # Добавляем обрезку по границам родительского элемента (канваса)
        # чтобы изображение не рендерилось за пределами канваса
        parent_clip_path = QPainterPath()
        if self.parentItem():
            parent_rect = self.parentItem().boundingRect()
            parent_clip_path.addRect(parent_rect)
            clip_path = clip_path.intersected(parent_clip_path)

        # Рисуем изображение если включено - с обрезкой по форме фигуры и канваса
        if self.obj.image_fill and self.obj.image_path:
            image = QImage(self.obj.image_path)
            if not image.isNull():
                painter.save()
                painter.setClipPath(clip_path)
                painter.drawImage(rect, image)
                painter.restore()

                # Рисуем обводку поверх изображения
                if self.obj.stroke_enabled:
                    pen = QPen(QColor(self.obj.stroke_color), self.obj.stroke_width)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(clip_path)

                # Рисуем рамку выделения
                if self.isSelected():
                    painter.save()
                    pen = QPen(QColor(Qt.GlobalColor.blue), 2)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(clip_path)
                    painter.restore()
                painter.restore()
                return

        # Рисуем заливку цветом
        color = QColor(self.obj.color)
        painter.setBrush(QBrush(color))

        # Рисуем обводку если включена
        if self.obj.stroke_enabled:
            pen = QPen(QColor(self.obj.stroke_color), self.obj.stroke_width)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        # Рисуем фигуру в зависимости от типа
        if shape_type == "ellipse":
            painter.drawEllipse(rect)
        elif shape_type == "triangle":
            polygon = QPolygonF([
                QPointF(rect.center().x(), rect.top()),
                QPointF(rect.bottomRight()),
                QPointF(rect.bottomLeft())
            ])
            painter.drawPolygon(polygon)
        else:  # rect
            painter.drawRect(rect)

        painter.restore()

        # Рисуем рамку выделения
        if self.isSelected():
            painter.save()
            pen = QPen(QColor(Qt.GlobalColor.blue), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            painter.restore()

    def _get_resize_edge(self, pos: QPointF) -> str | None:
        """Определяет край для изменения размера."""
        rect = self.rect()
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
            self._current_cursor = edge
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._current_cursor = None

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
                self._original_x = self.obj.x
                self._original_y = self.obj.y
                self._original_width = self.obj.width
                self._original_height = self.obj.height
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши."""
        if self._resizing and self._resize_edge:
            delta = event.scenePos() - self._resize_start_pos
            edge = self._resize_edge

            # Изменение по X
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

            # Изменение по Y
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

            self.update_geometry()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Сброс изменения размера при двойном клике."""
        self._resizing = False
        self._resize_edge = None
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        """Обработка изменений элемента."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._resizing:
                return QPointF(0, 0)

            # Получаем новую локальную позицию
            new_pos = value.toPoint()
            
            # Обновляем координаты в модели (локальные координаты)
            dx = new_pos.x() - self.obj.x
            dy = new_pos.y() - self.obj.y
            self.obj.x = new_pos.x()
            self.obj.y = new_pos.y()

            # Отправляем сигнал об изменении позиции для обновления в реальном времени
            if hasattr(self, 'scene') and self.scene():
                scene = self.scene()
                scene.object_moved.emit(self.obj)

            return new_pos
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_appearance()

        return super().itemChange(change, value)


class TextGraphicsItem(QGraphicsTextItem):
    """Текстовый элемент с поддержкой изменения размера."""

    def __init__(self, obj: TextObject, parent_item: QGraphicsTextItem = None):
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
        # Обновляем поворот
        self.setRotation(self.obj.rotation)

    def update_colors(self):
        """Обновляет цвета текста и обводки."""
        self.setDefaultTextColor(QColor(self.obj.text_color))
        # Обновляем флаг перемещения при изменении locked
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, not self.obj.locked)
        # Смещаем центр вращения в центр объекта
        self.setTransformOriginPoint(self.obj.width / 2, self.obj.height / 2)
        # Обновляем поворот
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
        # Добавляем обрезку по границам родительского элемента (канваса)
        if self.parentItem():
            parent_rect = self.parentItem().boundingRect()
            painter.setClipRect(parent_rect, Qt.ClipOperation.IntersectClip)
        
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

            # Изменение по X
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

            # Изменение по Y
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

            # Получаем новую локальную позицию
            new_pos = value.toPoint()
            
            # Обновляем координаты в модели (локальные координаты)
            self.obj.x = new_pos.x()
            self.obj.y = new_pos.y()

            # Отправляем сигнал об изменении позиции
            if hasattr(self, 'scene') and self.scene():
                scene = self.scene()
                scene.object_moved.emit(self.obj)

            return new_pos
        elif change == QGraphicsTextItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()

        return super().itemChange(change, value)


class PreviewScene(QGraphicsScene):
    """Сцена превью для одного канваса."""

    object_selected = Signal(BaseObject)
    object_changed = Signal(BaseObject)
    object_moved = Signal(BaseObject)

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self._object_items: dict[BaseObject, ResizableRectItem | TextGraphicsItem] = {}
        self._items_by_id: dict[str, ResizableRectItem | TextGraphicsItem] = {}

        # Добавляем фон канваса
        self.canvas_item = CanvasRectItem(canvas)
        self.addItem(self.canvas_item)

        # Устанавливаем обрезку по границам сцены (канваса)
        self.setSceneRect(0, 0, canvas.width, canvas.height)
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Обработчик изменения выделения."""
        for item in self.selectedItems():
            if isinstance(item, (ResizableRectItem, TextGraphicsItem)):
                self.object_selected.emit(item.obj)
                break

    def add_object(self, obj: BaseObject) -> ResizableRectItem | TextGraphicsItem:
        """Добавляет объект на сцену."""
        # Создаём элемент
        if isinstance(obj, TextObject):
            item = TextGraphicsItem(obj)
        else:
            item = ResizableRectItem(obj)

        self._object_items[obj] = item
        self._items_by_id[obj.id] = item

        # Находим родительский элемент
        parent_item = None
        parent_obj = None
        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_item = self._items_by_id[obj.parent_id]
            parent_obj = self._get_object_by_id(obj.parent_id)
            # Устанавливаем родителя - позиция будет относительно родителя
            item.setParentItem(parent_item)
            obj._parent = parent_obj
            # Устанавливаем zValue больше чем у родителя (дочерние рендерятся поверх)
            item.setZValue(parent_item.zValue() + 1)
            # Добавляем на сцену через родителя
            self.addItem(item)
        else:
            # Нет родителя - добавляем как child canvas_item для обрезки
            item.setParentItem(self.canvas_item)
            item.setZValue(0)

        # Устанавливаем локальную позицию
        item.setPos(obj.x, obj.y)

        return item

    def _get_object_by_id(self, obj_id: str) -> BaseObject | None:
        """Получает объект по ID."""
        for obj in self._object_items.keys():
            if obj.id == obj_id:
                return obj
        return None

    def remove_object(self, obj: BaseObject):
        """Удаляет объект со сцены."""
        if obj in self._object_items:
            item = self._object_items[obj]
            # Сначала удаляем дочерние элементы
            children = [o for o in self._object_items.keys() if o.parent_id == obj.id]
            for child in children:
                self.remove_object(child)

            self.removeItem(item)
            del self._object_items[obj]
            if obj.id in self._items_by_id:
                del self._items_by_id[obj.id]

    def update_object(self, obj: BaseObject):
        """Обновляет объект на сцене."""
        if obj in self._object_items:
            item = self._object_items[obj]
            if isinstance(item, TextGraphicsItem):
                item.update_font()
                item.update_colors()
            else:
                item.update_geometry()
                item.update_appearance()
            item.update()

    def rebuild_object_parent(self, obj: BaseObject):
        """Перестраивает иерархию для объекта (при изменении родителя).

        При смене родителя координаты пересчитываются:
        - Сохраняем глобальную позицию
        - Конвертируем в локальные координаты нового родителя
        """
        if obj not in self._object_items:
            return

        item = self._object_items[obj]

        # Сохраняем текущую глобальную позицию на сцене
        global_pos = item.scenePos()

        # Находим нового родителя
        new_parent_item = None
        new_parent_obj = None
        if obj.parent_id and obj.parent_id in self._items_by_id:
            new_parent_item = self._items_by_id[obj.parent_id]
            new_parent_obj = self._get_object_by_id(obj.parent_id)

        # Сбрасываем родителя
        item.setParentItem(None)
        obj._parent = None

        # Устанавливаем нового родителя
        if new_parent_item:
            item.setParentItem(new_parent_item)
            obj._parent = new_parent_obj
            # Обновляем zValue
            item.setZValue(new_parent_item.zValue() + 1)

            # Пересчитываем локальные координаты относительно нового родителя
            if new_parent_obj:
                parent_global = new_parent_obj.get_global_position()
                obj.x = global_pos.x() - parent_global[0]
                obj.y = global_pos.y() - parent_global[1]
            else:
                obj.x = global_pos.x()
                obj.y = global_pos.y()
        else:
            # Нет родителя - добавляем как child canvas_item для обрезки
            item.setParentItem(self.canvas_item)
            # Сбрасываем zValue для корневого объекта
            item.setZValue(0)
            # Используем глобальные координаты как локальные
            obj.x = global_pos.x()
            obj.y = global_pos.y()
        
        # Обновляем позицию элемента
        item.setPos(obj.x, obj.y)

    def update_canvas(self):
        """Обновляет канвас."""
        self.canvas_item.update_appearance()
        self.canvas_item.update_size()
        # Явно устанавливаем sceneRect в (0, 0, width, height)
        self.setSceneRect(0, 0, self.canvas.width, self.canvas.height)

    def clear_selection(self):
        """Снимает выделение со всех объектов."""
        self.clearSelection()

    def clear_objects(self):
        """Очищает все объекты."""
        for obj in list(self._object_items.keys()):
            self.remove_object(obj)


class PreviewFrame(QWidget):
    """Панель превью с поддержкой нескольких канвасов."""

    object_selected = Signal(BaseObject)
    object_changed = Signal(BaseObject)
    object_moved = Signal(BaseObject)
    canvas_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QStackedWidget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Стек для переключения между канвасами
        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        # Хранилище сцен по канвасам
        self._scenes: dict[str, PreviewScene] = {}
        self._views: dict[str, QGraphicsView] = {}

    def add_canvas(self, canvas: Canvas) -> PreviewScene:
        """Добавляет канвас для отображения."""
        scene = PreviewScene(canvas)
        scene.object_selected.connect(self.object_selected.emit)
        scene.object_changed.connect(self.object_changed.emit)
        scene.object_moved.connect(self.object_moved.emit)

        view = ClippedGraphicsView(self)
        view.setScene(scene)
        view.setSceneRect(0, 0, canvas.width, canvas.height)

        self._scenes[canvas.id] = scene
        self._views[canvas.id] = view
        self.stacked_widget.addWidget(view)

        return scene

    def remove_canvas(self, canvas_id: str):
        """Удаляет канвас."""
        if canvas_id in self._scenes:
            scene = self._scenes[canvas_id]
            view = self._views[canvas_id]
            index = self.stacked_widget.indexOf(view)
            self.stacked_widget.removeWidget(view)
            scene.clear()
            del self._scenes[canvas_id]
            del self._views[canvas_id]

    def set_active_canvas(self, canvas_id: str):
        """Переключается на указанный канвас."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            index = self.stacked_widget.indexOf(view)
            self.stacked_widget.setCurrentIndex(index)

    def get_scene(self, canvas_id: str) -> PreviewScene | None:
        """Получает сцену канваса."""
        return self._scenes.get(canvas_id)

    def add_object(self, canvas_id: str, obj: BaseObject):
        """Добавляет объект на канвас."""
        scene = self.get_scene(canvas_id)
        if scene:
            scene.add_object(obj)

    def remove_object(self, canvas_id: str, obj: BaseObject):
        """Удаляет объект с канваса."""
        scene = self.get_scene(canvas_id)
        if scene:
            scene.remove_object(obj)

    def update_object(self, canvas_id: str, obj: BaseObject):
        """Обновляет объект на канвасе."""
        scene = self.get_scene(canvas_id)
        if scene:
            scene.update_object(obj)

    def update_canvas(self, canvas_id: str):
        """Обновляет канвас."""
        scene = self.get_scene(canvas_id)
        if scene:
            scene.update_canvas()
            view = self._views[canvas_id]
            view.setSceneRect(0, 0, scene.canvas.width, scene.canvas.height)

    def zoom_in(self, canvas_id: str):
        """Увеличивает масштаб для указанного канваса."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            view.scale(1.1, 1.1)

    def zoom_out(self, canvas_id: str):
        """Уменьшает масштаб для указанного канваса."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            view.scale(1 / 1.1, 1 / 1.1)

    def reset_zoom(self, canvas_id: str):
        """Сбрасывает масштаб для указанного канваса к 100%."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            view.reset_zoom()

    def get_zoom_factor(self, canvas_id: str) -> float:
        """Возвращает текущий фактор масштаба для указанного канваса."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            return view.get_zoom_factor()
        return 1.0
