"""Панель предпросмотра с интерактивным редактированием элементов."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QImage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.elements import CanvasElement


class GraphicsImageItem(QGraphicsRectItem):
    """Графический элемент изображения."""

    def __init__(self, element: "CanvasElement", scene_ref):
        super().__init__()
        self._element = element
        self._scene_ref = scene_ref
        self.setRect(0, 0, element.width, element.height)
        self.setPos(element.x, element.y)
        
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Загрузка изображения
        if hasattr(element, 'image_path') and element.image_path:
            image = QImage(element.image_path)
            if not image.isNull():
                self.image = image.scaled(int(element.width), int(element.height), 
                                          Qt.AspectRatioMode.KeepAspectRatio)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self._scene_ref()
            if scene:
                scene.element_moved.emit(self._element.id, self.pos().x(), self.pos().y())
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Рисуем изображение
        if hasattr(self, 'image'):
            painter.drawImage(self.rect(), self.image)

        # Рамка выделения
        if self.isSelected():
            pen = QPen(QColor("#3498db"), 2)
            pen.setDashPattern([5, 3])
            painter.setPen(pen)
            painter.setBrush(QBrush())
            painter.drawRect(self.rect())


class GraphicsTextItem(QGraphicsRectItem):
    """Графический элемент текста."""

    def __init__(self, element: "CanvasElement", scene_ref):
        super().__init__()
        self._element = element
        self._scene_ref = scene_ref
        self.setRect(0, 0, element.width, element.height)
        self.setPos(element.x, element.y)
        
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self._scene_ref()
            if scene:
                scene.element_moved.emit(self._element.id, self.pos().x(), self.pos().y())
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Рисуем текст
        text_element = self._element
        font = QFont(text_element.font_family, text_element.font_size)
        font.setBold(text_element.bold)
        font.setItalic(text_element.italic)
        painter.setFont(font)
        painter.setPen(QColor(text_element.color))

        # Рамка выделения
        if self.isSelected():
            pen = QPen(QColor("#3498db"), 2)
            pen.setDashPattern([5, 3])
            painter.setPen(pen)
            painter.setBrush(QBrush())
            painter.drawRect(self.rect())
            painter.setPen(QColor(text_element.color))

        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, 
                        text_element.text)


class GraphicsShapeItem(QGraphicsRectItem):
    """Графический элемент фигуры."""

    def __init__(self, element: "CanvasElement", scene_ref):
        super().__init__()
        self._element = element
        self._scene_ref = scene_ref
        self.setRect(0, 0, element.width, element.height)
        self.setPos(element.x, element.y)
        
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self._scene_ref()
            if scene:
                scene.element_moved.emit(self._element.id, self.pos().x(), self.pos().y())
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        shape_element = self._element

        # Настройка кисти
        if shape_element.fill_color:
            fill_color = QColor(shape_element.fill_color)
            fill_color.setAlphaF(shape_element.opacity)
            brush = QBrush(fill_color)
            painter.setBrush(brush)
        else:
            painter.setBrush(QBrush())

        # Настройка пера
        pen = QPen(QColor(shape_element.stroke_color), shape_element.stroke_width)
        painter.setPen(pen)

        # Рисуем фигуру
        if shape_element.shape_type == "rectangle":
            painter.drawRect(self.rect())
        elif shape_element.shape_type == "ellipse":
            painter.drawEllipse(self.rect())

        # Рамка выделения
        if self.isSelected():
            pen = QPen(QColor("#3498db"), 2)
            pen.setDashPattern([5, 3])
            painter.setPen(pen)
            painter.setBrush(QBrush())
            if shape_element.shape_type == "rectangle":
                painter.drawRect(self.rect())
            elif shape_element.shape_type == "ellipse":
                painter.drawEllipse(self.rect())


class PreviewScene(QGraphicsScene):
    """Сцена для предпросмотра с сигналом о перемещении элементов."""

    element_moved = Signal(str, float, float)  # element_id, x, y
    element_selected = Signal(object)  # CanvasElement

    def __init__(self, parent=None):
        super().__init__(parent)
        self._elements_map = {}  # id -> QGraphicsItem
        self._canvas = None

    def set_canvas(self, canvas: "CanvasElement") -> None:
        """Установить канвас и отрисовать все элементы."""
        self._canvas = canvas
        self.clear()
        self._elements_map.clear()

        # Добавляем фон канваса
        canvas_rect = QGraphicsRectItem(0, 0, canvas.width, canvas.height)
        canvas_rect.setBrush(QBrush(QColor("#ffffff")))
        canvas_rect.setPen(QPen(QColor("#cccccc"), 1))
        self.addItem(canvas_rect)

        # Добавляем все элементы
        self._add_elements(canvas.children)

    def _add_elements(self, elements: list["CanvasElement"]) -> None:
        """Добавить элементы на сцену."""
        for element in elements:
            if not element.visible:
                continue

            graphics_item = self._create_graphics_item(element)
            if graphics_item:
                self.addItem(graphics_item)
                self._elements_map[element.id] = graphics_item

            # Рекурсивно добавляем дочерние элементы
            if hasattr(element, 'children'):
                self._add_elements(element.children)

    def _create_graphics_item(self, element: "CanvasElement"):
        """Создать графический элемент для элемента канваса."""
        from ..models.elements import ImageElement, TextElement, ShapeElement

        scene_ref = lambda: self

        if isinstance(element, ImageElement):
            return GraphicsImageItem(element, scene_ref)
        elif isinstance(element, TextElement):
            return GraphicsTextItem(element, scene_ref)
        elif isinstance(element, ShapeElement):
            return GraphicsShapeItem(element, scene_ref)

        return None

    def refresh(self) -> None:
        """Обновить сцену."""
        if self._canvas:
            self.set_canvas(self._canvas)

    def update_element_position(self, element_id: str, x: float, y: float) -> None:
        """Обновить позицию элемента в модели."""
        # Сцена только отправляет сигнал, обновление модели происходит в MainWindow
        pass


class PreviewFrame(QWidget):
    """Панель предпросмотра с интерактивным редактированием."""

    element_moved = Signal(str, float, float)  # element_id, x, y
    element_selected = Signal(object)  # CanvasElement

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Заголовок
        from PySide6.QtWidgets import QLabel
        title = QLabel("Предпросмотр")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # QGraphicsView для предпросмотра
        self.scene = PreviewScene(self)
        self.scene.element_moved.connect(self.element_moved.emit)

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        layout.addWidget(self.view)

    def set_canvas(self, canvas: "CanvasElement") -> None:
        """Установить канвас для предпросмотра."""
        self.scene.set_canvas(canvas)
        # Подгоняем размер view под канвас
        self.scene.setSceneRect(0, 0, canvas.width + 50, canvas.height + 50)

    def refresh(self) -> None:
        """Обновить предпросмотр."""
        self.scene.refresh()
