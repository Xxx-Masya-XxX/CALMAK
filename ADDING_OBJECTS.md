# Добавление нового типа объекта в Canvas Editor

## Обзор архитектуры

Каждый тип объекта проходит через 6 слоёв приложения.
Чтобы добавить новый тип — нужно расширить каждый из них:

```
1. domain/models.py          ← тип, payload, фабричная функция
2. rendering/scene_renderer.py ← как рисовать на сцене
3. export/exporter.py          ← как рендерить в PNG/JPEG
4. serialization/serializer.py ← как сохранять/загружать
5. ui/panels/properties_panel.py ← панель свойств
6. ui/constants.py + ui/main_window.py ← иконка, кнопка создания
```

---

## Пример: кривая Безье

Добавим тип `BEZIER` — кубическую кривую Безье с двумя контрольными точками.

---

### Шаг 1 — `domain/models.py`

#### 1.1 Добавить значение в `ObjectType`

```python
class ObjectType(str, Enum):
    GROUP    = "group"
    RECT     = "rect"
    ELLIPSE  = "ellipse"
    TEXT     = "text"
    IMAGE    = "image"
    BEZIER   = "bezier"   # ← НОВЫЙ ТИП
```

#### 1.2 Создать payload-датакласс

Payload хранит данные специфичные для этого типа объекта.
Для кривой Безье — четыре точки: P0, P1, P2, P3.

```python
@dataclass
class BezierPayload:
    # Точки в локальных координатах объекта (0..1 от bounding box)
    # P0 = начало, P3 = конец, P1/P2 = контрольные точки
    p0x: float = 0.0;   p0y: float = 0.5
    p1x: float = 0.3;   p1y: float = 0.0
    p2x: float = 0.7;   p2y: float = 1.0
    p3x: float = 1.0;   p3y: float = 0.5
```

#### 1.3 Добавить фабричную функцию

```python
def make_bezier(name="Bezier", x=100, y=100, w=200, h=100) -> ObjectState:
    obj = ObjectState(
        id=gen_id(),
        type=ObjectType.BEZIER,
        name=name,
        transform=Transform(x=x, y=y, width=w, height=h),
        style=StyleState(
            fill_color="transparent",
            stroke_color="#E2904A",
            stroke_width=2.5,
        ),
        payload=BezierPayload(),
    )
    return obj
```

---

### Шаг 2 — `rendering/scene_renderer.py`

#### 2.1 Импорт нового payload и типа

```python
from domain.models import (ObjectState, ObjectType, CanvasState,
                            TextPayload, ImagePayload, StyleState,
                            BezierPayload)   # ← добавить
```

#### 2.2 Добавить ветку в `_make_item`

```python
def _make_item(self, obj: ObjectState) -> QGraphicsItem | None:
    # ... существующие ветки ...

    elif obj.type == ObjectType.BEZIER:
        item = QGraphicsPathItem()
        _apply_style_bezier(item, obj)
        _apply_transform(item, obj)
        return item

    return None
```

#### 2.3 Написать функцию стиля

```python
def _apply_style_bezier(item: "QGraphicsPathItem", obj: ObjectState):
    from PySide6.QtGui import QPainterPath
    s = obj.style
    t = obj.transform
    payload = obj.payload

    if not isinstance(payload, BezierPayload):
        return

    # Переводим нормализованные координаты (0..1) в пиксели
    def pt(nx, ny):
        return QPointF(nx * t.width, ny * t.height)

    path = QPainterPath(pt(payload.p0x, payload.p0y))
    path.cubicTo(
        pt(payload.p1x, payload.p1y),
        pt(payload.p2x, payload.p2y),
        pt(payload.p3x, payload.p3y),
    )
    item.setPath(path)

    # Заливка прозрачная, обводка цветная
    fill = _color(s.fill_color)
    item.setBrush(QBrush(fill))
    pen = QPen(_color(s.stroke_color), s.stroke_width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    item.setPen(pen)
```

> **Важно:** `QGraphicsPathItem` нужно добавить в импорт:
> ```python
> from PySide6.QtWidgets import (... QGraphicsPathItem)
> ```

---

### Шаг 3 — `export/exporter.py`

Добавить ветку в `_draw_object`:

```python
elif obj.type == ObjectType.BEZIER:
    from PySide6.QtGui import QPainterPath
    payload = obj.payload
    if not isinstance(payload, BezierPayload):
        continue

    def pt(nx, ny):
        return QPointF(nx * t.width, ny * t.height)

    path = QPainterPath(pt(payload.p0x, payload.p0y))
    path.cubicTo(
        pt(payload.p1x, payload.p1y),
        pt(payload.p2x, payload.p2y),
        pt(payload.p3x, payload.p3y),
    )

    painter.setBrush(QBrush(_color(s.fill_color)))
    pen = QPen(_color(s.stroke_color), s.stroke_width)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawPath(path)
```

Также добавить импорт:
```python
from domain.models import (..., BezierPayload)
```

---

### Шаг 4 — `serialization/serializer.py`

#### 4.1 Сохранение payload — в `_obj_to_dict`

