# CALMAK

Редактор каллажей - приложение для создания композиций на основе PySide6.

## Структура проекта

```
CALMAK
│
├── src
│   ├── core
│   │   ├── __init__.py
│   │   └── project_manager.py
│   │
│   ├── models
│   │   ├── __init__.py
│   │   ├── canvas.py
│   │   └── objects
│   │       ├── __init__.py
│   │       ├── base_object.py
│   │       ├── text_object.py
│   │       ├── image_object.py
│   │       └── shape_object.py
│   │
│   ├── controllers
│   │   ├── __init__.py
│   │   └── scene_controller.py
│   │
│   ├── services
│   │   ├── __init__.py
│   │   ├── export_png.py
│   │   ├── save_project.py
│   │   └── load_project.py
│   │
│   ├── ui
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   │
│   │   ├── preview
│   │   │   ├── __init__.py
│   │   │   ├── preview_frame.py
│   │   │   ├── scene.py
│   │   │   └── items
│   │   │       ├── __init__.py
│   │   │       ├── text_item.py
│   │   │       ├── image_item.py
│   │   │       └── shape_item.py
│   │   │
│   │   ├── panels
│   │   │   ├── __init__.py
│   │   │   ├── elements_panel.py
│   │   │   └── properties_panel.py
│   │   │
│   │   └── dialogs
│   │       ├── __init__.py
│   │       ├── settings_dialog.py
│   │       └── text_editor_dialog.py
│   │
│   ├── utils
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── update_json.py
│   ├── __init__.py
│   ├── config.py
│   └── constants.py
│
├── assets
├── tools
├── tests
│
├── main.py
├── pyproject.toml
└── README.md
```

## Установка

```bash
# Установка зависимостей
uv install

# Запуск приложения
uv run python main.py
```

## Зависимости

- Python >= 3.14
- PySide6 >= 6.10.2
- Pillow >= 12.1.1

## Возможности

- Создание и управление канвасами
- Добавление объектов (фигуры, текст, изображения)
- Иерархия объектов (родитель-потомок)
- Настройка свойств объектов
- Экспорт в PNG
- Светлая и тёмная темы
- Поддержка зума

## Лицензия

MIT
