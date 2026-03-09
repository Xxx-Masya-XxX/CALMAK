"""Панель превью - рендер объектов с поддержкой иерархии."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView
from PySide6.QtGui import QPainter, QCursor
from PySide6.QtCore import Qt, QRectF, Signal

from ...models import Canvas, BaseObject
from .scene import PreviewScene


class ClippedGraphicsView(QGraphicsView):
    """QGraphicsView с обрезкой рендеринга по границам сцены и поддержкой зума."""

    zoom_changed = Signal(float)

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
            self.zoom_changed.emit(self._zoom_factor)
            event.accept()
            return
        super().wheelEvent(event)

    def reset_zoom(self):
        """Сбрасывает зум к 100%."""
        self.resetTransform()
        self._zoom_factor = 1.0
        self.zoom_changed.emit(self._zoom_factor)

    def get_zoom_factor(self) -> float:
        """Возвращает текущий фактор зума."""
        return self._zoom_factor


class PreviewFrame(QWidget):
    """Панель превью с поддержкой нескольких канвасов."""

    object_selected = Signal(BaseObject)
    object_moved = Signal(BaseObject)
    zoom_changed = Signal(float)  # Сигнал об изменении зума

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self._scenes: dict[str, PreviewScene] = {}
        self._views: dict[str, ClippedGraphicsView] = {}
        self._active_canvas_id: str | None = None

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stack для переключения между сценами
        self._stack_widget = QWidget()
        self._stack_layout = QVBoxLayout(self._stack_widget)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack_widget)

    def add_canvas(self, canvas: Canvas):
        """Добавляет канвас для превью."""
        # Создаём сцену
        scene = PreviewScene(canvas)
        scene.object_selected.connect(self.object_selected.emit)
        scene.object_moved.connect(self.object_moved.emit)
        self._scenes[canvas.id] = scene

        # Создаём view
        view = ClippedGraphicsView()
        view.setScene(scene)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        view.zoom_changed.connect(self.zoom_changed.emit)
        self._views[canvas.id] = view

        # Добавляем в стек
        self._stack_layout.addWidget(view)
        view.setVisible(False)

    def remove_canvas(self, canvas_id: str):
        """Удаляет канвас из превью."""
        if canvas_id in self._scenes:
            scene = self._scenes[canvas_id]
            view = self._views[canvas_id]

            self._stack_layout.removeWidget(view)
            view.deleteLater()
            scene.deleteLater()

            del self._scenes[canvas_id]
            del self._views[canvas_id]

            if self._active_canvas_id == canvas_id:
                self._active_canvas_id = None

    def set_active_canvas(self, canvas_id: str):
        """Устанавливает активный канвас для отображения."""
        # Скрываем все view
        for view in self._views.values():
            view.setVisible(False)

        # Показываем нужный
        if canvas_id in self._views:
            self._views[canvas_id].setVisible(True)
            self._active_canvas_id = canvas_id

    def get_scene(self, canvas_id: str) -> PreviewScene | None:
        """Получает сцену для канваса."""
        return self._scenes.get(canvas_id)

    def get_view(self, canvas_id: str) -> ClippedGraphicsView | None:
        """Получает view для канваса."""
        return self._views.get(canvas_id)

    def add_object(self, canvas_id: str, obj: BaseObject):
        """Добавляет объект на сцену канваса."""
        if canvas_id in self._scenes:
            self._scenes[canvas_id].add_object(obj)

    def remove_object(self, canvas_id: str, obj: BaseObject):
        """Удаляет объект со сцены канваса."""
        if canvas_id in self._scenes:
            self._scenes[canvas_id].remove_object(obj)

    def update_object(self, canvas_id: str, obj: BaseObject):
        """Обновляет объект на сцене канваса."""
        if canvas_id in self._scenes:
            self._scenes[canvas_id].update_object(obj)

    def update_canvas(self, canvas_id: str):
        """Обновляет канвас."""
        if canvas_id in self._scenes:
            canvas = self._scenes[canvas_id].canvas
            self._scenes[canvas_id].update_canvas(canvas)

    def get_zoom_factor(self, canvas_id: str) -> float:
        """Получает масштаб для канваса."""
        if canvas_id in self._views:
            return self._views[canvas_id].get_zoom_factor()
        return 1.0

    def zoom_in(self, canvas_id: str):
        """Увеличивает масштаб."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            view.scale(1.1, 1.1)
            view._zoom_factor *= 1.1
            view.zoom_changed.emit(view._zoom_factor)

    def zoom_out(self, canvas_id: str):
        """Уменьшает масштаб."""
        if canvas_id in self._views:
            view = self._views[canvas_id]
            view.scale(1 / 1.1, 1 / 1.1)
            view._zoom_factor /= 1.1
            view.zoom_changed.emit(view._zoom_factor)

    def reset_zoom(self, canvas_id: str):
        """Сбрасывает масштаб к 100%."""
        if canvas_id in self._views:
            self._views[canvas_id].reset_zoom()

    def select_object(self, canvas_id: str, obj: BaseObject) -> None:
        """Выделяет объект на сцене."""
        if canvas_id in self._scenes:
            self._scenes[canvas_id].select_object(obj)
