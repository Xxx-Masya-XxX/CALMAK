"""
ui/theme.py — единая система тем приложения.

Содержит:
  • THEMES        — словарь всех доступных тем
  • ThemeManager  — синглтон, хранит активную тему и рассылает сигнал
  • build_stylesheet(name) — генерирует QSS для QApplication
  • Темозависимые константы синхронизируются с ui.constants.C при смене темы
"""
from __future__ import annotations
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

THEMES: dict[str, dict] = {
    "Dark": {
        "bg":        "#1A1A2A",
        "surface":   "#252535",
        "surface2":  "#2A2A3E",
        "border":    "#3A3A4A",
        "accent":    "#4A90E2",
        "accent2":   "#3A5A9A",
        "text":      "#CCCCDD",
        "text_dim":  "#888899",
        "scene_bg":  "#2D2D3A",
    },
    "Light": {
        "bg":        "#F0F0F5",
        "surface":   "#FFFFFF",
        "surface2":  "#E8E8F0",
        "border":    "#C8C8D8",
        "accent":    "#2060C0",
        "accent2":   "#1040A0",
        "text":      "#111122",
        "text_dim":  "#666677",
        "scene_bg":  "#D8D8E8",
    },
    "Midnight": {
        "bg":        "#0D0D1A",
        "surface":   "#13131F",
        "surface2":  "#1A1A2A",
        "border":    "#2A2A3A",
        "accent":    "#7A4AE2",
        "accent2":   "#5A2AC2",
        "text":      "#DDDDFF",
        "text_dim":  "#7777AA",
        "scene_bg":  "#181828",
    },
    "Warm": {
        "bg":        "#1F1A14",
        "surface":   "#2A231A",
        "surface2":  "#352B20",
        "border":    "#4A3F30",
        "accent":    "#E2904A",
        "accent2":   "#C27030",
        "text":      "#EEE0CC",
        "text_dim":  "#998877",
        "scene_bg":  "#252018",
    },
}


# ---------------------------------------------------------------------------
# Stylesheet generator
# ---------------------------------------------------------------------------

