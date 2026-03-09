"""Миксин для графических элементов с поддержкой изменения размера."""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt, QRectF, QPointF

from ....models.objects.base_object import BaseObject


class ResizeMixin:
    """Миксин для добавления функциональности изменения размера.

    Предоставляет:
    - Определение края для изменения размера
    - Обработку курсоров
    - Обработку событий мыши для изменения размера
    """

    obj: BaseObject
    _resizing: bool
    _resize_handle_size: float
    _resize_edge: str | None
    _resize_start_pos: QPointF
    _original_x: float
    _original_y: float
    _original_width: float
    _original_height: float
    _current_cursor: str | None

    def _get_resize_edge(self, pos: QPointF) -> str | None:
        """Определяет край для изменения размера."""
        rect = self.bounding_rect_for_resize()
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

    def bounding_rect_for_resize(self) -> QRectF:
        """Возвращает границы для изменения размера."""
        return self.rect() if hasattr(self, 'rect') else self.boundingRect()

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

    def resize_mouse_press(self, event) -> bool:
        """Обработка нажатия мыши для изменения размера.

        Returns:
            True если событие обработано.
        """
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
                return True
        return False

    def resize_mouse_move(self, event) -> bool:
        """Обработка перемещения мыши для изменения размера.

        Returns:
            True если событие обработано.
        """
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

            self.update_geometry()
            self.on_resize()
            event.accept()
            return True
        return False

    def on_resize(self):
        """Вызывается после изменения размера.

        Переопределяется в наследниках для специфичной логики.
        """
        pass

    def resize_mouse_release(self, event) -> None:
        """Обработка отпускания мыши для изменения размера."""
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = None

    def resize_hover_move(self, event) -> bool:
        """Обработка наведения мыши для изменения размера.

        Returns:
            True если событие обработано.
        """
        if self._resizing:
            event.ignore()
            return True

        local_pos = event.pos()
        edge = self._get_resize_edge(local_pos)

        if edge:
            self.setCursor(self._get_cursor_for_edge(edge))
            self._current_cursor = edge
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._current_cursor = None
        return False
