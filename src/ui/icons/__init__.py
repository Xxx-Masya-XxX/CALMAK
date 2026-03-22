"""
ui/icons/__init__.py — загрузчик иконок.

Цвет иконок берётся из C.TEXT (ui.constants) который обновляется через
C.set_theme() при каждой смене темы. При вызове get_icon()/get_pixmap()
цвет читается из C.TEXT — всегда актуальный.

Кеш сбрасывается автоматически через ThemeManager.theme_changed.
Если SVG не найден — рисует fallback символ из _FALLBACKS.
"""
from __future__ import annotations
import os

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer

_ICONS_DIR = os.path.dirname(__file__)

# Fallback символы если SVG не найден
_FALLBACKS: dict[str, str] = {
    "rect":         "▭",
    "ellipse":      "◯",
    "triangle":     "△",
    "text":         "T",
    "image":        "🖼",
    "bezier":       "〜",
    "move":         "✥",
    "rotate":       "↻",
    "scale":        "⤡",
    "forward":      "⬆",
    "backward":     "⬇",
    "new":          "🆕",
    "open":         "📂",
    "save":         "💾",
    "export":       "📤",
    "undo":         "↩",
    "redo":         "↪",
    "settings":     "⚙",
    "add_canvas":   "➕",
    "canvas_node":  "🎨",
    "group":        "📁",
    "visible":      "👁",
    "hidden":       "🚫",
    "locked":       "🔒",
}

# Кеш: (name, size, color_hex) → QPixmap
_CACHE: dict[tuple, QPixmap] = {}


def _theme_color() -> QColor:
    """
    Возвращает цвет текста из активной темы (C.TEXT).
    C.set_theme() вызывается при каждой смене темы и обновляет C.TEXT.
    Это гарантирует что цвет всегда соответствует текущей теме,
    независимо от палитры Qt.
    """
    try:
        from ui.constants import C
        return QColor(C.TEXT)   # QColor из C.TEXT обновляется через set_theme()
    except Exception:
        return QColor("#CCCCDD")


def clear_cache() -> None:
    """Сбросить кеш. Вызывается автоматически при смене темы."""
    _CACHE.clear()


def _render_svg(svg_path: str, size: int, color: QColor) -> QPixmap:
    """Загружает SVG, подставляет color вместо currentColor, рендерит в QPixmap."""
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_data = f.read()
    svg_data = svg_data.replace("currentColor", color.name())
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    renderer.render(p)
    p.end()
    return pixmap


def _fallback_pixmap(text: str, size: int, color: QColor) -> QPixmap:
    """Рисует fallback символ/эмодзи на прозрачном фоне."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setPen(color)
    font = QFont()
    font.setPixelSize(max(8, int(size * 0.72)))
    p.setFont(font)
    p.drawText(pixmap.rect(), Qt.AlignCenter, text)
    p.end()
    return pixmap


def _get_pixmap_raw(name: str, size: int, color: QColor) -> QPixmap:
    """Внутренняя функция — рендерит с заданным цветом, использует кеш."""
    key = (name, size, color.name())
    if key in _CACHE:
        return _CACHE[key]

    svg_path = os.path.join(_ICONS_DIR, f"{name}.svg")
    if os.path.isfile(svg_path):
        try:
            pix = _render_svg(svg_path, size, color)
            _CACHE[key] = pix
            return pix
        except Exception:
            pass

    pix = _fallback_pixmap(_FALLBACKS.get(name, name[:1].upper()), size, color)
    _CACHE[key] = pix
    return pix


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_icon(name: str, size: int = 20) -> QIcon:
    """
    Возвращает QIcon с цветом текущей темы (C.TEXT).
    Кешируется. При смене темы вызывайте clear_cache().
    """
    return QIcon(_get_pixmap_raw(name, size, _theme_color()))


def get_pixmap(name: str, size: int = 16,
               color: QColor | None = None) -> QPixmap:
    """
    Возвращает QPixmap.
    color — явный цвет (для иконок типов объектов в дереве).
    Если color=None — используется цвет текущей темы C.TEXT.
    """
    return _get_pixmap_raw(name, size, color if color is not None else _theme_color())


def setup_theme_auto_refresh() -> None:
    """
    Подписывает clear_cache на theme_manager.theme_changed.
    Вызывать один раз при старте приложения.
    После смены темы кеш очищается автоматически, следующий get_icon()
    рендерит с новым цветом из C.TEXT.
    """
    try:
        from ui.theme import theme_manager
        # Disconnect old if any
        try:
            theme_manager.theme_changed.disconnect(_on_theme_changed)
        except (RuntimeError, TypeError):
            pass  # not connected yet — fine
        theme_manager.theme_changed.connect(_on_theme_changed)
    except Exception:
        pass


def _on_theme_changed(name: str, theme_dict: dict) -> None:
    """Слот — очищает кеш при смене темы."""
    clear_cache()