def build_stylesheet(theme_name: str) -> str:
    """Генерирует полный QSS для QApplication на основе выбранной темы."""
    t = THEMES.get(theme_name, THEMES["Dark"])
    return f"""
    /* ── Base ── */
    QMainWindow, QWidget {{
        background: {t['bg']}; color: {t['text']};
    }}

    /* ── Menu bar ── */
    QMenuBar {{
        background: {t['surface']}; color: {t['text']};
        border-bottom: 1px solid {t['border']};
        padding: 2px; font-size: 12px;
    }}
    QMenuBar::item {{ padding: 4px 8px; border-radius: 3px; }}
    QMenuBar::item:selected {{ background: {t['accent2']}; }}

    /* ── Menus ── */
    QMenu {{
        background: {t['surface']}; color: {t['text']};
        border: 1px solid {t['border']}; font-size: 12px; padding: 4px;
    }}
    QMenu::item {{ padding: 5px 20px 5px 12px; border-radius: 3px; }}
    QMenu::item:selected {{ background: {t['accent2']}; }}
    QMenu::separator {{
        height: 1px; background: {t['border']}; margin: 3px 6px;
    }}

    /* ── Toolbars ── */
    QToolBar {{
        background: {t['surface']};
        border: 1px solid {t['border']};
        spacing: 2px; padding: 2px 4px;
    }}
    QToolBar::handle {{
        background: {t['border']}; width: 6px;
        border-radius: 2px; margin: 2px;
    }}
    QToolBar::separator {{
        background: {t['border']}; width: 1px; margin: 4px 2px;
    }}

    /* ── Dock widgets ── */
    QDockWidget {{
        color: {t['text']};
        font-size: 11px;
    }}
    QDockWidget::title {{
        background: {t['surface']};
        padding: 4px 8px;
        color: {t['text_dim']};
        border-bottom: 1px solid {t['border']};
    }}
    QDockWidget::close-button, QDockWidget::float-button {{
        background: transparent;
        border: none;
        padding: 2px;
    }}
    QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
        background: {t['accent2']};
        border-radius: 3px;
    }}

    /* ── Status bar ── */
    QStatusBar {{
        background: {t['surface']};
        color: {t['text_dim']};
        border-top: 1px solid {t['border']};
        font-size: 11px;
    }}
    QStatusBar::item {{ border: none; }}

    /* ── Splitters ── */
    QSplitter::handle {{ background: {t['border']}; }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical   {{ height: 1px; }}

    /* ── Scroll bars ── */
    QScrollBar:vertical {{
        background: {t['bg']}; width: 8px; border: none; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']}; border-radius: 4px; min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t['accent2']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: {t['bg']}; height: 8px; border: none; margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['border']}; border-radius: 4px; min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t['accent2']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Buttons ── */
    QPushButton {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 4px;
        padding: 4px 10px; font-size: 11px;
    }}
    QPushButton:hover  {{ background: {t['accent2']}; border-color: {t['accent']}; }}
    QPushButton:pressed {{ background: {t['accent']}; }}
    QPushButton:checked {{
        background: {t['accent2']}; border: 1px solid {t['accent']};
    }}
    QPushButton:disabled {{ color: {t['text_dim']}; border-color: {t['border']}; }}
    QPushButton:flat {{ background: transparent; border: none; }}
    QPushButton:flat:hover {{ background: {t['surface2']}; border-radius: 4px; }}

    /* ── Inputs ── */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 3px;
        padding: 3px 6px; font-size: 11px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QComboBox:focus, QTextEdit:focus {{
        border-color: {t['accent']};
    }}
    QLineEdit:read-only {{ color: {t['text_dim']}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox::down-arrow {{
        width: 8px; height: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {t['surface']}; color: {t['text']};
        border: 1px solid {t['border']}; selection-background-color: {t['accent2']};
    }}

    /* ── Tables ── */
    QTableWidget {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']};
        gridline-color: {t['border']}; font-size: 11px;
    }}
    QTableWidget::item:selected {{ background: {t['accent2']}; }}
    QHeaderView::section {{
        background: {t['surface']}; color: {t['text_dim']};
        border: 1px solid {t['border']}; padding: 4px; font-size: 10px;
    }}

    /* ── Tabs ── */
    QTabWidget::pane {{
        border: 1px solid {t['border']}; background: {t['bg']};
    }}
    QTabBar::tab {{
        background: {t['surface']}; color: {t['text_dim']};
        padding: 5px 14px; border: none; font-size: 11px;
    }}
    QTabBar::tab:selected {{
        background: {t['bg']}; color: {t['text']};
        border-bottom: 2px solid {t['accent']};
    }}
    QTabBar::tab:hover:!selected {{ color: {t['text']}; }}

    /* ── Group boxes ── */
    QGroupBox {{
        color: {t['text_dim']}; border: 1px solid {t['border']};
        border-radius: 4px; margin-top: 10px;
        font-size: 11px; padding: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 8px; padding: 0 4px;
        color: {t['text_dim']};
    }}

    /* ── Checkboxes ── */
    QCheckBox {{ color: {t['text']}; font-size: 11px; spacing: 6px; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {t['border']}; border-radius: 3px;
        background: {t['surface2']};
    }}
    QCheckBox::indicator:checked {{
        background: {t['accent']}; border-color: {t['accent']};
    }}
    QCheckBox::indicator:hover {{ border-color: {t['accent']}; }}

    /* ── Key sequence edit ── */
    QKeySequenceEdit {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 3px;
        padding: 2px 6px; font-size: 11px;
    }}
    """


# ---------------------------------------------------------------------------
# ThemeManager — синглтон с сигналом
# ---------------------------------------------------------------------------

class ThemeManager(QObject):
    """
    Синглтон. Хранит имя активной темы и рассылает `theme_changed`
    когда тема меняется. Все виджеты которым нужно реагировать на смену
    темы (например SceneView для перекраски фона) подписываются на этот сигнал.
    """
    theme_changed = Signal(str, dict)   # (name, theme_dict)

    _instance: "ThemeManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._name: str  = "Dark"
        self._initialized = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def current(self) -> dict:
        return THEMES.get(self._name, THEMES["Dark"])

    def apply(self, theme_name: str):
        """
        Применяет тему:
          1. Обновляет QApplication stylesheet
          2. Обновляет C (QColor константы)
          3. Эмитит theme_changed для подписчиков (SceneView и др.)
        """
        if theme_name not in THEMES:
            return
        self._name = theme_name
        t = THEMES[theme_name]

        # Update QColor constants
        from ui.constants import C
        C.set_theme(t)

        # Update QApplication stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(theme_name))

        # Notify all subscribers
        self.theme_changed.emit(theme_name, t)

    def get(self, key: str, fallback: str = "#888888") -> str:
        """Получить hex-цвет из активной темы."""
        return self.current.get(key, fallback)


# Module-level singleton
theme_manager = ThemeManager()
