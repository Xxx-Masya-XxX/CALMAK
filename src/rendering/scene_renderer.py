"""
Rendering layer: синхронизирует DocumentState с QGraphicsScene.
QGraphicsItem — только визуальный адаптер. Истина — в DocumentState.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QColor, QBrush, QPen, QFont, QPixmap, QPainter,
                            QFontMetrics, QPainterPath)
from PySide6.QtWidgets import (QGraphicsScene, QGraphicsItem,
                                QGraphicsRectItem, QGraphicsEllipseItem,
                                QGraphicsTextItem, QGraphicsPixmapItem,
                                QGraphicsItemGroup, QGraphicsPathItem)

from domain.models import (ObjectState, ObjectType, CanvasState,
                            TextPayload, ImagePayload, StyleState)

if TYPE_CHECKING:
    from state.editor_store import EditorStore


# ---------------------------------------------------------------------------
# Item Registry: object_id ↔ QGraphicsItem
# ---------------------------------------------------------------------------

class SceneItemRegistry:
    def __init__(self):
        self._id_to_item: dict[str, QGraphicsItem] = {}
        self._item_to_id: dict[int, str] = {}   # id(item) → object_id

    def register(self, obj_id: str, item: QGraphicsItem):
        self._id_to_item[obj_id] = item
        self._item_to_id[id(item)] = obj_id

    def unregister(self, obj_id: str):
        item = self._id_to_item.pop(obj_id, None)
        if item is not None:
            self._item_to_id.pop(id(item), None)

    def get_item(self, obj_id: str) -> QGraphicsItem | None:
        return self._id_to_item.get(obj_id)

    def get_id(self, item: QGraphicsItem) -> str | None:
        return self._item_to_id.get(id(item))

    def clear(self):
        self._id_to_item.clear()
        self._item_to_id.clear()

    def all_ids(self) -> list[str]:
        return list(self._id_to_item.keys())


# ---------------------------------------------------------------------------
# Item factory helpers
# ---------------------------------------------------------------------------

def _color(hex_str: str, alpha: float = 1.0) -> QColor:
    if hex_str == "transparent":
        return QColor(0, 0, 0, 0)
    c = QColor(hex_str)
    c.setAlphaF(alpha)
    return c


def _apply_transform(item: QGraphicsItem, obj: ObjectState):
    t = obj.transform
    item.setPos(t.x, t.y)
    item.setRotation(t.rotation)
    item.setOpacity(t.opacity)


def _apply_style_rect(item: QGraphicsRectItem, obj: ObjectState):
    s = obj.style
    t = obj.transform
    item.setRect(0, 0, t.width, t.height)
    item.setBrush(QBrush(_color(s.fill_color)))
    pen = QPen(_color(s.stroke_color), s.stroke_width)
    item.setPen(pen)


def _apply_style_ellipse(item: QGraphicsEllipseItem, obj: ObjectState):
    s = obj.style
    t = obj.transform
    item.setRect(0, 0, t.width, t.height)
    item.setBrush(QBrush(_color(s.fill_color)))
    pen = QPen(_color(s.stroke_color), s.stroke_width)
    item.setPen(pen)


def _apply_style_text(item: QGraphicsTextItem, obj: ObjectState):
    s = obj.style
    t = obj.transform
    payload = obj.payload
    if isinstance(payload, TextPayload):
        item.setPlainText(payload.text)
    font = QFont(s.font_family, s.font_size)
    font.setBold(s.bold)
    font.setItalic(s.italic)
    item.setFont(font)
    item.setDefaultTextColor(_color(s.text_color))
    item.setTextWidth(t.width)


def _apply_style_image(item: QGraphicsPixmapItem, obj: ObjectState):
    t = obj.transform
    payload = obj.payload
    if isinstance(payload, ImagePayload) and payload.source_path:
        pix = QPixmap(payload.source_path)
        if not pix.isNull():
            pix = pix.scaled(int(t.width), int(t.height),
                              Qt.KeepAspectRatio,
                              Qt.SmoothTransformation)
            item.setPixmap(pix)
            return
    # placeholder
    pix = QPixmap(int(t.width), int(t.height))
    pix.fill(QColor("#CCCCCC"))
    painter = QPainter(pix)
    painter.setPen(QPen(QColor("#888888"), 2))
    painter.drawLine(0, 0, int(t.width), int(t.height))
    painter.drawLine(int(t.width), 0, 0, int(t.height))
    painter.drawRect(1, 1, int(t.width) - 2, int(t.height) - 2)
    painter.end()
    item.setPixmap(pix)


# ---------------------------------------------------------------------------
# Canvas background item
# ---------------------------------------------------------------------------

class CanvasBackgroundItem(QGraphicsRectItem):
    def __init__(self, canvas: CanvasState):
        super().__init__(0, 0, canvas.width, canvas.height)
        self.setZValue(-1000)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self._canvas = canvas
        self.setPen(QPen(QColor("#AAAAAA"), 1))
        # Устанавливаем цвет сразу при создании
        self.setBrush(QBrush(QColor(canvas.background)))

    def paint(self, painter, option, widget=None):
        # Читаем актуальный цвет при каждом paint — background мог измениться
        self.setRect(0, 0, self._canvas.width, self._canvas.height)
        self.setBrush(QBrush(QColor(self._canvas.background)))
        super().paint(painter, option, widget)
        # Поверх — фоновое изображение если задано
        bg_img = getattr(self._canvas, "background_image", "")
        if bg_img:
            pix = QPixmap(bg_img)
            if not pix.isNull():
                scaled = pix.scaled(
                    int(self._canvas.width), int(self._canvas.height),
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap(self.rect().toRect(), scaled)


# ---------------------------------------------------------------------------
# Scene Renderer
# ---------------------------------------------------------------------------

class SceneRenderer:
    """
    Полная синхронизация DocumentState → QGraphicsScene.
    Вызывается при каждом document_changed.
    """

    def __init__(self, scene: QGraphicsScene,
                 registry: SceneItemRegistry,
                 store: "EditorStore",
                 overlay: QGraphicsItem | None = None):
        self._scene    = scene
        self._registry = registry
        self._store    = store
        self._overlay  = overlay        # ← храним ссылку, не удаляем
        self._bg_item: CanvasBackgroundItem | None = None

    def full_sync(self):
        """Полная пересборка сцены из DocumentState. Overlay не трогаем."""
        canvas = self._store.active_canvas

        for item in list(self._scene.items()):
            if self._overlay is not None and item is self._overlay:
                continue
            self._scene.removeItem(item)
        self._registry.clear()
        self._bg_item = None

        if canvas is None:
            return

        self._bg_item = CanvasBackgroundItem(canvas)
        self._scene.addItem(self._bg_item)

        # Z-order берётся из obj.z_index — пересчитывается деревом элементов
        for obj_id in canvas.all_ids_ordered():
            obj = canvas.objects.get(obj_id)
            if obj:
                self._create_item(obj, obj.z_index)

        if self._overlay is not None:
            self._overlay.setZValue(9999)

        self._sync_selection()

    def _create_item(self, obj: ObjectState, z_index: int = 0) -> QGraphicsItem | None:
        item = self._make_item(obj)
        if item is None:
            return None

        item.setFlag(QGraphicsItem.ItemIsSelectable, not obj.locked)
        item.setFlag(QGraphicsItem.ItemIsMovable, not obj.locked)
        item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        item.setVisible(obj.visible)
        item.setZValue(z_index)

        self._scene.addItem(item)
        self._registry.register(obj.id, item)
        return item

    def _make_item(self, obj: ObjectState) -> QGraphicsItem | None:
        if obj.type == ObjectType.RECT:
            item = QGraphicsRectItem()
            _apply_style_rect(item, obj)
            _apply_transform(item, obj)
            return item

        elif obj.type == ObjectType.ELLIPSE:
            item = QGraphicsEllipseItem()
            _apply_style_ellipse(item, obj)
            _apply_transform(item, obj)
            return item

        elif obj.type == ObjectType.TEXT:
            item = QGraphicsTextItem()
            _apply_style_text(item, obj)
            _apply_transform(item, obj)
            return item

        elif obj.type == ObjectType.IMAGE:
            item = QGraphicsPixmapItem()
            _apply_style_image(item, obj)
            _apply_transform(item, obj)
            return item

        elif obj.type == ObjectType.GROUP:
            # Группа — прозрачный контейнер
            item = QGraphicsRectItem()
            t = obj.transform
            item.setRect(0, 0, max(t.width, 1), max(t.height, 1))
            item.setBrush(QBrush(Qt.transparent))
            item.setPen(QPen(QColor("#888888"), 1, Qt.DashLine))
            _apply_transform(item, obj)
            return item

        return None

    def _sync_selection(self):
        """Подсвечиваем выбранные объекты."""
        selected = set(self._store.selection.selected_ids)
        for obj_id, item in self._registry._id_to_item.items():
            # Qt selection управляем через флаги
            item.setSelected(obj_id in selected)