```python
@staticmethod
def _obj_to_dict(obj: ObjectState) -> dict:
    payload_data = {}
    if isinstance(obj.payload, TextPayload):
        payload_data = {"text": obj.payload.text}
    elif isinstance(obj.payload, ImagePayload):
        payload_data = {"source_path": obj.payload.source_path}
    elif isinstance(obj.payload, BezierPayload):          # ← ДОБАВИТЬ
        p = obj.payload
        payload_data = {
            "p0x": p.p0x, "p0y": p.p0y,
            "p1x": p.p1x, "p1y": p.p1y,
            "p2x": p.p2x, "p2y": p.p2y,
            "p3x": p.p3x, "p3y": p.p3y,
        }
    # ... rest unchanged
```

#### 4.2 Загрузка payload — в `_obj_from_dict`

```python
p_data = d.get("payload", {})
if obj_type == ObjectType.TEXT:
    payload = TextPayload(text=p_data.get("text", ""))
elif obj_type == ObjectType.IMAGE:
    payload = ImagePayload(source_path=p_data.get("source_path", ""))
elif obj_type == ObjectType.BEZIER:                       # ← ДОБАВИТЬ
    payload = BezierPayload(
        p0x=p_data.get("p0x", 0.0), p0y=p_data.get("p0y", 0.5),
        p1x=p_data.get("p1x", 0.3), p1y=p_data.get("p1y", 0.0),
        p2x=p_data.get("p2x", 0.7), p2y=p_data.get("p2y", 1.0),
        p3x=p_data.get("p3x", 1.0), p3y=p_data.get("p3y", 0.5),
    )
elif obj_type == ObjectType.GROUP:
    payload = GroupPayload()
else:
    payload = ShapePayload()
```

---

### Шаг 5 — `ui/panels/properties_panel.py`

#### 5.1 Добавить ветку в `_build_for_object`

```python
def _build_for_object(self, obj: ObjectState):
    self._obj_layout.addWidget(SectionHeader("Object"))
    self._add_common(obj)
    self._obj_layout.addWidget(SectionHeader("Transform"))
    self._add_transform(obj)

    if obj.type in (ObjectType.RECT, ObjectType.ELLIPSE):
        self._obj_layout.addWidget(SectionHeader("Appearance"))
        self._add_shape_style(obj)
    elif obj.type == ObjectType.TEXT:
        ...
    elif obj.type == ObjectType.BEZIER:                   # ← ДОБАВИТЬ
        self._obj_layout.addWidget(SectionHeader("Bezier Curve"))
        self._add_bezier(obj)
        self._obj_layout.addWidget(SectionHeader("Stroke"))
        self._add_bezier_stroke(obj)
```

#### 5.2 Написать секцию свойств

```python
def _add_bezier(self, obj: ObjectState):
    from domain.models import BezierPayload
    payload = obj.payload
    if not isinstance(payload, BezierPayload):
        return

    # Для каждой точки — два спиннера X/Y (значения 0..1)
    points = [
        ("P0 (start)", "payload_p0x", "payload_p0y",
         payload.p0x, payload.p0y),
        ("P1 (ctrl)", "payload_p1x", "payload_p1y",
         payload.p1x, payload.p1y),
        ("P2 (ctrl)", "payload_p2x", "payload_p2y",
         payload.p2x, payload.p2y),
        ("P3 (end)",  "payload_p3x", "payload_p3y",
         payload.p3x, payload.p3y),
    ]
    for label, kx, ky, vx, vy in points:
        self._obj_layout.addWidget(SectionHeader(label))
        sx = _spin(0, 1, dec=3, step=0.05)
        sx.setValue(vx)
        sx.valueChanged.connect(lambda v, k=kx: self._commit(k, v))
        self._obj_layout.addWidget(PropRow("X", sx))

        sy = _spin(0, 1, dec=3, step=0.05)
        sy.setValue(vy)
        sy.valueChanged.connect(lambda v, k=ky: self._commit(k, v))
        self._obj_layout.addWidget(PropRow("Y", sy))

def _add_bezier_stroke(self, obj: ObjectState):
    s = obj.style
    stroke = ColorButton(s.stroke_color)
    self._pick_color(stroke, "style.stroke_color")
    self._obj_layout.addWidget(PropRow("Color", stroke))

    sw = _spin(0.5, 50)
    sw.setValue(s.stroke_width)
    sw.valueChanged.connect(lambda v: self._commit("style.stroke_width", v))
    self._obj_layout.addWidget(PropRow("Width", sw))
```

#### 5.3 Добавить поддержку новых payload-ключей в `UpdatePropertiesCommand`

В `commands/commands.py` найти метод `_apply` класса `UpdatePropertiesCommand` и добавить:

