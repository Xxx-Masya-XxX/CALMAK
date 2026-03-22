"""
MainWindow — главное окно редактора.

Тулбары — QToolBar, можно перетаскивать и докировать:
  • "Tools"   — инструменты (Move/Rotate/Scale)
  • "Create"  — создание объектов
  • "File"    — файловые операции + undo/redo

Меню Settings:
  • Themes  — Dark / Light / Midnight / Warm
  • Hotkeys — настройка горячих клавиш для create-объектов
"""
from __future__ import annotations
import json, os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import (QAction, QKeySequence, QColor, QFont,
                            QKeyEvent)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QToolBar, QDockWidget, QLabel, QFrame, QPushButton,
    QSizePolicy, QApplication, QInputDialog, QButtonGroup,
    QDialog, QDialogButtonBox, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QKeySequenceEdit,
    QTabWidget, QFormLayout, QGroupBox, QMessageBox, QStatusBar,
    QAbstractItemView
)

from state.editor_store import EditorStore
from controllers.editor_controller import EditorController
from tools.tool_manager import (ToolManager, TOOL_MOVE, TOOL_ROTATE, TOOL_SCALE, TOOL_BEZIER)
from ui.scene.scene_view import SceneView
from ui.panels.element_tree_panel import ElementTreePanel
from ui.panels.properties_panel import PropertiesPanel
from ui.constants import C, menu_stylesheet
from ui.theme import THEMES, build_stylesheet, theme_manager
from ui.context_toolbar import ContextToolbarManager
from ui.icons import get_icon



# ---------------------------------------------------------------------------
# Default hotkeys for "Create" actions
# ---------------------------------------------------------------------------

DEFAULT_HOTKEYS: dict[str, str] = {
    # Create objects (no defaults — user assigns)
    "add_rect":     "",
    "add_ellipse":  "",
    "add_triangle": "",
    "add_text":     "",
    "add_image":    "",
    "add_bezier":   "",
    # Tools (defaults provided)
    "tool_move":    "V",
    "tool_rotate":  "R",
    "tool_scale":   "E",
    "tool_bezier":  "B",
}


