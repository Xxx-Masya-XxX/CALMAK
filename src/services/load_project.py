"""Сервис загрузки проекта."""

import json
from pathlib import Path
from typing import Any

from ..models import Canvas, BaseObject, TextObject, ImageObject, ShapeObject
from ..controllers import SceneController


def deserialize_object(data: dict[str, Any]) -> BaseObject:
    """Десериализует объект из словаря.

    Args:
        data: Словарь с данными объекта

    Returns:
        Экземпляр BaseObject или наследника
    """
    # Определяем тип объекта по наличию специфичных полей
    if "text" in data or data.get("name", "").startswith("Text"):
        return TextObject.from_dict(data)
    elif "image_path" in data and data.get("name", "").startswith("Image"):
        return ImageObject.from_dict(data)
    elif data.get("shape_type") in ("rect", "ellipse", "triangle"):
        return ShapeObject.from_dict(data)
    else:
        return BaseObject.from_dict(data)


def load_project(controller: SceneController, file_path: str | Path) -> bool:
    """Загружает проект из файла.

    Args:
        controller: SceneController для загрузки данных
        file_path: Путь к файлу проекта

    Returns:
        True если загрузка успешна, False иначе
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)

        # Очищаем текущий проект
        _clear_project(controller)

        # Загружаем канвасы
        canvases_data = project_data.get("canvases", [])
        canvas_id_map = {}  # old_id -> new_id

        for canvas_data in canvases_data:
            canvas = Canvas.from_dict(canvas_data)
            controller.add_canvas(canvas)
            canvas_id_map[canvas_data["id"]] = canvas.id

        # Загружаем объекты
        for canvas_data in canvases_data:
            new_canvas_id = canvas_id_map.get(canvas_data["id"])
            if not new_canvas_id:
                continue

            objects_data = canvas_data.get("objects", [])
            old_id_to_new_id = {}  # old_obj_id -> new_obj_id

            # Сначала создаём все объекты
            for obj_data in objects_data:
                obj = deserialize_object(obj_data)
                # Временно сохраняем старый ID для связи с родителем
                old_id_to_new_id[obj_data["id"]] = obj.id
                controller.add_object(new_canvas_id, obj)

            # Устанавливаем связи родителей
            for obj_data, obj in zip(objects_data, controller.get_objects(new_canvas_id)):
                old_parent_id = obj_data.get("parent_id")
                if old_parent_id:
                    new_parent_id = old_id_to_new_id.get(old_parent_id)
                    if new_parent_id:
                        # Находим объект родителя
                        parent_obj = None
                        for o in controller.get_objects(new_canvas_id):
                            if o.id == new_parent_id:
                                parent_obj = o
                                break
                        if parent_obj:
                            controller.set_parent(new_canvas_id, obj, parent_obj)

        # Устанавливаем активный канвас
        active_canvas_old_id = project_data.get("active_canvas_id")
        if active_canvas_old_id:
            new_active_id = canvas_id_map.get(active_canvas_old_id)
            if new_active_id:
                controller.set_active_canvas(new_active_id)

        return True
    except (IOError, OSError, json.JSONDecodeError, KeyError):
        return False


def _clear_project(controller: SceneController):
    """Очищает проект."""
    for canvas in controller.get_all_canvases():
        controller.remove_canvas(canvas.id)
