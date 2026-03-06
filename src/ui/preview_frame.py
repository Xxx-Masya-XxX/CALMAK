"""Панель превью - рендер объектов."""

from PySide6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QCursor, QFont, QBrush as QBrushGui,
    QPainterPath, QGlyphRun, QImage, QPolygonF, QStaticText
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal

from ..models import BaseObject, Canvas, TextObject


class CanvasRectItem(QGraphicsRectItem):
    """Визуальное представление канваса."""
    
    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(0, 0, canvas.width, canvas.height, parent)
        self.canvas = canvas
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(False)
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

    def __init__(self, obj: BaseObject, parent=None):
        super().__init__(0, 0, obj.width, obj.height, parent)
        self.obj = obj
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
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
        # Обновляем только размер, позиция управляется через setPos
        self.setRect(0, 0, self.obj.width, self.obj.height)
        self.setPos(self.obj.x, self.obj.y)

    def update_appearance(self):
        """Обновляет внешний вид."""
        color = QColor(self.obj.color)
        self.setBrush(QBrush(color))
        self.update()

    def paint(self, painter: QPainter, option, widget):
        """Рисует фигуру с обводкой и изображением."""
        painter.save()
        
        rect = self.rect()
        
        # Рисуем изображение если включено
        if self.obj.image_fill and self.obj.image_path:
            image = QImage(self.obj.image_path)
            if not image.isNull():
                painter.drawImage(rect, image)
                painter.restore()
                
                # Рисуем рамку выделения
                if self.isSelected():
                    painter.save()
                    pen = QPen(QColor(Qt.GlobalColor.blue), 2)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(rect)
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
        shape_type = self.obj.shape_type
        
        if shape_type == "ellipse":
            painter.drawEllipse(rect)
        elif shape_type == "triangle":
            # Рисуем треугольник
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

        # Позиция мыши относительно элемента
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
            # Позиция мыши относительно элемента
            local_pos = event.pos()
            edge = self._get_resize_edge(local_pos)

            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_pos = event.scenePos()
                # Сохраняем текущие значения объекта
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
        # Игнорируем изменение позиции во время изменения размера
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._resizing:
                return QPointF(0, 0)

            # Получаем абсолютную позицию на сцене
            scene_pos = self.scenePos()
            dx = scene_pos.x() - self.obj.x
            dy = scene_pos.y() - self.obj.y
            self.obj.x = scene_pos.x()
            self.obj.y = scene_pos.y()

            # Обновляем координаты дочерних объектов в модели и визуально
            if hasattr(self, 'scene') and self.scene():
                scene = self.scene()
                for child_obj, child_item in getattr(scene, '_object_items', {}).items():
                    if child_obj.parent_id == self.obj.id:
                        # Обновляем координаты в модели
                        child_obj.x += dx
                        child_obj.y += dy
                        # Обновляем позицию визуально
                        child_item.setPos(child_obj.x, child_obj.y)
                
                # Отправляем сигнал об изменении позиции для обновления в реальном времени
                scene.object_moved.emit(self.obj)

            return QPointF(0, 0)
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_appearance()

        return super().itemChange(change, value)


