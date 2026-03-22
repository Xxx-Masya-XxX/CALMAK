"""
PropertiesPanel — панель свойств выбранного объекта + настройки канваса.
Фиксы:
  - чекбоксы: используем checkStateChanged(Qt.CheckState) вместо stateChanged(int)
  - guard _updating блокирует только setValue/setChecked, не connect
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox,
    QColorDialog, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QTabWidget, QFileDialog, QTextEdit
)
from domain.models import (ObjectState, ObjectType, TextPayload, ImagePayload)

if TYPE_CHECKING:
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SectionHeader(QLabel):
    def __init__(self, text: str):
        super().__init__(text.upper())
        self.setStyleSheet(
            "color:#6A6A8A;font-size:10px;font-weight:bold;"
            "padding:10px 8px 3px 8px;letter-spacing:1px;")


class PropRow(QWidget):
    def __init__(self, label: str, widget: QWidget):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(8)
        lbl = QLabel(label)
        lbl.setFixedWidth(72)
        lbl.setStyleSheet("font-size:11px;")
        lay.addWidget(lbl)
        lay.addWidget(widget, 1)


# Minimal structural styles — colors come from QApplication theme stylesheet
_SPIN_SS = "font-size:11px;"
_LINE_SS = "font-size:11px;"
_BTN_SS  = "font-size:11px;"
_CHECK_SS = "font-size:11px;"


def _spin(mn=-9999, mx=9999, dec=1, step=1.0) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(mn, mx); s.setDecimals(dec); s.setSingleStep(step)
    s.setStyleSheet(_SPIN_SS)
    return s


def _ispin(mn=0, mx=9999) -> QSpinBox:
    s = QSpinBox()
    s.setRange(mn, mx)
    s.setStyleSheet(_SPIN_SS)
    return s


def _line() -> QLineEdit:
    e = QLineEdit()
    e.setStyleSheet(_LINE_SS)
    return e


def _btn(text: str, slot=None) -> QPushButton:
    b = QPushButton(text)
    b.setStyleSheet(_BTN_SS)
    if slot:
        b.clicked.connect(slot)
    return b


class ColorButton(QPushButton):
    """
    Кнопка выбора цвета. При клике открывает QColorDialog.
    После выбора эмитит clicked (стандартный сигнал QPushButton).
    Внешний код подключается к clicked и читает get_color().
    """
    def __init__(self, color="#FFFFFF", parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(64, 24)
        self._color = color
        self._refresh()
        # Перехватываем нажатие сами — не используем внешний clicked
        self.clicked.connect(self._open_dialog)

    def _open_dialog(self):
        initial = (QColor(self._color) if self._color != "transparent"
                   else QColor(255, 255, 255))
        dlg = QColorDialog(initial, self)
        dlg.setOption(QColorDialog.ShowAlphaChannel)
        if dlg.exec():
            self._color = dlg.currentColor().name()
            self._refresh()
            # Сообщаем всем подписчикам что цвет изменился
            self.color_picked.emit(self._color)

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._refresh()

    def get_color(self) -> str:
        return self._color

    def _refresh(self):
        c = self._color if self._color != "transparent" else "#444455"
        self.setStyleSheet(
            f"QPushButton{{background:{c};border:1px solid #555566;border-radius:3px;}}"
            f"QPushButton:hover{{border:1px solid #7A7AAA;}}")

    # Кастомный сигнал — эмитится только после реального выбора цвета
    from PySide6.QtCore import Signal as _Signal
    color_picked = _Signal(str)


# ---------------------------------------------------------------------------
# PropertiesPanel
# ---------------------------------------------------------------------------

class PropertiesPanel(QWidget):
    def __init__(self, store: "EditorStore", controller: "EditorController"):
        super().__init__()
        self._store      = store
        self._controller = controller
        self._current_id: str | None = None
        self._updating   = False

        self._setup_ui()
        self._connect_store()

    # -----------------------------------------------------------------------
    def _setup_ui(self):
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        pass  # colors from QApplication theme stylesheet

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet("border-bottom:1px solid palette(mid);")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(8, 6, 8, 6)
        t = QLabel("Properties")
        t.setStyleSheet("font-weight:bold;font-size:12px;")
        hl.addWidget(t)
        outer.addWidget(hdr)

        # Tabs: Object | Canvas
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border:none; background:#1A1A2A; }
            QTabBar::tab {
                background:#252535; color:#888899;
                padding:5px 14px; border:none; font-size:11px;
            }
            QTabBar::tab:selected { background:#1A1A2A; color:#CCCCDD;
                border-bottom:2px solid #4A90E2; }
            QTabBar::tab:hover { color:#CCCCDD; }
        """)
        outer.addWidget(self._tabs)

        # --- Object tab ---
        obj_widget = QWidget()
        
        obj_scroll = QScrollArea()
        obj_scroll.setWidgetResizable(True)
        obj_scroll.setStyleSheet("QScrollArea{border:none;}")
        obj_scroll.setWidget(obj_widget)
        self._obj_layout = QVBoxLayout(obj_widget)
        self._obj_layout.setContentsMargins(0, 4, 0, 8)
        self._obj_layout.setSpacing(0)
        self._tabs.addTab(obj_scroll, "Object")

        # --- Canvas tab ---
        canvas_widget = QWidget()
        
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(True)
        canvas_scroll.setStyleSheet("QScrollArea{border:none;}")
        canvas_scroll.setWidget(canvas_widget)
        self._canvas_layout = QVBoxLayout(canvas_widget)
        self._canvas_layout.setContentsMargins(0, 4, 0, 8)
        self._canvas_layout.setSpacing(0)
        self._tabs.addTab(canvas_scroll, "Canvas")

        self._build_canvas_tab()
        self._show_empty()

    def _connect_store(self):
        self._store.selection_changed.connect(self._on_selection_changed)
        self._store.document_changed.connect(self._on_document_changed)
        self._store.canvas_switched.connect(lambda _: self._refresh_canvas_tab())

    def _on_selection_changed(self, ids, active_id):
        """Выбор изменился — полная перестройка панели под новый объект."""
        self._current_id = active_id
        self._rebuild_obj_panel()

    def _on_document_changed(self):
        """
        Документ изменился (move/color/etc).
        Если выбранный объект тот же — только обновляем значения спиннеров/текста
        без пересоздания виджетов (иначе панель мигает при drag).
        Если объект удалён — показываем empty.
        """
        self._refresh_canvas_tab()
        if not self._current_id:
            return
        canvas = self._store.active_canvas
        if not canvas or self._current_id not in canvas.objects:
            self._show_empty()
            self._current_id = None
            return
        # Обновляем значения в существующих виджетах без rebuild
        self._update_values_in_place()

    def _update_values_in_place(self):
        """
        Обновляет числа и тексты в уже созданных виджетах панели.
        Не пересоздаёт layout — нет мигания.
        """
        if not self._current_id:
            return
        canvas = self._store.active_canvas
        if not canvas:
            return
        obj = canvas.objects.get(self._current_id)
        if not obj:
            return

        # Обходим layout и обновляем виджеты по их позиции
        # Проще всего — полный rebuild только если тип объекта поменялся
        # (на практике тип не меняется, поэтому достаточно rebuild при selection change)
        # Однако значения X/Y/W/H должны обновляться при drag.
        # Делаем partial rebuild только если panel пустая или другой объект
        self._updating = True
        try:
            self._refresh_transform_spinboxes(obj)
        finally:
            self._updating = False

    def _refresh_transform_spinboxes(self, obj):
        """Обновляет значения спиннеров трансформации без пересоздания."""
        t = obj.transform
        # Ищем PropRow с QDoubleSpinBox в obj_layout
        spin_idx = 0
        for i in range(self._obj_layout.count()):
            item = self._obj_layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if w is None:
                continue
            # PropRow содержит QLabel + spin
            from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
            spins = w.findChildren(QDoubleSpinBox)
            if not spins:
                spins = w.findChildren(QSpinBox)
            if not spins:
                continue
            spin = spins[0]
            # Порядок спиннеров в transform: X, Y, W, H, Rot, Opacity
            vals = [t.x, t.y, t.width, t.height, t.rotation, t.opacity]
            if spin_idx < len(vals):
                if abs(spin.value() - vals[spin_idx]) > 0.001:
                    spin.blockSignals(True)
                    spin.setValue(vals[spin_idx])
                    spin.blockSignals(False)
                spin_idx += 1

    # -----------------------------------------------------------------------
    # Canvas settings tab
    # -----------------------------------------------------------------------

    def _build_canvas_tab(self):
        self._canvas_layout.addWidget(SectionHeader("Size"))

        self._cw_spin = _ispin(1, 99999)
        self._cw_spin.valueChanged.connect(self._on_canvas_size_changed)
        self._canvas_layout.addWidget(PropRow("Width", self._cw_spin))

        self._ch_spin = _ispin(1, 99999)
        self._ch_spin.valueChanged.connect(self._on_canvas_size_changed)
        self._canvas_layout.addWidget(PropRow("Height", self._ch_spin))

        # Presets
        presets_row = QWidget()
        pl = QHBoxLayout(presets_row)
        pl.setContentsMargins(8, 2, 8, 6)
        pl.setSpacing(4)
        for label, w, h in [("FHD", 1920, 1080), ("4K", 3840, 2160),
                              ("A4", 2480, 3508), ("Square", 1080, 1080)]:
            b = _btn(label)
            b.setFixedHeight(24)
            b.setStyleSheet(_BTN_SS + "QPushButton{padding:2px 8px;font-size:10px;}")
            _w, _h = w, h
            b.clicked.connect(lambda _, w=_w, h=_h: self._apply_canvas_size(w, h))
            pl.addWidget(b)
        pl.addStretch()
        self._canvas_layout.addWidget(presets_row)

        self._canvas_layout.addWidget(SectionHeader("Background"))

        self._bg_color_btn = ColorButton("#FFFFFF")
        self._bg_color_btn.color_picked.connect(self._on_bg_color_pick)
        self._canvas_layout.addWidget(PropRow("Color", self._bg_color_btn))

        self._bg_image_edit = _line()
        self._bg_image_edit.setReadOnly(True)
        self._bg_image_edit.setPlaceholderText("No image")
        self._canvas_layout.addWidget(PropRow("Image", self._bg_image_edit))

        img_row = QWidget()
        il = QHBoxLayout(img_row)
        il.setContentsMargins(8, 2, 8, 4)
        il.addStretch()
        il.addWidget(_btn("Browse…", self._on_bg_image_browse))
        il.addWidget(_btn("Clear", self._on_bg_image_clear))
        self._canvas_layout.addWidget(img_row)

        self._canvas_layout.addWidget(SectionHeader("Name"))
        self._canvas_name_edit = _line()
        self._canvas_name_edit.editingFinished.connect(self._on_canvas_name_changed)
        self._canvas_layout.addWidget(PropRow("Name", self._canvas_name_edit))

        self._canvas_layout.addStretch()
        self._refresh_canvas_tab()

    def _refresh_canvas_tab(self):
        canvas = self._store.active_canvas
        if not canvas:
            return
        self._updating = True
        self._cw_spin.setValue(canvas.width)
        self._ch_spin.setValue(canvas.height)
        self._bg_color_btn.set_color(canvas.background)
        bg_img = getattr(canvas, "background_image", "")
        self._bg_image_edit.setText(bg_img or "")
        self._canvas_name_edit.setText(canvas.name)
        self._updating = False

    def _on_canvas_size_changed(self):
        if self._updating:
            return
        canvas = self._store.active_canvas
        if canvas:
            canvas.width  = self._cw_spin.value()
            canvas.height = self._ch_spin.value()
            self._store.document_changed.emit()

    def _apply_canvas_size(self, w: int, h: int):
        canvas = self._store.active_canvas
        if canvas:
            canvas.width  = w
            canvas.height = h
            self._store.document_changed.emit()
            self._updating = True
            self._cw_spin.setValue(w)
            self._ch_spin.setValue(h)
            self._updating = False

    def _on_bg_color_pick(self, color: str):
        """Вызывается когда пользователь выбрал цвет в ColorButton."""
        canvas = self._store.active_canvas
        if not canvas:
            return
        canvas.background = color
        self._store.document_changed.emit()

    def _on_bg_image_browse(self):
        canvas = self._store.active_canvas
        if not canvas:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            canvas.background_image = path
            self._bg_image_edit.setText(path)
            self._store.document_changed.emit()

    def _on_bg_image_clear(self):
        canvas = self._store.active_canvas
        if canvas:
            canvas.background_image = ""
            self._bg_image_edit.setText("")
            self._store.document_changed.emit()

    def _on_canvas_name_changed(self):
        if self._updating:
            return
        canvas = self._store.active_canvas
        if canvas:
            canvas.name = self._canvas_name_edit.text()
            self._store.document_changed.emit()

    # -----------------------------------------------------------------------
    # Object tab
    # -----------------------------------------------------------------------

    def _clear_obj_layout(self):
        # setParent(None) удаляет виджет синхронно (в отличие от deleteLater)
        # и немедленно убирает его из layout — без артефактов
        while self._obj_layout.count():
            item = self._obj_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _show_empty(self):
        self._clear_obj_layout()
        lbl = QLabel("No selection")
        lbl.setStyleSheet("font-size:12px;padding:20px;")
        lbl.setAlignment(Qt.AlignCenter)
        self._obj_layout.addWidget(lbl)
        self._obj_layout.addStretch()

    def _rebuild_obj_panel(self):
        if not self._current_id:
            self._show_empty()
            return
        canvas = self._store.active_canvas
        if not canvas:
            self._show_empty()
            return
        obj = canvas.objects.get(self._current_id)
        if not obj:
            self._show_empty()
            return

        self._updating = True
        self._clear_obj_layout()
        self._build_for_object(obj)
        self._obj_layout.addStretch()
        self._updating = False

    def _build_for_object(self, obj: ObjectState):
        self._obj_layout.addWidget(SectionHeader("Object"))
        self._add_common(obj)
        self._obj_layout.addWidget(SectionHeader("Transform"))
        self._add_transform(obj)
        if obj.type in (ObjectType.RECT, ObjectType.ELLIPSE):
            self._obj_layout.addWidget(SectionHeader("Appearance"))
            self._add_shape_style(obj)
        elif obj.type == ObjectType.TEXT:
            self._obj_layout.addWidget(SectionHeader("Text"))
            self._add_text_content(obj)
            self._obj_layout.addWidget(SectionHeader("Font"))
            self._add_text_style(obj)
        elif obj.type == ObjectType.IMAGE:
            self._obj_layout.addWidget(SectionHeader("Image"))
            self._add_image(obj)
        elif obj.type == ObjectType.BEZIER:
            self._obj_layout.addWidget(SectionHeader("Bezier Curve"))
            self._add_bezier(obj)

    # -----------------------------------------------------------------------
    # Common
    # -----------------------------------------------------------------------

    def _add_common(self, obj: ObjectState):
        name_edit = _line()
        name_edit.setText(obj.name)
        name_edit.editingFinished.connect(
            lambda: self._commit("name", name_edit.text()))
        self._obj_layout.addWidget(PropRow("Name", name_edit))

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 4, 8, 4)
        rl.setSpacing(16)

        vis = QCheckBox("Visible")
        
        vis.setChecked(obj.visible)
        # Используем checkStateChanged — передаёт Qt.CheckState
        vis.checkStateChanged.connect(
            lambda state: self._commit("visible", state == Qt.Checked))

        lock = QCheckBox("Locked")
        
        lock.setChecked(obj.locked)
        lock.checkStateChanged.connect(
            lambda state: self._commit("locked", state == Qt.Checked))

        rl.addWidget(vis)
        rl.addWidget(lock)
        rl.addStretch()
        self._obj_layout.addWidget(row)

    # -----------------------------------------------------------------------
    # Transform
    # -----------------------------------------------------------------------

    def _add_transform(self, obj: ObjectState):
        t = obj.transform

        for label, attr, val in [
            ("X",  "transform.x",       t.x),
            ("Y",  "transform.y",       t.y),
            ("W",  "transform.width",   t.width),
            ("H",  "transform.height",  t.height),
            ("Rot°", "transform.rotation", t.rotation),
        ]:
            s = _spin(-99999, 99999)
            s.setValue(val)
            _attr = attr
            s.valueChanged.connect(
                lambda v, a=_attr: self._commit(a, v))
            self._obj_layout.addWidget(PropRow(label, s))

        op = _spin(0, 1, dec=2, step=0.05)
        op.setValue(t.opacity)
        op.valueChanged.connect(lambda v: self._commit("transform.opacity", v))
        self._obj_layout.addWidget(PropRow("Opacity", op))

    # -----------------------------------------------------------------------
    # Shape
    # -----------------------------------------------------------------------

    def _add_shape_style(self, obj: ObjectState):
        s = obj.style

        fill = ColorButton(s.fill_color)
        self._pick_color(fill, "style.fill_color")
        self._obj_layout.addWidget(PropRow("Fill", fill))

        stroke = ColorButton(s.stroke_color)
        self._pick_color(stroke, "style.stroke_color")
        self._obj_layout.addWidget(PropRow("Stroke", stroke))

        sw = _spin(0, 50)
        sw.setValue(s.stroke_width)
        sw.valueChanged.connect(lambda v: self._commit("style.stroke_width", v))
        self._obj_layout.addWidget(PropRow("Stroke W", sw))

        if obj.type == ObjectType.RECT:
            cr = _spin(0, 500, dec=0)
            cr.setValue(s.corner_radius)
            cr.valueChanged.connect(lambda v: self._commit("style.corner_radius", v))
            self._obj_layout.addWidget(PropRow("Radius", cr))

    # -----------------------------------------------------------------------
    # Text
    # -----------------------------------------------------------------------

    def _add_text_content(self, obj: ObjectState):
        payload = obj.payload
        if not isinstance(payload, TextPayload):
            return
        te = QTextEdit()
        te.setPlainText(payload.text)
        te.setFixedHeight(80)
        te.setStyleSheet("font-size:11px;padding:4px;")
        te.textChanged.connect(
            lambda: self._commit("payload_text", te.toPlainText()))
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(8, 2, 8, 2)
        wl.addWidget(te)
        self._obj_layout.addWidget(w)

    def _add_text_style(self, obj: ObjectState):
        s = obj.style

        tc = ColorButton(s.text_color)
        self._pick_color(tc, "style.text_color")
        self._obj_layout.addWidget(PropRow("Color", tc))

        fs = _ispin(4, 500)
        fs.setValue(s.font_size)
        fs.valueChanged.connect(lambda v: self._commit("style.font_size", v))
        self._obj_layout.addWidget(PropRow("Size", fs))

        ff = _line()
        ff.setText(s.font_family)
        ff.editingFinished.connect(
            lambda: self._commit("style.font_family", ff.text()))
        self._obj_layout.addWidget(PropRow("Font", ff))

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 4, 8, 4)
        rl.setSpacing(16)

        bold = QCheckBox("Bold")
        
        bold.setChecked(s.bold)
        bold.checkStateChanged.connect(
            lambda state: self._commit("style.bold", state == Qt.Checked))

        italic = QCheckBox("Italic")
        
        italic.setChecked(s.italic)
        italic.checkStateChanged.connect(
            lambda state: self._commit("style.italic", state == Qt.Checked))

        rl.addWidget(bold); rl.addWidget(italic); rl.addStretch()
        self._obj_layout.addWidget(row)

    # -----------------------------------------------------------------------
    # Image
    # -----------------------------------------------------------------------

    def _add_bezier(self, obj: ObjectState):
        from domain.models import BezierPayload
        payload = obj.payload
        if not isinstance(payload, BezierPayload):
            return

        s = obj.style

        # Stroke color + width
        stroke = ColorButton(s.stroke_color)
        self._pick_color(stroke, "style.stroke_color")
        self._obj_layout.addWidget(PropRow("Color", stroke))

        sw = _spin(0.5, 50)
        sw.setValue(s.stroke_width)
        sw.valueChanged.connect(lambda v: self._commit("style.stroke_width", v))
        self._obj_layout.addWidget(PropRow("Width", sw))

        # Closed toggle
        from PySide6.QtWidgets import QCheckBox
        closed_cb = QCheckBox("Closed path")
        closed_cb.setChecked(payload.closed)
        closed_cb.checkStateChanged.connect(
            lambda state: self._commit_bezier_closed(obj.id, state))
        self._obj_layout.addWidget(closed_cb)

        # Point info (read-only summary — editing done on canvas with BezierTool)
        self._obj_layout.addWidget(SectionHeader("Points"))
        n = len(payload.points)
        pts_label = "point" if n == 1 else "points"
        info = QLabel(
            f"{n} anchor {pts_label}\n"
            "Select \u301c Bezier tool to edit on canvas.\n"
            "Click=add/select  |  Delete=remove  |  Shift+click=corner/smooth"
        )
        info.setStyleSheet("font-size:10px;padding:4px 8px;")
        info.setWordWrap(True)
        self._obj_layout.addWidget(info)

        # List anchor positions (read-only)
        for i, pt in enumerate(payload.points):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 1, 8, 1)
            rl.setSpacing(4)
            lbl = QLabel(f"P{i}")
            lbl.setFixedWidth(24)
            lbl.setStyleSheet("font-size:10px;")
            sx = _spin(-99999, 99999, dec=1)
            sx.setValue(pt.x)
            sx.valueChanged.connect(
                lambda v, idx=i: self._commit_bezier_point(obj.id, idx, "x", v))
            sy = _spin(-99999, 99999, dec=1)
            sy.setValue(pt.y)
            sy.valueChanged.connect(
                lambda v, idx=i: self._commit_bezier_point(obj.id, idx, "y", v))
            rl.addWidget(lbl)
            rl.addWidget(QLabel("X")); rl.addWidget(sx, 1)
            rl.addWidget(QLabel("Y")); rl.addWidget(sy, 1)
            self._obj_layout.addWidget(row)

    def _commit_bezier_closed(self, obj_id: str, state):
        from PySide6.QtCore import Qt as _Qt
        canvas = self._store.active_canvas
        if not canvas: return
        obj = canvas.objects.get(obj_id)
        if not obj: return
        obj.payload.closed = (state == _Qt.Checked)
        self._store.document_changed.emit()

    def _commit_bezier_point(self, obj_id: str, idx: int, axis: str, value: float):
        if self._updating: return
        canvas = self._store.active_canvas
        if not canvas: return
        obj = canvas.objects.get(obj_id)
        if not obj or idx >= len(obj.payload.points): return
        setattr(obj.payload.points[idx], axis, value)
        self._store.document_changed.emit()

    def _add_image(self, obj: ObjectState):
        payload = obj.payload
        if not isinstance(payload, ImagePayload):
            return
        path_edit = _line()
        path_edit.setReadOnly(True)
        path_edit.setText(payload.source_path)
        path_edit.setStyleSheet(path_edit.styleSheet() + "color:#888899;")
        self._obj_layout.addWidget(PropRow("Path", path_edit))

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 2, 8, 4)
        rl.addStretch()

        def browse():
            p, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
            if p:
                path_edit.setText(p)
                self._commit("payload_image", p)

        rl.addWidget(_btn("Browse…", browse))
        self._obj_layout.addWidget(row)

    # -----------------------------------------------------------------------
    # Color picker helper
    # -----------------------------------------------------------------------

    def _pick_color(self, btn: ColorButton, key: str):
        """Подключается к color_picked сигналу кнопки."""
        # Отсоединяем старые коннекты чтобы не дублировать
        try:
            btn.color_picked.disconnect()
        except (RuntimeError, TypeError):
            pass
        btn.color_picked.connect(lambda c: self._commit(key, c))

    # -----------------------------------------------------------------------
    # Commit
    # -----------------------------------------------------------------------

    def _commit(self, key: str, value):
        if self._updating or not self._current_id:
            return
        self._controller.update_properties(self._current_id, {key: value})