# ---------------------------------------------------------------------------
# SettingsDialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """
    Диалог настроек:
      • Вкладка "Appearance" — выбор темы
      • Вкладка "Hotkeys"    — назначение горячих клавиш для создания объектов
    """

    def __init__(self, current_theme: str,
                 hotkeys: dict[str, str],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(480, 380)
        self._chosen_theme = current_theme
        self._hotkeys      = dict(hotkeys)

        self._build_ui()

    # ---- UI ----------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(8)

        tabs = QTabWidget()
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._hotkeys_tab(),    "Hotkeys")
        root.addWidget(tabs)

        bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        root.addWidget(bbox)

    def _appearance_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 16, 12, 8)
        lay.setSpacing(12)

        grp = QGroupBox("Theme")
        gl  = QVBoxLayout(grp)

        lbl = QLabel("Choose application color theme:")
        lbl.setWordWrap(True)
        gl.addWidget(lbl)

        self._theme_combo = QComboBox()
        for name in THEMES:
            self._theme_combo.addItem(name)
        self._theme_combo.setCurrentText(self._chosen_theme)
        self._theme_combo.currentTextChanged.connect(self._on_theme_preview)
        gl.addWidget(self._theme_combo)

        preview_lbl = QLabel(
            "Preview changes live — cancel to discard.")
        preview_lbl.setStyleSheet("font-size:10px;")
        gl.addWidget(preview_lbl)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    def _hotkeys_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 16, 12, 8)
        lay.setSpacing(8)

        info = QLabel(
            "Assign optional keyboard shortcuts for creating objects.\n"
            "Leave empty to disable. Press a key combination in the field.")
        info.setWordWrap(True)
        info.setStyleSheet("font-size:10px;")
        lay.addWidget(info)

        self._hotkey_table = QTableWidget(len(self._hotkeys), 2)
        self._hotkey_table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self._hotkey_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self._hotkey_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        self._hotkey_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._hotkey_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._hotkey_table.verticalHeader().setVisible(False)

        # All configurable actions: tools first, then create objects
        _labels = {
            "tool_move":    "Tool: Move",
            "tool_rotate":  "Tool: Rotate",
            "tool_scale":   "Tool: Scale",
            "tool_bezier":  "Tool: Bezier Path",
            "add_rect":     "Add Rectangle",
            "add_ellipse":  "Add Ellipse",
            "add_triangle": "Add Triangle",
            "add_text":     "Add Text",
            "add_image":    "Add Image",
            "add_bezier":   "Add Bezier Curve",
        }
        # Resize table to fit all actions
        self._hotkey_table.setRowCount(len(_labels))
        self._key_edits: dict[str, QKeySequenceEdit] = {}

        for row, (action_id, label) in enumerate(_labels.items()):
            name_item = QTableWidgetItem(label)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self._hotkey_table.setItem(row, 0, name_item)

            edit = QKeySequenceEdit(QKeySequence(self._hotkeys.get(action_id, "")))
            self._hotkey_table.setCellWidget(row, 1, edit)
            self._key_edits[action_id] = edit

        lay.addWidget(self._hotkey_table)

        clear_btn = QPushButton("Clear All Shortcuts")
        clear_btn.setFixedWidth(160)
        clear_btn.clicked.connect(self._clear_all_hotkeys)
        lay.addWidget(clear_btn, alignment=Qt.AlignLeft)
        return w

    # ---- Slots -------------------------------------------------------------

    def _on_theme_preview(self, theme_name: str):
        self._chosen_theme = theme_name
        # Live preview через theme_manager — обновляет всё включая SceneView
        theme_manager.apply(theme_name)

    def _clear_all_hotkeys(self):
        for edit in self._key_edits.values():
            edit.setKeySequence(QKeySequence())

    # ---- Result ------------------------------------------------------------

    def get_theme(self) -> str:
        return self._chosen_theme

    def get_hotkeys(self) -> dict[str, str]:
        return {
            action_id: edit.keySequence().toString()
            for action_id, edit in self._key_edits.items()
        }


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    # ---- Init --------------------------------------------------------------

    def __init__(self):
        super().__init__()
        self._store        = EditorStore()
        self._controller   = EditorController(self._store)
        self._tool_manager = ToolManager()
        self._hotkeys      = dict(DEFAULT_HOTKEYS)

        # Load saved settings
        self._settings = QSettings("CanvasEditor", "CanvasEditor")
        saved_theme = self._settings.value("theme", "Dark")
        saved_hk    = self._settings.value("hotkeys", None)
        if saved_hk:
            try:
                self._hotkeys.update(json.loads(saved_hk))
            except Exception:
                pass

        self.setWindowTitle("Canvas Editor")
        self.resize(1480, 920)

        # Apply saved theme — обновляет C, QApplication stylesheet и все подписчики
        theme_manager.apply(saved_theme)

        self._build_ui()
        self._apply_hotkeys()

        # Restore window geometry and toolbar/dock layout from last session
        geom  = self._settings.value("geometry")
        state = self._settings.value("windowState")
        if geom:
            self.restoreGeometry(geom)
        if state:
            self.restoreState(state)

        self._create_demo()

    # ---- Build UI ----------------------------------------------------------

    def _build_ui(self):
        # Подписываем кеш иконок на смену темы (автосброс)
        from ui.icons import setup_theme_auto_refresh
        setup_theme_auto_refresh()

        self._setup_menu()
        self._setup_toolbars()   # ← QToolBar (перемещаемые)
        self._setup_docks()      # ← Layers + Properties
        self._setup_central()    # ← SceneView
        self._setup_status()
        self._connect_store()

    # ---- Menu --------------------------------------------------------------

    def _setup_menu(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu("File")
        self._act(fm, "New",            "Ctrl+N",
                  lambda: self._controller.new_document(self))
        self._act(fm, "Open…",          "Ctrl+O",
                  lambda: self._controller.load_document(self))
        fm.addSeparator()
        self._act(fm, "Save",           "Ctrl+S",
                  lambda: self._controller.save_document(self))
        fm.addSeparator()
        self._act(fm, "Export Canvas…", "Ctrl+E",
                  lambda: self._controller.export_canvas(self))
        fm.addSeparator()
        self._act(fm, "Quit", "Ctrl+Q", QApplication.quit)

        # Edit
        em = mb.addMenu("Edit")
        self._act(em, "Undo",       "Ctrl+Z",       self._controller.undo)
        self._act(em, "Redo",       "Ctrl+Shift+Z", self._controller.redo)
        em.addSeparator()
        self._act(em, "Duplicate",  "Ctrl+D",
                  self._controller.duplicate_selected)
        self._act(em, "Delete",     "Delete",
                  self._controller.delete_selected)
        em.addSeparator()
        self._act(em, "Select All", "Ctrl+A", self._select_all)

        # Object
        om = mb.addMenu("Object")
        self._act(om, "Add Rect",     None,
                  lambda: self._controller.add_rect())
        self._act(om, "Add Ellipse",  None,
                  lambda: self._controller.add_ellipse())
        self._act(om, "Add Triangle", None,
                  lambda: self._controller.add_triangle())
        self._act(om, "Add Text",     None,
                  lambda: self._controller.add_text())
        self._act(om, "Add Image",    None,
                  lambda: self._controller.add_image_from_dialog(self))
        om.addSeparator()
        self._act(om, "Bring Forward", "Ctrl+]", self._bring_forward)
        self._act(om, "Send Backward", "Ctrl+[", self._send_backward)

        # Align
        alm = mb.addMenu("Align")
        for mode, label in [
            ("left",     "Align Left"),
            ("right",    "Align Right"),
            ("top",      "Align Top"),
            ("bottom",   "Align Bottom"),
            ("center_h", "Center Horizontal"),
            ("center_v", "Center Vertical"),
        ]:
            self._act(alm, label, None,
                      lambda _, m=mode: self._controller.align_objects(m))

        # Settings  ← новое меню
        sm = mb.addMenu("Settings")
        self._act(sm, "Preferences…", "Ctrl+,", self._open_settings)
        sm.addSeparator()
        # Quick theme switching
        for theme_name in THEMES:
            _t = theme_name
            self._act(sm, f"Theme: {theme_name}", None,
                      lambda _, t=_t: self._apply_theme(t))

        # View
        vm = mb.addMenu("View")
        self._act(vm, "Fit Canvas", "Ctrl+0",
                  lambda: self._scene_view.fit_view()
                  if hasattr(self, "_scene_view") else None)
        self._act(vm, "Zoom In",    "Ctrl+=",
                  lambda: self._scene_view.zoom_in()
                  if hasattr(self, "_scene_view") else None)
        self._act(vm, "Zoom Out",   "Ctrl+-",
                  lambda: self._scene_view.zoom_out()
                  if hasattr(self, "_scene_view") else None)

    def _act(self, menu, label, shortcut, slot) -> QAction:
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if slot:
            a.triggered.connect(slot)
        menu.addAction(a)
        return a

    # ---- Toolbars ----------------------------------------------------------

    def _setup_toolbars(self):
        """
        Три QToolBar — все можно перетаскивать и докировать.
        По умолчанию горизонтальные, расположены сверху.
        """
        self._build_file_toolbar()
        self._build_tools_toolbar()
        self._build_create_toolbar()

    # ---- File toolbar

    def _build_file_toolbar(self):
        tb = QToolBar("File & Edit", self)
        tb.setObjectName("tb_file")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)   # только иконки
        self.addToolBar(Qt.TopToolBarArea, tb)

        def add_svg(icon_name: str, tip: str, slot,
                    checkable: bool = False) -> QAction:
            a = QAction(self)
            a.setIcon(get_icon(icon_name, 20))
            a.setToolTip(tip)
            a.setCheckable(checkable)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        add_svg("new",    "New document  (Ctrl+N)",
                lambda: self._controller.new_document(self))
        add_svg("open",   "Open project  (Ctrl+O)",
                lambda: self._controller.load_document(self))
        add_svg("save",   "Save project  (Ctrl+S)",
                lambda: self._controller.save_document(self))
        add_svg("export", "Export canvas  (Ctrl+E)",
                lambda: self._controller.export_canvas(self))
        tb.addSeparator()

        self._undo_action = add_svg("undo", "Undo  (Ctrl+Z)",
                                    self._controller.undo)
        self._redo_action = add_svg("redo", "Redo  (Ctrl+Shift+Z)",
                                    self._controller.redo)
        self._undo_action.setEnabled(False)
        self._redo_action.setEnabled(False)
        tb.addSeparator()

        # Canvas selector (остаётся с текстом — это комбобокс)
        self._canvas_combo = QComboBox()
        self._canvas_combo.setMinimumWidth(150)
        self._canvas_combo.setMaximumWidth(220)
        self._canvas_combo.currentIndexChanged.connect(self._on_canvas_combo)
        tb.addWidget(self._canvas_combo)

        self._add_canvas_action = add_svg(
            "add_canvas", "Add new canvas", self._add_canvas_dialog)

        tb.addSeparator()
        self._settings_action = add_svg(
            "settings", "Settings  (Ctrl+,)", self._open_settings)

        # Сохраняем все svg-actions для рефреша при смене темы
        self._file_toolbar_actions = {
            "new":        tb.actions()[0],
            "open":       tb.actions()[1],
            "save":       tb.actions()[2],
            "export":     tb.actions()[3],
        }

    # ---- Tools toolbar (Move / Rotate / Scale)

    def _build_tools_toolbar(self):
        tb = QToolBar("Transform Tools", self)
        tb.setObjectName("tb_tools")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)  # только иконки
        self.addToolBar(Qt.TopToolBarArea, tb)

        # (tool_id, icon_name, label, hotkey_id)
        tools = [
            (TOOL_MOVE,   "move",     "Move",        "tool_move"),
            (TOOL_ROTATE, "rotate",   "Rotate",      "tool_rotate"),
            (TOOL_SCALE,  "scale",    "Scale",       "tool_scale"),
            (TOOL_BEZIER, "bezier",   "Bezier Path", "tool_bezier"),
        ]

        self._tool_actions: dict[str, QAction] = {}
        self._tool_hotkey_ids: dict[str, str] = {
            TOOL_MOVE:   "tool_move",
            TOOL_ROTATE: "tool_rotate",
            TOOL_SCALE:  "tool_scale",
            TOOL_BEZIER: "tool_bezier",
        }

        for tool_id, icon_name, label, hk_id in tools:
            default_key = DEFAULT_HOTKEYS.get(hk_id, "")
            tip = f"{label}  ({default_key})" if default_key else label
            a = QAction(self)
            a.setIcon(get_icon(icon_name, 20))
            a.setToolTip(tip)
            a.setCheckable(True)
            a.setData(tool_id)
            a.triggered.connect(lambda checked, tid=tool_id:
                                 self._tool_manager.set_tool(tid))
            tb.addAction(a)
            self._tool_actions[tool_id] = a

        self._tool_actions[TOOL_MOVE].setChecked(True)
        self._tool_manager.tool_changed.connect(self._on_tool_changed)

        tb.addSeparator()
        af = QAction(self)
        af.setIcon(get_icon("forward", 20))
        af.setToolTip("Bring Forward  (Ctrl+])")
        af.triggered.connect(self._bring_forward)
        tb.addAction(af)

        ab = QAction(self)
        ab.setIcon(get_icon("backward", 20))
        ab.setToolTip("Send Backward  (Ctrl+[)")
        ab.triggered.connect(self._send_backward)
        tb.addAction(ab)

    # ---- Create toolbar

    def _build_create_toolbar(self):
        tb = QToolBar("Create Objects", self)
        tb.setObjectName("tb_create")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)  # только иконки, без текста
        self.addToolBar(Qt.TopToolBarArea, tb)

        self._create_actions: dict[str, QAction] = {}
        # Store labels for tooltip generation in _apply_hotkeys
        self._create_labels: dict[str, str] = {}

        # (action_id, icon_name, display_label)
        objects = [
            ("add_rect",     "rect",     "Rectangle"),
            ("add_ellipse",  "ellipse",  "Ellipse"),
            ("add_triangle", "triangle", "Triangle"),
            ("add_text",     "text",     "Text"),
            ("add_image",    "image",    "Image"),
            ("add_bezier",   "bezier",   "Bezier Curve"),
        ]
        for action_id, icon_name, label in objects:
            slot = getattr(self, f"_{action_id}_action")
            a = QAction(self)
            a.setIcon(get_icon(icon_name, 20))
            # Tooltip will be set properly by _apply_hotkeys after build
            a.setToolTip(f"Add {label}")
            a.triggered.connect(slot)
            tb.addAction(a)
            self._create_actions[action_id] = a
            self._create_labels[action_id] = f"Add {label}"

    def _make_action(self, text: str, tip: str, slot) -> QAction:
        a = QAction(text, self)
        a.setToolTip(tip)
        a.triggered.connect(slot)
        return a

    # Create action slots
    def _add_rect_action(self):     self._controller.add_rect()
    def _add_ellipse_action(self):  self._controller.add_ellipse()
    def _add_triangle_action(self): self._controller.add_triangle()
    def _add_text_action(self):     self._controller.add_text()
    def _add_image_action(self):
        self._controller.add_image_from_dialog(self)

    def _add_bezier_action(self):
        self._controller.add_bezier()

    # ---- Docks -------------------------------------------------------------

    def _setup_docks(self):
        # Properties — right
        self._props_panel = PropertiesPanel(self._store, self._controller)
        d_props = QDockWidget("Properties", self)
        d_props.setObjectName("dock_properties")
        d_props.setWidget(self._props_panel)
        d_props.setMinimumWidth(250)
        self.addDockWidget(Qt.RightDockWidgetArea, d_props)

        # Layers — right, below Properties
        self._tree_panel = ElementTreePanel(self._store, self._controller)
        d_layers = QDockWidget("Layers", self)
        d_layers.setObjectName("dock_layers")
        d_layers.setWidget(self._tree_panel)
        d_layers.setMinimumWidth(220)
        self.addDockWidget(Qt.RightDockWidgetArea, d_layers)
        self.splitDockWidget(d_props, d_layers, Qt.Vertical)

    # ---- Central -----------------------------------------------------------

    def _setup_central(self):
        self._scene_view = SceneView(self._store, self._controller,
                                     self._tool_manager)

        # Wrapper: context toolbar + scene
        wrapper = QWidget()
        wrapper.setObjectName("scene_wrapper")
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self._ctx_toolbar = ContextToolbarManager(
            self._store, self._controller, self._tool_manager, wrapper)
        vbox.addWidget(self._ctx_toolbar)
        vbox.addWidget(self._scene_view)

        self.setCentralWidget(wrapper)
        self._refresh_canvas_combo()

    # ---- Status bar --------------------------------------------------------

    def _setup_status(self):
        sb = self.statusBar()
        self._status_lbl = QLabel("Ready")
        sb.addWidget(self._status_lbl)
        self._sel_lbl  = QLabel("")
        sb.addPermanentWidget(self._sel_lbl)
        self._tool_lbl = QLabel("  Tool: Move")
        sb.addPermanentWidget(self._tool_lbl)
        self._zoom_lbl = QLabel("  100%")
        sb.addPermanentWidget(self._zoom_lbl)

    # ---- Store connections -------------------------------------------------

    def _connect_store(self):
        self._store.document_changed.connect(self._on_doc_changed)
        self._store.selection_changed.connect(
            lambda ids, aid: self._update_status())
        self._store.history_changed.connect(self._on_history_changed)
        self._store.title_changed.connect(self.setWindowTitle)
        self._store.canvas_switched.connect(
            lambda _: self._refresh_canvas_combo())
        # Update zoom label when view transforms
        # We use a timer to poll (QGraphicsView has no zoom signal)
        from PySide6.QtCore import QTimer
        self._zoom_timer = QTimer(self)
        self._zoom_timer.timeout.connect(self._update_zoom_label)
        self._zoom_timer.start(200)  # poll every 200ms

    def _on_doc_changed(self):
        self._refresh_canvas_combo()
        self._update_status()
        if hasattr(self, '_ctx_toolbar'):
            self._ctx_toolbar.refresh_active()

    def _on_history_changed(self, can_undo: bool, can_redo: bool):
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)
        h = self._store.history
        self._undo_action.setToolTip(
            f"Undo: {h.undo_description}" if can_undo else "Nothing to undo")
        self._redo_action.setToolTip(
            f"Redo: {h.redo_description}" if can_redo else "Nothing to redo")

    def _on_tool_changed(self, tool_id: str):
        for tid, act in self._tool_actions.items():
            act.setChecked(tid == tool_id)
        names = {TOOL_MOVE: "Move", TOOL_ROTATE: "Rotate",
                 TOOL_SCALE: "Scale", TOOL_BEZIER: "Bezier Path"}
        self._tool_lbl.setText(f"  Tool: {names.get(tool_id, tool_id)}")

    def _update_zoom_label(self):
        if hasattr(self, "_scene_view") and hasattr(self, "_zoom_lbl"):
            pct = self._scene_view.current_zoom_percent()
            self._zoom_lbl.setText(f"  {pct}%")

    def _update_status(self):
        canvas = self._store.active_canvas
        if canvas:
            n   = len(canvas.objects)
            sel = len(self._store.selection.selected_ids)
            self._status_lbl.setText(
                f"{canvas.name}  •  {n} object{'s' if n != 1 else ''}"
                f"  •  {canvas.width}×{canvas.height}")
            self._sel_lbl.setText(f"  {sel} selected" if sel else "")

    # ---- Canvas combo ------------------------------------------------------

    def _refresh_canvas_combo(self):
        self._canvas_combo.blockSignals(True)
        self._canvas_combo.clear()
        doc = self._store.document
        for cid, canvas in doc.canvases.items():
            self._canvas_combo.addItem(canvas.name, cid)
        for i in range(self._canvas_combo.count()):
            if self._canvas_combo.itemData(i) == doc.active_canvas_id:
                self._canvas_combo.setCurrentIndex(i)
                break
        self._canvas_combo.blockSignals(False)

    def _on_canvas_combo(self, idx: int):
        cid = self._canvas_combo.itemData(idx)
        if cid:
            self._controller.switch_canvas(cid)

    def _add_canvas_dialog(self):
        name, ok = QInputDialog.getText(self, "New Canvas", "Canvas name:")
        if ok and name.strip():
            self._controller.add_canvas(name.strip())

    # ---- Settings ----------------------------------------------------------

    def _open_settings(self):
        dlg = SettingsDialog(theme_manager.name, self._hotkeys, self)
        prev_theme = theme_manager.name

        if dlg.exec():
            self._hotkeys = dlg.get_hotkeys()
            self._apply_theme(dlg.get_theme())
            self._apply_hotkeys()
            self._save_settings()
        else:
            # Restore previous theme if user cancelled
            if prev_theme != theme_manager.name:
                theme_manager.apply(prev_theme)

    def _apply_theme(self, theme_name: str):
        theme_manager.apply(theme_name)
        self._refresh_toolbar_icons()

    def _refresh_toolbar_icons(self):
        """Перерисовывает SVG иконки при смене темы.
        Кеш уже сброшен автоматически через theme_manager.theme_changed.
        get_icon() читает новый C.TEXT и рендерит с правильным цветом.
        """

        # File toolbar
        file_icon_map = [
            ("new",        lambda: self._controller.new_document(self)),
            ("open",       lambda: self._controller.load_document(self)),
            ("save",       lambda: self._controller.save_document(self)),
            ("export",     lambda: self._controller.export_canvas(self)),
            ("undo",       None),
            ("redo",       None),
            ("add_canvas", None),
            ("settings",   None),
        ]
        # Update undo/redo specifically
        if hasattr(self, '_undo_action'):
            self._undo_action.setIcon(get_icon("undo", 20))
        if hasattr(self, '_redo_action'):
            self._redo_action.setIcon(get_icon("redo", 20))
        if hasattr(self, '_add_canvas_action'):
            self._add_canvas_action.setIcon(get_icon("add_canvas", 20))
        if hasattr(self, '_settings_action'):
            self._settings_action.setIcon(get_icon("settings", 20))

        # File toolbar first 4 actions (new/open/save/export)
        from PySide6.QtWidgets import QToolBar
        for tb in self.findChildren(QToolBar):
            if tb.objectName() == "tb_file":
                acts = [a for a in tb.actions() if not a.isSeparator()]
                for i, name in enumerate(["new","open","save","export"]):
                    if i < len(acts):
                        acts[i].setIcon(get_icon(name, 20))
                break

        # Create toolbar
        create_icon_map = {
            "add_rect":     "rect",
            "add_ellipse":  "ellipse",
            "add_triangle": "triangle",
            "add_text":     "text",
            "add_image":    "image",
            "add_bezier":   "bezier",
        }
        for action_id, icon_name in create_icon_map.items():
            a = self._create_actions.get(action_id)
            if a:
                a.setIcon(get_icon(icon_name, 20))

        # Tools toolbar
        tool_icon_map = {
            TOOL_MOVE:   "move",
            TOOL_ROTATE: "rotate",
            TOOL_SCALE:  "scale",
            TOOL_BEZIER: "bezier",
        }
        for tool_id, icon_name in tool_icon_map.items():
            a = self._tool_actions.get(tool_id)
            if a:
                a.setIcon(get_icon(icon_name, 20))

        # Refresh tree panel icons too
        if hasattr(self, '_tree_panel'):
            self._tree_panel._tree.update()

    def _apply_hotkeys(self):
        """Назначает горячие клавиши из self._hotkeys всем действиям."""
        # Create object actions — build rich tooltip: "Add Rectangle  (Ctrl+R)"
        create_ids = [
            "add_rect", "add_ellipse", "add_triangle",
            "add_text", "add_image",  "add_bezier",
        ]
        for action_id in create_ids:
            action = self._create_actions.get(action_id)
            if action is None:
                continue
            seq     = self._hotkeys.get(action_id, "")
            seq_str = QKeySequence(seq).toString() if seq else ""
            action.setShortcut(QKeySequence(seq) if seq else QKeySequence())
            # Use stored label — action.text() is empty for icon-only buttons
            base_label = getattr(self, "_create_labels", {}).get(
                action_id, action_id.replace("_", " ").title())
            tooltip = f"{base_label}  ({seq_str})" if seq_str else base_label
            action.setToolTip(tooltip)

        # Tool actions
        tool_map = {
            "tool_move":   self._tool_actions.get(TOOL_MOVE),
            "tool_rotate": self._tool_actions.get(TOOL_ROTATE),
            "tool_scale":  self._tool_actions.get(TOOL_SCALE),
            "tool_bezier": self._tool_actions.get(TOOL_BEZIER),
        }
        tool_names = {
            "tool_move":   "Move",
            "tool_rotate": "Rotate",
            "tool_scale":  "Scale",
            "tool_bezier": "Bezier Path",
        }
        for hk_id, action in tool_map.items():
            if action is None:
                continue
            seq = self._hotkeys.get(hk_id, "")
            action.setShortcut(QKeySequence(seq) if seq else QKeySequence())
            seq_str = QKeySequence(seq).toString() if seq else ""
            name = tool_names.get(hk_id, hk_id)
            action.setToolTip(f"{name}  ({seq_str})" if seq_str else name)

    def _save_settings(self):
        self._settings.setValue("theme", theme_manager.name)
        self._settings.setValue("hotkeys", json.dumps(self._hotkeys))

    # ---- Window close — save geometry + settings ---------------------------

    def closeEvent(self, event):
        self._save_settings()
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    # ---- Helpers -----------------------------------------------------------

    def _select_all(self):
        canvas = self._store.active_canvas
        if canvas:
            self._controller.select(list(canvas.objects.keys()))

    def _bring_forward(self):
        for oid in self._store.selection.selected_ids:
            self._controller.bring_forward(oid)

    def _send_backward(self):
        for oid in self._store.selection.selected_ids:
            self._controller.send_backward(oid)

    # ---- Demo --------------------------------------------------------------

    def _create_demo(self):
        c = self._controller
        c.add_rect(80, 80, 300, 180)
        c.add_ellipse(450, 100, 200, 200)
        c.add_text(80, 320, "Canvas Editor")
        c.clear_selection()
