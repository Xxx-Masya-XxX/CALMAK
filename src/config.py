"""Конфигурация приложения."""

import json
import os
from pathlib import Path


# Пути к файлам конфигурации
SETTINGS_FILE = Path("settings.json")
TEMPLATE_FILE = Path("template.json")

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "style": "Fusion",
    "theme": "dark",
}

DEFAULT_WINDOW_SIZE = {
    "width": 1200,
    "height": 800,
}

DEFAULT_CANVAS_SIZE = {
    "width": 800,
    "height": 600,
}


def load_settings() -> dict:
    """Загружает настройки из файла."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Сохраняет настройки в файл."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


def get_setting(key: str, default=None):
    """Получает настройку по ключу."""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value) -> None:
    """Устанавливает настройку и сохраняет."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
