"""Сервис сохранения проекта."""

import json
from pathlib import Path
from typing import Any

from ..models import Canvas, BaseObject
from ..controllers import SceneController


def serialize_project(controller: SceneController) -> dict[str, Any]:
    """Сериализует проект в словарь.

    Args:
        controller: SceneController с данными проекта

    Returns:
        Словарь с данными проекта
    """
    project_data = {
        "version": "1.0",
        "canvases": [],
        "active_canvas_id": controller.get_active_canvas_id(),
    }

    for canvas in controller.get_all_canvases():
        canvas_data = canvas.to_dict()
        canvas_data["objects"] = []

        for obj in controller.get_objects(canvas.id):
            canvas_data["objects"].append(obj.to_dict())

        project_data["canvases"].append(canvas_data)

    return project_data


def save_project(controller: SceneController, file_path: str | Path) -> bool:
    """Сохраняет проект в файл.

    Args:
        controller: SceneController с данными проекта
        file_path: Путь для сохранения файла

    Returns:
        True если сохранение успешно, False иначе
    """
    try:
        project_data = serialize_project(controller)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        return True
    except (IOError, OSError, TypeError):
        return False


def save_project_auto(controller: SceneController, project_name: str = "project") -> str | None:
    """Автоматически сохраняет проект в директорию data.

    Args:
        controller: SceneController с данными проекта
        project_name: Имя проекта (без расширения)

    Returns:
        Путь к сохранённому файлу или None если ошибка
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    file_path = data_dir / f"{project_name}.json"

    if save_project(controller, file_path):
        return str(file_path)
    return None
