"""Визуальное представление канваса.

Перенесено из preview/scene.py в objects/canvas_object.py,
чтобы все графические объекты были в одном месте.
"""

from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtCore import Qt, QRectF

from ...models import Canvas


class CanvasRectItem(QGraphicsRectItem):
    """Фон канваса. Объекты являются его дочерними элементами → клип по границам."""

    def __init__(self, canvas: Canvas, parent=None):
        super().__init__(0, 0, canvas.width, canvas.height, parent)
        self.canvas = canvas
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable,    False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemClipsChildrenToShape)
        self._refresh()

    def _refresh(self):
        self.setBrush(QBrush(QColor(self.canvas.background_color)))
        self.setPen(QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashLine))

    def update_appearance(self):
        self._refresh()

    def update_size(self):
        self.setRect(QRectF(0, 0, self.canvas.width, self.canvas.height))
