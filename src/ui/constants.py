"""
ui/constants.py — единый источник констант для всего UI.

Структура:
  • ObjectColors  — цвета типов объектов
  • ObjectIcons   — иконки типов объектов
  • LayerTree     — размеры строк дерева слоёв
  • Colors        — статические цвета (не зависят от темы)
  • SceneColors   — цвета сцены (берутся из активной темы)

Использование:
    from ui.constants import C, ICONS, LAYER

    # Статический цвет:
    pen = QPen(C.ACCENT)

    # Цвет из активной темы:
    bg = QColor(C.theme("bg"))
"""
from __future__ import annotations
from PySide6.QtGui import QColor
from domain.models import ObjectType


# ---------------------------------------------------------------------------
# Object type → icon / color
# ---------------------------------------------------------------------------

class ICONS:
    """Иконки типов объектов."""
    MAP = {
        ObjectType.RECT:    "▭",
        ObjectType.ELLIPSE: "◯",
        ObjectType.TEXT:    "T",
        ObjectType.IMAGE:   "🖼",
        ObjectType.GROUP:   "📁",
        ObjectType.BEZIER:  "〜",
    }
    CANVAS = "🎨"
    CANVAS_ACTIVE = "▶"

    @classmethod
    def get(cls, obj_type: ObjectType, fallback: str = "?") -> str:
        return cls.MAP.get(obj_type, fallback)


class OBJECT_COLORS:
    """Цвета типов объектов (QColor)."""
    MAP = {
        ObjectType.RECT:    "#4A90E2",
        ObjectType.ELLIPSE: "#E2604A",
        ObjectType.TEXT:    "#4AE27A",
        ObjectType.IMAGE:   "#E2A84A",
        ObjectType.GROUP:   "#A84AE2",
        ObjectType.BEZIER:  "#E2C44A",
    }
    FALLBACK = "#CCCCCC"

    @classmethod
    def get(cls, obj_type: ObjectType) -> QColor:
        return QColor(cls.MAP.get(obj_type, cls.FALLBACK))

    @classmethod
    def get_hex(cls, obj_type: ObjectType) -> str:
        return cls.MAP.get(obj_type, cls.FALLBACK)


# ---------------------------------------------------------------------------
# Layer tree dimensions
# ---------------------------------------------------------------------------

class LAYER:
    """Размеры и отступы строк дерева слоёв."""
    ITEM_H    = 28    # высота строки px
    INDENT    = 20    # отступ на уровень вложенности px
    ICON_W    = 22    # ширина колонки иконки px
    TOGGLE_W  = 14    # ширина зоны expand/collapse px
    PAD_LEFT  = 4     # левый отступ px


# ---------------------------------------------------------------------------
# Static UI colors (theme-independent)
# ---------------------------------------------------------------------------

