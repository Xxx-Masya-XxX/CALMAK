# Рефакторинг графических элементов

## Новая архитектура

```
BaseGraphicsItem  (base_item.py)
├── Вся логика: move, resize (8 ручек), selection, сигналы
├── _paint_content(painter, rect) — пустой метод для переопределения
└── _paint_selection(painter, rect) — рамка выделения с квадратиками

ShapeGraphicsItem  (shape_item.py)
└── Только _paint_content() — rect/ellipse/triangle + изображение

ImageGraphicsItem  (image_item.py)
└── Только _paint_content() — изображение с масштабированием

TextGraphicsItem   (text_item.py)
└── Только _paint_content() — текст строго внутри content_rect с padding
    └── update_font() / update_colors() — публичные методы обновления
```

---

## Файлы

| Файл | Действие |
|------|----------|
| `src/ui/preview/items/base_item.py`    | ЗАМЕНИТЬ |
| `src/ui/preview/items/shape_item.py`   | ЗАМЕНИТЬ |
| `src/ui/preview/items/image_item.py`   | ЗАМЕНИТЬ |
| `src/ui/preview/items/text_item.py`    | ЗАМЕНИТЬ |
| `src/ui/preview/items/stroke_renderer.py` | ЗАМЕНИТЬ |
| `src/ui/preview/items/__init__.py`     | ЗАМЕНИТЬ |

---

## Изменения в существующих файлах

### scene.py — добавить 2 сигнала

```python
# В классе PreviewScene:
object_selected          = Signal(BaseObject)
object_changed           = Signal(BaseObject)
object_moved             = Signal(BaseObject)
object_resized           = Signal(BaseObject)          # ← добавить
object_geometry_changed  = Signal(BaseObject)          # ← добавить
```

### scene.py — update_object

```python
def update_object(self, obj: BaseObject):
    if obj not in self._object_items:
        return
    item = self._object_items[obj]
    item.sync_from_model()
    if hasattr(item, 'update_font'):
        item.update_font()
```

### preview_frame.py — добавить сигналы

```python
object_resized          = Signal(BaseObject)
object_geometry_changed = Signal(BaseObject)
```

### preview_frame.py — в add_canvas()

```python
scene.object_resized.connect(self.object_resized.emit)
scene.object_geometry_changed.connect(self.object_geometry_changed.emit)
```

### main_window.py — в _connect_signals()

```python
self.preview_frame.object_resized.connect(self._on_object_resized)
self.preview_frame.object_geometry_changed.connect(self._on_object_geometry_changed)
```

### main_window.py — новые обработчики

```python
def _on_object_resized(self, obj: BaseObject):
    canvas_id = self.elements_panel.tree._model.get_canvas_id_for_obj(obj)
    if canvas_id:
        self.preview_frame.update_object(canvas_id, obj)
    self.properties_panel.update_object_geometry(obj)

def _on_object_geometry_changed(self, obj: BaseObject):
    self.properties_panel.update_object_geometry(obj)
```

### properties_panel.py — новый метод

```python
def update_object_geometry(self, obj: BaseObject):
    if self._current_object and self._current_object.id == obj.id:
        t = self.transform
        t._blocking = True
        t.x_spin.setValue(obj.x)
        t.y_spin.setValue(obj.y)
        t.width_spin.setValue(obj.width)
        t.height_spin.setValue(obj.height)
        gx, gy = obj.get_global_position()
        t.global_label.setText(f"{gx:.1f}, {gy:.1f}")
        t._blocking = False
```

---

## Почему resize не работал раньше

В старом коде `ShapeGraphicsItem` имел **два метода** `mouseReleaseEvent` —
второй перекрывал первый (с `was_resizing`), поэтому сигнал никогда не испускался.
В новой архитектуре весь resize — только в `BaseGraphicsItem`, подклассы его не трогают.

Сигналы теперь два:
- `object_geometry_changed` — испускается **во время** resize (каждый mouseMoveEvent)
  → обновляет панель свойств в реальном времени
- `object_resized` — испускается **после** отпускания мыши
  → финальное обновление сцены
