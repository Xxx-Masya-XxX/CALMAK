# **ШАГ 1. Создать базовую структуру CalendarNode**

**Что создать:**

* Новый объект `CalendarNode`
* Он работает как **контейнер / папка**, может хранить дочерние объекты-шаблоны (Canvas)
* Имеет **специальный список сгенерированных объектов для превью** (`preview_objects`)

**Структура:**

```txt
CalendarNode
    settings
    templates
    preview_objects
```

---

# **ШАГ 2. Определить настройки CalendarNode**

**Настройки генерации календаря:**

```txt
settings:
    month           : int 1..12
    year            : int
    week_start      : int 0..6       # 0 = Пн, 6 = Вс
    day_width       : float          # ширина одного дня
    day_height      : float          # высота одного дня
    spacing_x       : float          # отступ между днями по горизонтали
    spacing_y       : float          # отступ между днями по вертикали
    margin_left     : float          # отступ от края канваса
    margin_right    : float
    margin_top      : float
    margin_bottom   : float
    special_days    : list[dict]     # [{"date":"2026-01-07","text":"Рождество"}]
```

> Эти настройки определяют **сетки календаря**, расположение дней, отступы и особые дни.

---

# **ШАГ 3. Создать шаблоны в CalendarNode**

**Типы шаблонов:**

```txt
templates:
    template_day           : Canvas
    template_weekend       : Canvas
    template_special_day   : Canvas
    template_empty_day     : Canvas
    template_weekday       : Canvas
    template_week_number   : Canvas
```

**Что хранит каждый шаблон:**

* **Canvas** с дочерними объектами (`Shape` и `Text`)
* Для каждого `Text` объекта указывать `role` (роль), по которой CalendarNode будет подставлять текст:

```txt
Roles для Text:
    "day_number"     # дата обычного/выходного дня
    "special_text"   # описание особого дня
    "weekday_name"   # название дня недели
    "week_number"    # номер недели
    "month_name"     # название месяца
```

**Пример: template_special_day**

```txt
Canvas (template_special_day)
    Shape: фон
    Text: role="day_number"
    Text: role="special_text"
```

---

# **ШАГ 4. Поддержка редактирования шаблонов**

* Пользователь выбирает шаблон в CalendarNode
* Может редактировать **Canvas, Shape, Text**
* `role` для Text сохраняется для подстановки текста

**Важно:** сгенерированные объекты в `preview_objects` нельзя редактировать напрямую.

---

# **ШАГ 5. Создать функцию генерации календаря**

**Алгоритм:**

1. Очистить `preview_objects`
2. Определить **первый день месяца и количество дней**
3. Создать **weekday row** (дни недели)
4. Создать **сетки 7×6 (недели × дни)**
5. Для каждой ячейки:

   * Определить тип дня: обычный, выходной, особый, пустой
   * Выбрать соответствующий шаблон Canvas
   * Клонировать Canvas и все дочерние объекты
   * Подставить текст в Text объекты по `role`
   * Выставить координаты (x = column * (day_width + spacing_x), y = row * (day_height + spacing_y))
6. Добавить в `preview_objects` для рендеринга превью

---

# **ШАГ 6. Система подстановки текста**

```python
for obj in cloned_template.children:
    if obj.role == "day_number":
        obj.text = номер_дня
    elif obj.role == "special_text":
        obj.text = текст_особого_дня
    elif obj.role == "weekday_name":
        obj.text = название_дня
    elif obj.role == "week_number":
        obj.text = номер_недели
    elif obj.role == "month_name":
        obj.text = название месяца
```

---

# **ШАГ 7. Автоматический рендер превью**

* `preview_objects` рендерятся в сцене как обычные объекты
* Используются **для визуализации** календаря внутри редактора
* Пользователь редактирует **только шаблоны и настройки**, а не инстансы

---

# **ШАГ 8. Дополнительно стоит добавить в редактор**

1. **Canvas как полноценный объект-контейнер** (может хранить дочерние Shape/Text/Canvas)
2. **CloneCanvas()** для копирования шаблонов без изменения оригинала
3. **Role для Text объектов** для подстановки текста
4. **Anchor / Pivot** для объектов внутри шаблонов, чтобы текст правильно центрировался при изменении размеров
5. **Flags** для объектов:

   * editable: можно редактировать
   * generated: нельзя редактировать (для объектов preview)

---

# **ШАГ 9. Итоговая структура CalendarNode**

```txt
CalendarNode
    settings
        month, year, week_start
        day_width, day_height
        spacing_x, spacing_y
        margin_top, margin_left, ...
        special_days

    templates
        template_day         (Canvas)
            Shape
            Text(role="day_number")
        template_weekend     (Canvas)
            Shape
            Text(role="day_number")
        template_special_day (Canvas)
            Shape
            Text(role="day_number")
            Text(role="special_text")
        template_empty_day   (Canvas)
            Shape
        template_weekday     (Canvas)
            Text(role="weekday_name")
        template_week_number (Canvas)
            Text(role="week_number")

    preview_objects
        инстансы шаблонов с подставленным текстом
```