class C:
    """
    Статические цвета интерфейса.
    Тема-зависимые цвета получайте через C.theme(key).
    """

    # ---- Accent / selection ----
    ACCENT          = QColor("#4A90E2")
    ACCENT_DIM      = QColor("#3A5A9A")

    # ---- Selection ----
    SEL_BG          = QColor("#3A4A6A")
    SEL_FG          = QColor("#FFFFFF")
    HOVER           = QColor(255, 255, 255, 18)

    # ---- Drop indicators ----
    DROP_LINE       = QColor("#4A9EFF")
    DROP_RECT       = QColor("#4A9EFF")

    # ---- Overlay / selection box ----
    SELECTION_BOX   = QColor("#4A9EFF")

    # ---- Scene background ----
    SCENE_BG        = QColor("#2D2D3A")
    CANVAS_BORDER   = QColor("#AAAAAA")

    # ---- Text ----
    TEXT            = QColor("#CCCCDD")
    TEXT_DIM        = QColor("#888899")
    TEXT_MUTED      = QColor("#555566")
    TEXT_CANVAS     = QColor("#FFFFFF")
    TEXT_CANVAS_DIM = QColor("#AAAACC")

    # ---- Backgrounds ----
    BG              = QColor("#1A1A2A")
    SURFACE         = QColor("#252535")
    SURFACE2        = QColor("#2A2A3E")
    BORDER          = QColor("#3A3A4A")

    # ---- Object/canvas tree ----
    TREE_BG         = QColor("#1E1E2E")
    TREE_ROW_SEP    = QColor("#2A2A3A")
    TREE_TOGGLE     = QColor("#888899")
    TREE_CANVAS_BG  = QColor("#252535")

    # ---- Render placeholders ----
    PLACEHOLDER_FILL   = QColor("#CCCCCC")
    PLACEHOLDER_STROKE = QColor("#888888")
    GROUP_STROKE       = QColor("#888888")

    # ---- Tools ----
    ROTATE_INDICATOR = QColor("#FF9900")
    SCALE_HANDLE_BG  = QColor("#FFFFFF")
    SCALE_HANDLE_FG  = QColor("#4A9EFF")

    # ---- Misc ----
    TRANSPARENT = QColor(0, 0, 0, 0)

    # -----------------------------------------------------------------------
    # Theme-aware access
    # -----------------------------------------------------------------------

    _current_theme: dict = {}

    @classmethod
    def set_theme(cls, theme_dict: dict):
        """Обновить текущую тему (вызывается при смене темы)."""
        cls._current_theme = theme_dict
        # Обновляем QColor-поля которые зависят от темы
        if theme_dict:
            cls.ACCENT       = QColor(theme_dict.get("accent",   "#4A90E2"))
            cls.ACCENT_DIM   = QColor(theme_dict.get("accent2",  "#3A5A9A"))
            cls.TEXT         = QColor(theme_dict.get("text",     "#CCCCDD"))
            cls.TEXT_DIM     = QColor(theme_dict.get("text_dim", "#888899"))
            cls.BG           = QColor(theme_dict.get("bg",       "#1A1A2A"))
            cls.SURFACE      = QColor(theme_dict.get("surface",  "#252535"))
            cls.SURFACE2     = QColor(theme_dict.get("surface2", "#2A2A3E"))
            cls.BORDER       = QColor(theme_dict.get("border",   "#3A3A4A"))
            cls.SCENE_BG     = QColor(theme_dict.get("scene_bg", "#2D2D3A"))
            cls.TREE_BG      = QColor(theme_dict.get("bg",       "#1E1E2E"))
            cls.SEL_BG       = QColor(theme_dict.get("accent2",  "#3A5A9A"))
            cls.TREE_CANVAS_BG = QColor(theme_dict.get("surface", "#252535"))

    @classmethod
    def theme(cls, key: str, fallback: str = "#888888") -> str:
        """Получить hex-цвет из активной темы по ключу."""
        return cls._current_theme.get(key, fallback)


# ---------------------------------------------------------------------------
# Default canvas settings
# ---------------------------------------------------------------------------

class CANVAS_DEFAULTS:
    BACKGROUND = "#FFFFFF"
    WIDTH      = 1920
    HEIGHT     = 1080


# ---------------------------------------------------------------------------
# Stylesheet snippets (reusable)
# ---------------------------------------------------------------------------

def menu_stylesheet() -> str:
    return f"""
        QMenu {{
            background: {C.theme('surface', '#252535')};
            color: {C.theme('text', '#CCCCDD')};
            border: 1px solid {C.theme('border', '#3A3A5A')};
            font-size: 12px; padding: 4px;
        }}
        QMenu::item {{
            padding: 5px 20px 5px 12px; border-radius: 3px;
        }}
        QMenu::item:selected {{
            background: {C.theme('accent2', '#3A4A6A')};
        }}
        QMenu::separator {{
            height: 1px;
            background: {C.theme('border', '#3A3A5A')};
            margin: 3px 6px;
        }}
    """