class TextGraphicsItem(QGraphicsTextItem):
    """Текстовый элемент с поддержкой изменения размера."""

    def __init__(self, obj: TextObject, parent=None):
        super().__init__(obj.text, parent)
        self.obj = obj
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        self._resizing = False
        self._resize_handle_size = 8.0
        self._resize_edge = None
        
        # Устанавливаем позицию и размер
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

        # Обновляем текст
        self.setPlainText(self.obj.text)

        # Ограничиваем текст по ширине
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

    def update_colors(self):
        """Обновляет цвета текста и обводки."""
        # Цвет текста
        self.setDefaultTextColor(QColor(self.obj.text_color))
        
        # Обновляем для перерисовки
        self.update()

    def boundingRect(self) -> QRectF:
        """Переопределённая граница для обработки изменения размера."""
        # Получаем реальные границы текста
        doc_rect = self.document().idealWidth(), self.document().size().height()
        base_rect = QRectF(0, 0, self.obj.width, max(self.obj.height, doc_rect[1]))
        return base_rect.adjusted(
            -self._resize_handle_size,
            -self._resize_handle_size,
            self._resize_handle_size,
            self._resize_handle_size
        )

    def paint(self, painter: QPainter, option, widget):
        """Рисует текст с обводкой и выравниванием."""
        # Вычисляем смещение для вертикального выравнивания
        doc_height = self.document().size().height()
        y_offset = 0

        if self.obj.text_align_v == "center":
            y_offset = (self.obj.height - doc_height) / 2
        elif self.obj.text_align_v == "bottom":
            y_offset = self.obj.height - doc_height

        # Применяем вертикальное выравнивание
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
            
            # Рисуем обводку через QTextLayout с правильными координатами
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
                            # Удаляем символ новой строки если есть
                            if line_text.endswith('\n'):
                                line_text = line_text[:-1]
                            if line_text:
                                path = QPainterPath()
                                # line.x() и line.y() - это абсолютные координаты внутри QGraphicsTextItem
                                path.addText(line.x(), line.y() + font.pointSize(), font, line_text)
                                painter.drawPath(path)
                
                block = block.next()

            painter.restore()

        # Рисуем обычный текст
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

        # Восстанавливаем трансформацию вертикального выравнивания
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
            scene_pos = self.scenePos()
            dx = scene_pos.x() - self.obj.x
            dy = scene_pos.y() - self.obj.y
            self.obj.x = scene_pos.x()
            self.obj.y = scene_pos.y()
            
            # Обновляем координаты дочерних объектов в модели и визуально
            if hasattr(self, 'scene') and self.scene():
                scene = self.scene()
                for child_obj, child_item in getattr(scene, '_object_items', {}).items():
                    if child_obj.parent_id == self.obj.id:
                        # Обновляем координаты в модели
                        child_obj.x += dx
                        child_obj.y += dy
                        # Обновляем позицию визуально
                        child_item.setPos(child_obj.x, child_obj.y)
                
                # Отправляем сигнал об изменении позиции для обновления в реальном времени
                scene.object_moved.emit(self.obj)
            
            return QPointF(0, 0)
        elif change == QGraphicsTextItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()

        return super().itemChange(change, value)


class PreviewScene(QGraphicsScene):
    """Сцена превью для одного канваса."""

    object_selected = Signal(BaseObject)
    object_changed = Signal(BaseObject)
    object_moved = Signal(BaseObject)  # Сигнал для обновления в реальном времени

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self._object_items: dict[BaseObject, ResizableRectItem | TextGraphicsItem] = {}
        self._items_by_id: dict[str, ResizableRectItem | TextGraphicsItem] = {}

        # Добавляем фон канваса
        self.canvas_item = CanvasRectItem(canvas)
        self.addItem(self.canvas_item)

        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Обработчик изменения выделения."""
        for item in self.selectedItems():
            if isinstance(item, (ResizableRectItem, TextGraphicsItem)):
                self.object_selected.emit(item.obj)
                break

    def add_object(self, obj: BaseObject) -> ResizableRectItem | TextGraphicsItem:
        """Добавляет объект на сцену."""
        if isinstance(obj, TextObject):
            item = TextGraphicsItem(obj)
        else:
            item = ResizableRectItem(obj)

        self._object_items[obj] = item
        self._items_by_id[obj.id] = item

        # Добавляем на сцену (без setParentItem)
        self.addItem(item)

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
            item.update()  # Обновляем для перерисовки обводки

    def rebuild_object_parent(self, obj: BaseObject):
        """Перестраивает иерархию для объекта (при изменении родителя)."""
        if obj not in self._object_items:
            return

        item = self._object_items[obj]
        parent_obj = None

        # Находим родителя
        if obj.parent_id and obj.parent_id in self._items_by_id:
            parent_obj = self._get_object_by_id(obj.parent_id)

        # Сохраняем абсолютную позицию
        abs_pos = item.scenePos()

        # Устанавливаем новую позицию
        if parent_obj:
            # Позиция относительно родителя
            item.setPos(obj.x, obj.y)
        else:
            item.setPos(abs_pos)

    def update_canvas(self):
        """Обновляет канвас."""
        self.canvas_item.update_size()
        self.canvas_item.update_appearance()
        self.setSceneRect(self.canvas_item.boundingRect())

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
    object_moved = Signal(BaseObject)  # Сигнал для обновления в реальном времени
    canvas_selected = Signal(object)  # canvas_id

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
        # Создаём сцену
        scene = PreviewScene(canvas)
        scene.object_selected.connect(self.object_selected.emit)
        scene.object_changed.connect(self.object_changed.emit)
        scene.object_moved.connect(self.object_moved.emit)

        # Создаём view
        view = QGraphicsView(self)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        view.setScene(scene)
        view.setSceneRect(0, 0, canvas.width, canvas.height)
        
        # Добавляем в стек
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
