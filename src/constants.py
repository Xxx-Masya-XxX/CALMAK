"""Константы приложения."""

# Версия приложения
APP_VERSION = "0.1.0"
APP_NAME = "CALMAK"
APP_TITLE = f"{APP_NAME} - Редактор"

# Размеры
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 800

DEFAULT_CANVAS_WIDTH = 800
DEFAULT_CANVAS_HEIGHT = 600

# Панели
MIN_ELEMENTS_PANEL_WIDTH = 200
MAX_ELEMENTS_PANEL_WIDTH = 400
MIN_PROPERTIES_PANEL_WIDTH = 250
MAX_PROPERTIES_PANEL_WIDTH = 400

# Зум
ZOOM_IN_FACTOR = 1.1
ZOOM_OUT_FACTOR = 1 / 1.1
MIN_ZOOM = 0.1
MAX_ZOOM = 5.0

# Цвета темы
LIGHT_THEME_BG = "#ffffff"
DARK_THEME_BG = "#2b2b2b"

# Типы объектов
OBJECT_TYPE_RECT = "rect"
OBJECT_TYPE_ELLIPSE = "ellipse"
OBJECT_TYPE_TRIANGLE = "triangle"
OBJECT_TYPE_TEXT = "text"
OBJECT_TYPE_IMAGE = "image"

# Роли для текстовых объектов (для CalendarNode)
ROLE_DAY_NUMBER = "day_number"
ROLE_SPECIAL_TEXT = "special_text"
ROLE_WEEKDAY_NAME = "weekday_name"
ROLE_WEEK_NUMBER = "week_number"
ROLE_MONTH_NAME = "month_name"
