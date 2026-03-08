"""Сервис экспорта в PNG."""

from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtCore import QRectF

from ..models import Canvas


def export_to_png(
    scene: QGraphicsScene,
    canvas: Canvas,
    file_path: str,
    clear_selection: bool = True,
) -> bool:
    """Экспортирует сцену в PNG файл.

    Args:
        scene: QGraphicsScene для экспорта
        canvas: Канвас с настройками размера и фона
        file_path: Путь для сохранения файла
        clear_selection: Снимать ли выделение перед экспортом

    Returns:
        True если экспорт успешен, False иначе
    """
    if not scene or not canvas:
        return False

    # Снимаем выделение для чистого рендера
    if clear_selection:
        scene.clearSelection()

    # Устанавливаем размер сцены равным размеру канваса
    scene.setSceneRect(0, 0, canvas.width, canvas.height)

    # Создаём pixmap нужного размера
    pixmap = QPixmap(int(canvas.width), int(canvas.height))
    pixmap.fill(QColor(canvas.background_color))

    # Рисуем сцену на pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter)
    painter.end()

    # Сохраняем в файл
    return pixmap.save(file_path)


def export_scene_to_pixmap(
    scene: QGraphicsScene,
    canvas: Canvas,
    clear_selection: bool = True,
) -> QPixmap | None:
    """Экспортирует сцену в QPixmap.

    Args:
        scene: QGraphicsScene для экспорта
        canvas: Канвас с настройками размера и фона
        clear_selection: Снимать ли выделение перед экспортом

    Returns:
        QPixmap или None если ошибка
    """
    if not scene or not canvas:
        return None

    # Снимаем выделение для чистого рендера
    if clear_selection:
        scene.clearSelection()

    # Устанавливаем размер сцены равным размеру канваса
    scene.setSceneRect(0, 0, canvas.width, canvas.height)

    # Создаём pixmap нужного размера
    pixmap = QPixmap(int(canvas.width), int(canvas.height))
    pixmap.fill(QColor(canvas.background_color))

    # Рисуем сцену на pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter)
    painter.end()

    return pixmap
