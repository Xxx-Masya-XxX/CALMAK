"""Debug окно — инспектор ВСЕХ экземпляров классов в программе.

Использует pympler.tracker.SummaryTracker + gc для отслеживания
всех живых объектов в памяти Python.

Подключение в main_window.py:
    from ..ui.debug_window import DebugWindow
    self._debug_window = None
    from PySide6.QtGui import QShortcut, QKeySequence
    QShortcut(QKeySequence("F12"), self).activated.connect(self._open_debug)

    def _open_debug(self):
        if self._debug_window and self._debug_window.isVisible():
            self._debug_window.raise_()
            return
        def get_scene_data():
            canvas = self.controller.get_active_canvas()
            if not canvas:
                return [], {}
            objects = list(self.controller.get_objects(canvas.id))
            scene = self.preview_frame.get_scene(canvas.id)
            items = {}
            if scene:
                for obj, item in scene._object_items.items():
                    items[obj.id] = item
            return objects, items
        self._debug_window = DebugWindow(get_scene_data, parent=self)
        self._debug_window.show()
"""

import gc
import time
import weakref
import dataclasses
import tracemalloc
from datetime import datetime
from typing import Any
from collections import defaultdict

from pympler import asizeof, muppy, summary

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QHeaderView, QSplitter, QTreeWidget, QTreeWidgetItem,
    QFrame, QLineEdit, QCheckBox, QComboBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QFont

from ..models.objects.base_object import BaseObject

# ── Палитра ───────────────────────────────────────────────────────────────────
BG       = "#0d1117"
BG2      = "#161b22"
BG3      = "#21262d"
BORDER   = "#30363d"
TEXT     = "#e6edf3"
TEXT_DIM = "#8b949e"
GREEN    = "#3fb950"
RED      = "#f85149"
BLUE     = "#58a6ff"
YELLOW   = "#d29922"
PURPLE   = "#bc8cff"
CYAN     = "#79c0ff"
ORANGE   = "#f0883e"

BASE_STYLE = f"""
QDialog, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
    font-size: 12px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG2};
}}
QTabBar::tab {{
    background-color: {BG};
    color: {TEXT_DIM};
    padding: 7px 18px;
    border: 1px solid {BORDER};
    border-bottom: none;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {BG2};
    color: {TEXT};
    border-bottom: 2px solid {BLUE};
}}
QTabBar::tab:hover:!selected {{ background-color: {BG3}; color: {TEXT}; }}
QTableWidget {{
    background-color: {BG2};
    color: {TEXT};
    gridline-color: {BORDER};
    border: none;
    selection-background-color: #1f6feb;
}}
QTableWidget::item {{ padding: 2px 6px; }}
QHeaderView::section {{
    background-color: {BG3};
    color: {TEXT_DIM};
    padding: 5px 8px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    font-weight: bold;
    font-size: 10px;
    letter-spacing: 1px;
}}
QTreeWidget {{
    background-color: {BG2};
    color: {TEXT};
    border: none;
}}
QTreeWidget::item:selected {{ background-color: #1f6feb; }}
QTreeWidget::item:hover    {{ background-color: {BG3}; }}
QPushButton {{
    background-color: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 12px;
    border-radius: 4px;
}}
QPushButton:hover {{ background-color: #1f6feb; border-color: {BLUE}; color: white; }}
QPushButton:checked {{ background-color: {BG}; border-color: {YELLOW}; color: {YELLOW}; }}
QLineEdit {{
    background-color: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 3px 8px;
    border-radius: 4px;
}}
QComboBox {{
    background-color: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 3px 8px;
    border-radius: 4px;
}}
QComboBox::drop-down {{ border: none; }}
QScrollBar:vertical {{
    background: {BG}; width: 8px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {BG3}; border-radius: 4px; min-height: 20px;
}}
QSplitter::handle {{ background-color: {BORDER}; width: 1px; height: 1px; }}
QCheckBox {{ color: {TEXT}; }}
"""


