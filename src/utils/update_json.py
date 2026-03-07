import json
import os

def update_json(file, updates):
    data = {}

    # если файл существует — читаем
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    # обновляем ключи
    data.update(updates)

    # записываем обратно
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)