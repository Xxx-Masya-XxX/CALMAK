# Canvas Editor

Графический редактор на PySide6 с чистой state-driven архитектурой.

## Быстрый старт

```bash
pip install PySide6
python src/main.py
```

## Горячие клавиши

| Действие          | Клавиши            |
|-------------------|--------------------|
| Новый документ    | Ctrl+N             |
| Открыть           | Ctrl+O             |
| Сохранить         | Ctrl+S             |
| Экспорт PNG       | Ctrl+E             |
| Undo              | Ctrl+Z             |
| Redo              | Ctrl+Shift+Z       |
| Дублировать       | Ctrl+D             |
| Удалить           | Delete             |
| Выбрать всё       | Ctrl+A             |
| Добавить Rect     | R                  |
| Добавить Ellipse  | E                  |
| Добавить Text     | T                  |
| Добавить Image    | I                  |
| Bring Forward     | Ctrl+]             |
| Send Backward     | Ctrl+[             |
| Zoom In/Out       | Ctrl+= / Ctrl+-    |
| Fit canvas        | Ctrl+0             |
| Стрелки (move)    | ←↑→↓ (×10 с Shift) |
| Pan               | Middle mouse / Alt+drag |
| Zoom              | Ctrl+Scroll        |
| Rubber band       | Drag по фону       |
| Multi-select      | Ctrl+Click         |
| Редактировать текст | Double-click     |

## Архитектура

```
┌──────────────────────────────────────────┐
│                    UI                     │
│  SceneView  │  TreePanel  │ PropsPanel   │
│      ↓ intent signals                     │
├──────────────────────────────────────────┤
│            EditorController               │
│      создаёт команды → пушит в Store     │
├──────────────────────────────────────────┤
│   Commands (undo/redo)  │  EditorStore   │
│   AddObject, Move,      │  ↓ state sigs  │
│   Resize, Delete...     │  → все панели  │
├──────────────────────────────────────────┤
│              Domain Models                │
│   DocumentState → CanvasState            │
│   ObjectState (Rect/Ellipse/Text/Image)  │
│   Transform, StyleState, Payloads        │
└──────────────────────────────────────────┘
```

### Принципы

- **Один источник правды** — `DocumentState` + `SelectionState`
- **UI не меняет состояние напрямую** — только через `EditorController`
- **Все изменения — команды** — поэтому Undo/Redo работает везде
- **Панели не знают друг о друге** — подписываются только на `EditorStore`
- **SceneView** — только рендер + передача событий, не логика

### Поток данных

```
User action
    → UI widget emits intent signal
    → EditorController.some_method()
    → Command created & pushed to history
    → Command.execute(DocumentState)
    → EditorStore.document_changed.emit()
    → All panels update independently
```

## Структура проекта

```
src/
├── main.py                      # Точка входа
├── domain/
│   └── models.py                # DocumentState, CanvasState, ObjectState...
├── state/
│   └── editor_store.py          # Единый Store с Qt-сигналами
├── commands/
│   └── commands.py              # Add/Move/Resize/Delete/Reparent/Duplicate...
├── controllers/
│   └── editor_controller.py     # Все мутации идут сюда
├── rendering/
│   └── scene_renderer.py        # DocumentState → QGraphicsScene
├── serialization/
│   └── serializer.py            # Save/Load .cep (JSON)
├── export/
│   └── exporter.py              # PNG/JPEG/BMP export
└── ui/
    ├── main_window.py           # Главное окно
    ├── scene/
    │   └── scene_view.py        # Интерактивный холст
    ├── panels/
    │   ├── element_tree_panel.py  # Дерево слоёв
    │   └── properties_panel.py    # Панель свойств
    └── dialogs/
        └── text_dialog.py         # Редактор текста
```

## Формат проекта (.cep)

JSON-файл, содержащий все канвасы, объекты, трансформации и стили.

```json
{
  "version": "1.0",
  "active_canvas_id": "abc123",
  "canvases": {
    "abc123": {
      "id": "abc123",
      "name": "Canvas 1",
      "width": 1920,
      "height": 1080,
      "background": "#1E1E2E",
      "root_ids": ["obj1", "obj2"],
      "objects": { ... }
    }
  }
}
```

## Расширение (следующие этапы по документации)

- **Этап 2**: Tool system (SelectTool, MoveTool, RotateTool, ScaleTool), ActionRegistry
- **Этап 3**: Asset system, группировка объектов, множественные канвасы
- **Этап 4**: ScriptEngine + ScriptAPI, параметрические шаблоны, placeholders
- **Этап 5**: PDF/SVG export, batch processing