# ── Утилиты ───────────────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    if n < 1024:        return f"{n} B"
    if n < 1024 ** 2:   return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.2f} MB"

def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]

def _cell(text: str, color: str = None,
          align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(align)
    if color:
        item.setForeground(QBrush(QColor(color)))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item

def _get_module(cls) -> str:
    return getattr(cls, '__module__', '') or ''

def _short_module(mod: str) -> str:
    """src.ui.panels.sections.transform_section → ui.panels…transform"""
    parts = mod.split('.')
    # Убираем __main__ и слишком длинные пути
    if len(parts) <= 2:
        return mod
    return '.'.join(parts[-2:])


# ── Снимок всех объектов в памяти ────────────────────────────────────────────

def _take_snapshot(filter_str: str = "", only_project: bool = False) -> list[dict]:
    """
    Собирает все живые объекты через gc.get_objects().
    Группирует по классу: (module, classname) → {count, total_size, instances[]}.
    """
    all_objects = gc.get_objects()

    # Группируем по типу
    groups: dict[tuple, dict] = {}
    for obj in all_objects:
        cls  = type(obj)
        name = cls.__name__
        mod  = _get_module(cls)

        if only_project:
            # Показываем только классы из нашего проекта
            if not any(mod.startswith(p) for p in ('src.', '__main__')):
                continue

        if filter_str:
            search = filter_str.lower()
            if search not in name.lower() and search not in mod.lower():
                continue

        key = (mod, name)
        if key not in groups:
            groups[key] = {
                'module':    mod,
                'classname': name,
                'count':     0,
                'size':      0,
                'instances': [],
            }
        groups[key]['count'] += 1
        # Не считаем размер для каждого — слишком медленно для всех объектов
        # Считаем только первые N для превью
        if len(groups[key]['instances']) < 20:
            groups[key]['instances'].append(obj)

    # Сортируем по количеству (desc)
    result = sorted(groups.values(), key=lambda x: x['count'], reverse=True)
    return result


# ── Трекер изменений (дельта между снимками) ─────────────────────────────────

class DeltaTracker:
    """Сравнивает два снимка — показывает что появилось/исчезло."""

    def __init__(self):
        self._prev: dict[tuple, int] = {}  # (mod, cls) → count

    def update(self, snapshot: list[dict]) -> list[dict]:
        """Возвращает записи с добавленным полем delta."""
        current = {(r['module'], r['classname']): r['count'] for r in snapshot}
        result  = []
        for row in snapshot:
            key   = (row['module'], row['classname'])
            prev  = self._prev.get(key, 0)
            delta = row['count'] - prev
            result.append({**row, 'delta': delta})
        self._prev = current
        return result


# ── Трекер жизненного цикла сцены ────────────────────────────────────────────

@dataclasses.dataclass
class LifecycleEvent:
    kind:      str
    ts:        float
    obj_id:    str
    obj_class: str
    obj_name:  str
    ram:       int
    canvas_id: str


class LifecycleTracker:
    def __init__(self):
        self.events: list[LifecycleEvent] = []
        self._known:     dict[str, weakref.ref] = {}
        self._known_ram: dict[str, int]         = {}

    def update(self, objects: list[BaseObject], canvas_id: str = ""):
        current_ids = {obj.id for obj in objects}
        known_ids   = set(self._known.keys())

        for obj in objects:
            if obj.id not in known_ids:
                ram = asizeof.asizeof(obj)
                self.events.append(LifecycleEvent(
                    kind="created", ts=time.time(),
                    obj_id=obj.id, obj_class=type(obj).__name__,
                    obj_name=obj.name, ram=ram, canvas_id=canvas_id,
                ))
                self._known[obj.id]     = weakref.ref(obj)
                self._known_ram[obj.id] = ram

        for obj_id in known_ids - current_ids:
            ref = self._known[obj_id]
            obj = ref()
            self.events.append(LifecycleEvent(
                kind="deleted", ts=time.time(),
                obj_id=obj_id,
                obj_class=type(obj).__name__ if obj else "<?>",
                obj_name=obj.name           if obj else "<?>",
                ram=self._known_ram.get(obj_id, 0),
                canvas_id=canvas_id,
            ))
            del self._known[obj_id]
            del self._known_ram[obj_id]

        for obj in objects:
            self._known_ram[obj.id] = asizeof.asizeof(obj)


# ── Вкладка: Все классы в памяти ─────────────────────────────────────────────

class AllClassesTab(QWidget):
    """Показывает все живые экземпляры классов Python через gc."""

    COLS = ["Класс", "Модуль", "Кол-во", "Δ", "Превью экземпляра"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._delta  = DeltaTracker()
        self._rows:  list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Тулбар
        bar = QFrame()
        bar.setStyleSheet(f"background:{BG3}; border-bottom:1px solid {BORDER};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 4, 8, 4)
        bl.setSpacing(8)

        # Поиск
        self._search = QLineEdit()
        self._search.setPlaceholderText("Фильтр по имени класса или модулю...")
        self._search.setFixedWidth(280)
        self._search.textChanged.connect(self._apply_filter)
        bl.addWidget(self._search)

        # Только проект
        self._only_project = QCheckBox("Только проект")
        self._only_project.setChecked(True)
        self._only_project.stateChanged.connect(self._apply_filter)
        bl.addWidget(self._only_project)

        # Сортировка
        sort_lbl = QLabel("Сортировка:")
        sort_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        bl.addWidget(sort_lbl)
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["По количеству ↓", "По имени ↑", "По дельте ↓"])
        self._sort_combo.currentIndexChanged.connect(self._apply_filter)
        self._sort_combo.setFixedWidth(160)
        bl.addWidget(self._sort_combo)

        bl.addStretch()
        self._status = QLabel("Классов: 0")
        self._status.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        bl.addWidget(self._status)
        lay.addWidget(bar)

        # Сплиттер: таблица классов + инспектор экземпляра
        splitter = QSplitter(Qt.Orientation.Vertical)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels(self.COLS)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellClicked.connect(self._on_row_click)
        splitter.addWidget(self._table)

        # Инспектор выбранного экземпляра
        self._inspector = QTreeWidget()
        self._inspector.setHeaderLabels(["Атрибут", "Тип", "Значение"])
        self._inspector.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._inspector.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self._inspector.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self._inspector)

        splitter.setSizes([420, 220])
        lay.addWidget(splitter)

    def refresh(self):
        filter_str   = self._search.text()
        only_project = self._only_project.isChecked()

        snapshot  = _take_snapshot(filter_str, only_project)
        with_delta = self._delta.update(snapshot)

        # Сортировка
        sort_idx = self._sort_combo.currentIndex()
        if sort_idx == 0:
            with_delta.sort(key=lambda x: x['count'], reverse=True)
        elif sort_idx == 1:
            with_delta.sort(key=lambda x: x['classname'].lower())
        elif sort_idx == 2:
            with_delta.sort(key=lambda x: x.get('delta', 0), reverse=True)

        self._rows = with_delta
        self._status.setText(f"Классов: {len(with_delta)}")
        self._table.setRowCount(len(with_delta))

        for row, rec in enumerate(with_delta):
            delta     = rec.get('delta', 0)
            delta_str = f"+{delta}" if delta > 0 else str(delta) if delta != 0 else "—"
            delta_col = GREEN if delta > 0 else RED if delta < 0 else TEXT_DIM

            # Превью первого экземпляра
            preview = ""
            if rec['instances']:
                inst = rec['instances'][0]
                try:
                    r = repr(inst)
                    preview = r[:80] + "…" if len(r) > 80 else r
                except Exception:
                    preview = "<repr error>"

            # Цвет модуля
            mod = rec['module']
            if mod.startswith('src.'):
                mod_color = CYAN
            elif mod.startswith('PySide6'):
                mod_color = PURPLE
            elif mod.startswith('__'):
                mod_color = TEXT_DIM
            else:
                mod_color = TEXT_DIM

            # Большое количество — подсветить
            count     = rec['count']
            count_col = RED if count > 500 else YELLOW if count > 100 else GREEN if count > 10 else TEXT

            cells = [
                (rec['classname'],              BLUE,      Qt.AlignmentFlag.AlignLeft),
                (_short_module(mod),            mod_color, Qt.AlignmentFlag.AlignLeft),
                (str(count),                    count_col, Qt.AlignmentFlag.AlignCenter),
                (delta_str,                     delta_col, Qt.AlignmentFlag.AlignCenter),
                (preview,                       TEXT_DIM,  Qt.AlignmentFlag.AlignLeft),
            ]
            for col, (val, color, align) in enumerate(cells):
                self._table.setItem(row, col, _cell(val, color, align))

    def _apply_filter(self):
        self.refresh()

    def _on_row_click(self, row: int, _col: int):
        if row >= len(self._rows):
            return
        rec = self._rows[row]
        self._populate_inspector(rec)

    def _populate_inspector(self, rec: dict):
        self._inspector.clear()

        instances = rec['instances']
        if not instances:
            return

        # Заголовок
        root_item = QTreeWidgetItem(self._inspector,
            [f"◆ {rec['classname']}", "", f"{rec['count']} экз. в памяти"])
        root_item.setForeground(0, QBrush(QColor(BLUE)))
        root_item.setForeground(2, QBrush(QColor(CYAN)))
        f = root_item.font(0); f.setBold(True); root_item.setFont(0, f)

        # Показываем до 5 экземпляров
        for idx, inst in enumerate(instances[:5]):
            ram = 0
            try:
                ram = asizeof.asizeof(inst)
            except Exception:
                pass

            inst_node = QTreeWidgetItem(root_item,
                [f"[{idx}]  id={id(inst)}", type(inst).__name__,
                 f"RAM: {_fmt_bytes(ram)}"])
            inst_node.setForeground(0, QBrush(QColor(YELLOW)))
            inst_node.setForeground(2, QBrush(QColor(CYAN)))

            # Атрибуты экземпляра
            attrs = {}
            try:
                if dataclasses.is_dataclass(inst):
                    attrs = {f.name: getattr(inst, f.name)
                             for f in dataclasses.fields(inst)}
                elif hasattr(inst, '__dict__'):
                    attrs = dict(inst.__dict__)
                elif hasattr(inst, '__slots__'):
                    attrs = {s: getattr(inst, s, '<no attr>')
                             for s in inst.__slots__}
            except Exception:
                pass

            for name, val in list(attrs.items())[:40]:
                typ = type(val).__name__
                try:
                    display = repr(val)
                    if len(display) > 100:
                        display = display[:97] + "…"
                except Exception:
                    display = "<repr error>"

                child = QTreeWidgetItem(inst_node, [name, typ, display])
                child.setForeground(1, QBrush(QColor(TEXT_DIM)))

                if isinstance(val, bool):
                    child.setForeground(2, QBrush(QColor(GREEN if val else RED)))
                elif isinstance(val, (int, float)):
                    child.setForeground(2, QBrush(QColor(CYAN)))
                elif isinstance(val, str) and val.startswith("#") and len(val) in (7, 9):
                    try:    child.setForeground(2, QBrush(QColor(val)))
                    except: child.setForeground(2, QBrush(QColor(TEXT)))
                elif val is None:
                    child.setForeground(2, QBrush(QColor(TEXT_DIM)))
                else:
                    child.setForeground(2, QBrush(QColor(TEXT)))

            if len(attrs) > 40:
                QTreeWidgetItem(inst_node,
                    [f"… ещё {len(attrs) - 40} полей", "", ""])

            inst_node.setExpanded(idx == 0)  # Раскрываем только первый

        if rec['count'] > 5:
            QTreeWidgetItem(root_item,
                [f"… ещё {rec['count'] - 5} экземпляров не показаны", "", ""])

        root_item.setExpanded(True)


# ── Вкладка: Объекты сцены (живые) ───────────────────────────────────────────

class SceneObjectsTab(QWidget):
    """Живые объекты сцены с инспектором полей и сравнением с QGraphicsItem."""

    COLS = ["Имя", "Класс", "ID", "RAM", "x", "y", "w", "h", "rot°", "parent"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._objects:   list[BaseObject] = []
        self._items_map: dict[str, Any]   = {}
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        bar = QFrame()
        bar.setStyleSheet(f"background:{BG3}; border-bottom:1px solid {BORDER};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 4, 10, 4)
        self._status = QLabel("Объектов: 0  |  RAM: 0 B")
        self._status.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        bl.addWidget(self._status)
        bl.addStretch()
        lay.addWidget(bar)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels(self.COLS)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(self.COLS)):
            self._table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellClicked.connect(self._on_row_click)
        splitter.addWidget(self._table)

        self._inspector = QTreeWidget()
        self._inspector.setHeaderLabels(["Поле", "Тип", "Значение"])
        self._inspector.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._inspector.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self._inspector.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self._inspector)
        splitter.setSizes([320, 260])
        lay.addWidget(splitter)

    def refresh(self, objects: list[BaseObject], items: dict[str, Any]):
        self._objects   = objects
        self._items_map = items
        total_ram = sum(asizeof.asizeof(o) for o in objects)
        self._status.setText(
            f"Объектов: {len(objects)}  |  RAM: {_fmt_bytes(total_ram)}")

        self._table.setRowCount(len(objects))
        for row, obj in enumerate(objects):
            ram   = asizeof.asizeof(obj)
            gitem = items.get(obj.id)
            warn  = ""
            if gitem and hasattr(gitem, 'pos'):
                p = gitem.pos()
                if abs(p.x() - obj.x) > 0.5 or abs(p.y() - obj.y) > 0.5:
                    warn = " ⚠"

            cells = [
                (obj.name,                                  TEXT,    Qt.AlignmentFlag.AlignLeft),
                (type(obj).__name__,                         PURPLE,  Qt.AlignmentFlag.AlignLeft),
                (obj.id[:10] + "…",                         TEXT_DIM,Qt.AlignmentFlag.AlignLeft),
                (_fmt_bytes(ram),                            CYAN,    Qt.AlignmentFlag.AlignCenter),
                (f"{obj.x:.1f}{warn}", YELLOW if warn else TEXT,      Qt.AlignmentFlag.AlignCenter),
                (f"{obj.y:.1f}",                             TEXT,    Qt.AlignmentFlag.AlignCenter),
                (f"{obj.width:.1f}",                         GREEN,   Qt.AlignmentFlag.AlignCenter),
                (f"{obj.height:.1f}",                        GREEN,   Qt.AlignmentFlag.AlignCenter),
                (f"{obj.rotation:.1f}", YELLOW if obj.rotation else TEXT, Qt.AlignmentFlag.AlignCenter),
                (obj.parent_id[:8]+"…" if obj.parent_id else "—", TEXT_DIM, Qt.AlignmentFlag.AlignCenter),
            ]
            for col, (val, color, align) in enumerate(cells):
                self._table.setItem(row, col, _cell(val, color, align))

        rows = self._table.selectionModel().selectedRows()
        if rows and rows[0].row() < len(objects):
            self._populate_inspector(objects[rows[0].row()])

    def _on_row_click(self, row: int, _col: int):
        if row < len(self._objects):
            self._populate_inspector(self._objects[row])

    def _populate_inspector(self, obj: BaseObject):
        self._inspector.clear()
        ram = asizeof.asizeof(obj)
        root = QTreeWidgetItem(self._inspector,
            [f"◆ {obj.name}", type(obj).__name__, f"RAM: {_fmt_bytes(ram)}"])
        root.setForeground(0, QBrush(QColor(BLUE)))
        root.setForeground(2, QBrush(QColor(CYAN)))
        f = root.font(0); f.setBold(True); root.setFont(0, f)

        mn = QTreeWidgetItem(root, ["📦 Поля модели", "", ""])
        mn.setForeground(0, QBrush(QColor(YELLOW)))

        fields = ({f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)}
                  if dataclasses.is_dataclass(obj) else vars(obj))

        for name, val in sorted(fields.items()):
            display = repr(val) if not isinstance(val, str) else f'"{val}"'
            if len(display) > 90: display = display[:87] + "…"
            child = QTreeWidgetItem(mn, [name, type(val).__name__, display])
            child.setForeground(1, QBrush(QColor(TEXT_DIM)))
            if isinstance(val, bool):
                child.setForeground(2, QBrush(QColor(GREEN if val else RED)))
            elif isinstance(val, (int, float)):
                child.setForeground(2, QBrush(QColor(CYAN)))
            else:
                child.setForeground(2, QBrush(QColor(TEXT)))

        gitem = self._items_map.get(obj.id)
        if gitem:
            gn = QTreeWidgetItem(root, ["🎨 QGraphicsItem", "", ""])
            gn.setForeground(0, QBrush(QColor(PURPLE)))
            try:
                pos = gitem.pos()
                dx, dy = abs(pos.x()-obj.x), abs(pos.y()-obj.y)
                for label, val in [
                    ("pos()",        f"({pos.x():.2f}, {pos.y():.2f})"),
                    ("zValue()",     f"{gitem.zValue():.1f}"),
                    ("isSelected()", str(gitem.isSelected())),
                    ("type",         type(gitem).__name__),
                ]:
                    c = QTreeWidgetItem(gn, [label, "—", val])
                    c.setForeground(0, QBrush(QColor(TEXT_DIM)))
                    c.setForeground(2, QBrush(QColor(CYAN)))
                if dx > 0.5 or dy > 0.5:
                    w = QTreeWidgetItem(gn, ["⚠ РАСХОЖДЕНИЕ pos", "",
                        f"obj({obj.x:.1f},{obj.y:.1f}) ≠ item({pos.x():.1f},{pos.y():.1f})"])
                    w.setForeground(0, QBrush(QColor(RED)))
                    w.setForeground(2, QBrush(QColor(RED)))
            except Exception as e:
                QTreeWidgetItem(gn, ["error", "", str(e)])
            gn.setExpanded(True)

        root.setExpanded(True)
        mn.setExpanded(True)