```python
def _apply(self, obj: "ObjectState", updates: dict):
    for key, value in updates.items():
        if "." in key:
            attr, sub = key.split(".", 1)
            setattr(getattr(obj, attr), sub, value)
        elif key == "name":    obj.name = value
        elif key == "visible": obj.visible = value
        elif key == "locked":  obj.locked = value
        elif key == "payload_text":
            from domain.models import TextPayload
            if isinstance(obj.payload, TextPayload):
                obj.payload.text = value
        elif key == "payload_image":
            from domain.models import ImagePayload
            if isinstance(obj.payload, ImagePayload):
                obj.payload.source_path = value

        # ── НОВЫЕ КЛЮЧИ ДЛЯ BEZIER ──────────────────────────────
        elif key.startswith("payload_p") and key[9] in "0123" and key[10] in "xy":
            from domain.models import BezierPayload
            if isinstance(obj.payload, BezierPayload):
                setattr(obj.payload, key[8:], value)  # p0x, p1y, etc.
        # ────────────────────────────────────────────────────────
```

---

### Шаг 6 — `ui/constants.py`

Добавить иконку и цвет для нового типа:

```python
class ICONS:
    MAP = {
        ObjectType.RECT:    "▭",
        ObjectType.ELLIPSE: "◯",
        ObjectType.TEXT:    "T",
        ObjectType.IMAGE:   "🖼",
        ObjectType.GROUP:   "📁",
        ObjectType.BEZIER:  "〜",   # ← ДОБАВИТЬ
    }

class OBJECT_COLORS:
    MAP = {
        ObjectType.RECT:    "#4A90E2",
        ObjectType.ELLIPSE: "#E2604A",
        ObjectType.TEXT:    "#4AE27A",
        ObjectType.IMAGE:   "#E2A84A",
        ObjectType.GROUP:   "#A84AE2",
        ObjectType.BEZIER:  "#E2C44A",  # ← ДОБАВИТЬ
    }
```

---

### Шаг 7 — `ui/main_window.py`

#### 7.1 Метод создания в `MainWindow`

```python
def _add_bezier_action(self):
    self._controller.add_bezier()
```

#### 7.2 Добавить кнопку в Create toolbar

```python
def _build_create_toolbar(self):
    # ...
    objects = [
        ("add_rect",     "▭", "Rectangle"),
        ("add_ellipse",  "◯", "Ellipse"),
        ("add_triangle", "△", "Triangle"),
        ("add_text",     "T", "Text"),
        ("add_image",    "🖼","Image"),
        ("add_bezier",   "〜","Bezier"),  # ← ДОБАВИТЬ
    ]
```

#### 7.3 Добавить в DEFAULT_HOTKEYS (опционально)

```python
DEFAULT_HOTKEYS: dict[str, str] = {
    ...
    "add_bezier": "",   # ← ДОБАВИТЬ
}
```

---

### Шаг 8 — `controllers/editor_controller.py`

Добавить метод создания:

```python
def add_bezier(self, x=100, y=100, w=200, h=100):
    from domain.models import make_bezier
    cid = self._canvas_id()
    if not cid:
        return
    canvas = self.store.active_canvas
    n = sum(1 for o in canvas.objects.values()
            if o.type == ObjectType.BEZIER) + 1
    obj = make_bezier(f"Bezier {n}", x, y, w, h)
    self.store._push_command(AddObjectCommand(cid, obj))
    self.select_one(obj.id)
```

---

## Итоговый чеклист

| Файл | Что добавить |
|------|-------------|
| `domain/models.py` | `ObjectType.BEZIER`, `BezierPayload`, `make_bezier()` |
| `rendering/scene_renderer.py` | ветка в `_make_item`, функция `_apply_style_bezier` |
| `export/exporter.py` | ветка в `_draw_object` |
| `serialization/serializer.py` | сериализация/десериализация payload |
| `ui/panels/properties_panel.py` | ветка в `_build_for_object`, методы `_add_bezier`, `_add_bezier_stroke` |
| `commands/commands.py` | ключи `payload_p0x..p3y` в `UpdatePropertiesCommand._apply` |
| `ui/constants.py` | иконка и цвет в `ICONS.MAP` и `OBJECT_COLORS.MAP` |
| `controllers/editor_controller.py` | метод `add_bezier()` |
| `ui/main_window.py` | кнопка в Create toolbar, `_add_bezier_action`, DEFAULT_HOTKEYS |

---

## Типичные ошибки

**Забыли обновить сериализатор** — объект не сохраняется/загружается,
payload при загрузке будет `ShapePayload()` вместо `BezierPayload`.

**Забыли ветку в `_make_item`** — объект на сцене не виден
(рендерер вернёт `None`).

**Забыли ветку в `_draw_object` экспортёра** — объект есть на превью,
но отсутствует в экспортированном PNG.

**Ключи payload в `UpdatePropertiesCommand`** — если не добавить обработку
новых ключей, изменения в панели свойств не будут применяться,
и undo/redo не будет работать для них.

---

## Советы по расширению

**Если нужен интерактивный редактор формы** (например, тащить контрольные
точки кривой прямо на сцене) — добавьте новый инструмент в
`tools/tool_manager.py` по образцу `ScaleTool`.

**Если объект имеет составную геометрию** (несколько контуров, дырки) —
используйте `QPainterPath` с несколькими `moveTo`/`lineTo`/`cubicTo`.

**Если payload большой** — можно хранить его отдельным файлом в zip-архиве
проекта, обновив `serialization/serializer.py`.