# ── Вкладка: История объектов сцены ──────────────────────────────────────────

class LifecycleTab(QWidget):

    COLS = ["Время", "Событие", "Имя", "Класс", "ID", "RAM", "Canvas"]

    def __init__(self, tracker: LifecycleTracker, parent=None):
        super().__init__(parent)
        self._tracker    = tracker
        self._last_count = 0
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        bar = QFrame()
        bar.setStyleSheet(f"background:{BG3}; border-bottom:1px solid {BORDER};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 4, 10, 4)
        self._lbl = QLabel("Событий: 0")
        self._lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        bl.addWidget(self._lbl)
        bl.addStretch()
        btn = QPushButton("Очистить")
        btn.clicked.connect(self._clear)
        bl.addWidget(btn)
        lay.addWidget(bar)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels(self.COLS)
        modes = [
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.Stretch,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
        ]
        for i, m in enumerate(modes):
            self._table.horizontalHeader().setSectionResizeMode(i, m)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        lay.addWidget(self._table)

    def refresh(self):
        events = self._tracker.events
        if len(events) == self._last_count:
            return
        self._table.setRowCount(len(events))
        self._lbl.setText(f"Событий: {len(events)}")
        for row, ev in enumerate(events):
            created  = ev.kind == "created"
            row_bg   = QColor("#0d1f0d") if created else QColor("#1f0d0d")
            kind_col = GREEN if created else RED
            cells = [
                (_fmt_time(ev.ts),                                             TEXT_DIM, Qt.AlignmentFlag.AlignCenter),
                ("✚ создан" if created else "✖ удалён",                       kind_col, Qt.AlignmentFlag.AlignCenter),
                (ev.obj_name,                                                   TEXT,    Qt.AlignmentFlag.AlignLeft),
                (ev.obj_class,                                                  PURPLE,  Qt.AlignmentFlag.AlignLeft),
                (ev.obj_id[:14]+"…",                                           TEXT_DIM,Qt.AlignmentFlag.AlignLeft),
                (_fmt_bytes(ev.ram),                                            CYAN,    Qt.AlignmentFlag.AlignCenter),
                (ev.canvas_id[:10] if ev.canvas_id else "—",                  TEXT_DIM,Qt.AlignmentFlag.AlignCenter),
            ]
            for col, (val, color, align) in enumerate(cells):
                c = _cell(val, color, align)
                c.setBackground(QBrush(row_bg))
                self._table.setItem(row, col, c)
        if len(events) > self._last_count:
            self._table.scrollToBottom()
        self._last_count = len(events)

    def _clear(self):
        self._tracker.events.clear()
        self._last_count = 0
        self._table.setRowCount(0)
        self._lbl.setText("Событий: 0")


# ── Главное окно ──────────────────────────────────────────────────────────────

class DebugWindow(QDialog):
    """CALMAK Memory Inspector — все экземпляры классов + сцена + история."""

    def __init__(self, get_scene_data_fn, parent=None):
        super().__init__(parent)
        self._get_data   = get_scene_data_fn
        self._tracker    = LifecycleTracker()
        self._paused     = False

        self.setWindowTitle("CALMAK — Memory Inspector")
        self.setMinimumSize(1000, 720)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(BASE_STYLE)
        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Шапка
        header = QFrame()
        header.setFixedHeight(44)
        header.setStyleSheet(f"background:{BG3}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 10, 0)
        title = QLabel("◈  Memory Inspector")
        title.setStyleSheet(
            f"color:{BLUE}; font-size:14px; font-weight:bold; letter-spacing:1px;")
        hl.addWidget(title)
        hl.addStretch()

        self._live_dot = QLabel("● live")
        self._live_dot.setStyleSheet(f"color:{GREEN}; font-size:11px;")
        hl.addWidget(self._live_dot)

        pause_btn = QPushButton("⏸ Пауза")
        pause_btn.setCheckable(True)
        pause_btn.setFixedWidth(90)
        pause_btn.toggled.connect(self._on_pause)
        hl.addWidget(pause_btn)

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedWidth(32)
        refresh_btn.setToolTip("Обновить сейчас")
        refresh_btn.clicked.connect(self._tick)
        hl.addWidget(refresh_btn)
        root.addWidget(header)

        # Вкладки
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        self._all_classes_tab = AllClassesTab()
        self._scene_tab       = SceneObjectsTab()
        self._lifecycle_tab   = LifecycleTab(self._tracker)

        tabs.addTab(self._all_classes_tab, "🧠  Все классы")
        tabs.addTab(self._scene_tab,       "🔵  Объекты сцены")
        tabs.addTab(self._lifecycle_tab,   "📋  История сцены")

        root.addWidget(tabs)

    def _tick(self):
        if self._paused:
            return
        try:
            objects, items = self._get_data()
        except Exception:
            objects, items = [], {}

        canvas_id = getattr(objects[0], 'canvas_id', "") if objects else ""
        self._tracker.update(objects, canvas_id)

        # Обновляем активную вкладку
        idx = self.findChild(QTabWidget).currentIndex()
        if idx == 0:
            self._all_classes_tab.refresh()
        elif idx == 1:
            self._scene_tab.refresh(objects, items)
        elif idx == 2:
            self._lifecycle_tab.refresh()

        # История обновляется всегда (она лёгкая)
        if idx != 2:
            self._lifecycle_tab.refresh()

    def _on_pause(self, paused: bool):
        self._paused = paused
        if paused:
            self._live_dot.setText("⏸ пауза")
            self._live_dot.setStyleSheet(f"color:{YELLOW}; font-size:11px;")
        else:
            self._live_dot.setText("● live")
            self._live_dot.setStyleSheet(f"color:{GREEN}; font-size:11px;")
            self._tick()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)