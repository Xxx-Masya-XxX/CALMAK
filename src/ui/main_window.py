"""
MainWindow — главное окно редактора.

Собирает приложение из независимых компонентов:
  ui/toolbars/file_toolbar.py    — файл/undo/canvas
  ui/toolbars/tools_toolbar.py   — инструменты трансформации
  ui/toolbars/create_toolbar.py  — создание объектов
  ui/dialogs/settings_dialog.py  — настройки темы и горячих клавиш
  ui/hotkeys.py                  — DEFAULT_HOTKEYS + apply_hotkeys()
  ui/context_toolbar.py          — контекстный тулбар (Bezier и др.)
"""
from __future__ import annotations
import json

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget,
    QLabel, QSizePolicy, QApplication, QInputDialog,
)

from state.editor_store import EditorStore
from controllers.editor_controller import EditorController
from tools.tool_manager import (ToolManager,
                                 TOOL_MOVE, TOOL_ROTATE,
                                 TOOL_SCALE, TOOL_BEZIER)

from ui.scene.scene_view import SceneView
from ui.panels.element_tree_panel import ElementTreePanel
from ui.panels.properties_panel import PropertiesPanel
from ui.context_toolbar import ContextToolbarManager

from ui.toolbars.file_toolbar   import FileToolbar
from ui.toolbars.tools_toolbar  import ToolsToolbar
from ui.toolbars.create_toolbar import CreateToolbar

from ui.dialogs.settings_dialog import SettingsDialog
from ui.hotkeys import DEFAULT_HOTKEYS, apply_hotkeys
from ui.theme import THEMES, build_stylesheet, theme_manager
from ui.icons import get_icon, setup_theme_auto_refresh


class MainWindow(QMainWindow):

    # -----------------------------------------------------------------------
    # Init
    # -----------------------------------------------------------------------

    def __init__(self):
        super().__init__()
        self._store        = EditorStore()
        self._controller   = EditorController(self._store)
        self._tool_manager = ToolManager()
        self._hotkeys      = dict(DEFAULT_HOTKEYS)

        self._settings = QSettings("CanvasEditor", "CanvasEditor")
        self._load_settings()

        self.setWindowTitle("Canvas Editor")
        self.resize(1480, 920)

        # Auto-clear icon cache on theme change
        setup_theme_auto_refresh()

        self._build_ui()
        apply_hotkeys(self._hotkeys,
                      self._tb_create.actions_map,
                      self._tb_tools.tool_actions,
                      self._tb_create.labels)

        # Restore window layout from last session
        geom  = self._settings.value("geometry")
        state = self._settings.value("windowState")
        if geom:  self.restoreGeometry(geom)
        if state: self.restoreState(state)

        self._create_demo()

    # -----------------------------------------------------------------------
    # Settings persistence
    # -----------------------------------------------------------------------

    def _load_settings(self):
        saved_theme = self._settings.value("theme", "Dark")
        saved_hk    = self._settings.value("hotkeys")
        if saved_hk:
            try:
                self._hotkeys.update(json.loads(saved_hk))
            except Exception:
                pass
        theme_manager.apply(saved_theme)

    def _save_settings(self):
        self._settings.setValue("theme",       theme_manager.name)
        self._settings.setValue("hotkeys",     json.dumps(self._hotkeys))
        self._settings.setValue("geometry",    self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def _build_ui(self):
        self._setup_menu()
        self._setup_toolbars()
        self._setup_docks()
        self._setup_central()
        self._setup_status()
        self._connect_store()

    # -----------------------------------------------------------------------
    # Menu
    # -----------------------------------------------------------------------

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
        self._act(om, "Add Rect",     None, lambda: self._controller.add_rect())
        self._act(om, "Add Ellipse",  None, lambda: self._controller.add_ellipse())
        self._act(om, "Add Triangle", None, lambda: self._controller.add_triangle())
        self._act(om, "Add Text",     None, lambda: self._controller.add_text())
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

        # Settings
        sm = mb.addMenu("Settings")
        self._act(sm, "Preferences…", "Ctrl+,", self._open_settings)
        sm.addSeparator()
        for theme_name in THEMES:
            _t = theme_name
            self._act(sm, f"Theme: {theme_name}", None,
                      lambda _, t=_t: self._apply_theme(t))

        # View
        vm = mb.addMenu("View")
        self._act(vm, "Fit Canvas", "Ctrl+0",
                  lambda: self._scene_view.fit_view())
        self._act(vm, "Zoom In",    "Ctrl+=",
                  lambda: self._scene_view.zoom_in())
        self._act(vm, "Zoom Out",   "Ctrl+-",
                  lambda: self._scene_view.zoom_out())

    def _act(self, menu, label, shortcut, slot) -> QAction:
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if slot:
            a.triggered.connect(slot)
        menu.addAction(a)
        return a

    # -----------------------------------------------------------------------
    # Toolbars
    # -----------------------------------------------------------------------

    def _setup_toolbars(self):
        self._tb_file = FileToolbar(
            self._store, self._controller,
            self._open_settings, self)
        self.addToolBar(Qt.TopToolBarArea, self._tb_file)

        self._tb_tools = ToolsToolbar(
            self._tool_manager,
            self._bring_forward,
            self._send_backward, self)
        self.addToolBar(Qt.TopToolBarArea, self._tb_tools)

        self._tb_create = CreateToolbar(self._controller, self)
        self.addToolBar(Qt.TopToolBarArea, self._tb_create)

        # Convenience aliases (used in _connect_store, _apply_hotkeys)
        self._tool_actions   = self._tb_tools.tool_actions
        self._create_actions = self._tb_create.actions_map

    # -----------------------------------------------------------------------
    # Docks
    # -----------------------------------------------------------------------

    def _setup_docks(self):
        self._props_panel = PropertiesPanel(self._store, self._controller)
        d_props = QDockWidget("Properties", self)
        d_props.setObjectName("dock_properties")
        d_props.setWidget(self._props_panel)
        d_props.setMinimumWidth(250)
        self.addDockWidget(Qt.RightDockWidgetArea, d_props)

        self._tree_panel = ElementTreePanel(self._store, self._controller)
        d_layers = QDockWidget("Layers", self)
        d_layers.setObjectName("dock_layers")
        d_layers.setWidget(self._tree_panel)
        d_layers.setMinimumWidth(220)
        self.addDockWidget(Qt.RightDockWidgetArea, d_layers)

        self.splitDockWidget(d_props, d_layers, Qt.Vertical)

    # -----------------------------------------------------------------------
    # Central widget
    # -----------------------------------------------------------------------

    def _setup_central(self):
        self._scene_view = SceneView(
            self._store, self._controller, self._tool_manager)

        wrapper = QWidget()
        wrapper.setObjectName("scene_wrapper")
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self._ctx_toolbar = ContextToolbarManager(
            self._store, self._controller,
            self._tool_manager, wrapper)
        vbox.addWidget(self._ctx_toolbar)
        vbox.addWidget(self._scene_view)

        self.setCentralWidget(wrapper)
        self._tb_file.refresh_canvas_combo()

    # -----------------------------------------------------------------------
    # Status bar
    # -----------------------------------------------------------------------

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

        self._zoom_timer = QTimer(self)
        self._zoom_timer.timeout.connect(self._update_zoom_label)
        self._zoom_timer.start(200)

    # -----------------------------------------------------------------------
    # Store connections
    # -----------------------------------------------------------------------

    def _connect_store(self):
        self._store.document_changed.connect(self._on_doc_changed)
        self._store.selection_changed.connect(
            lambda ids, aid: self._update_status())
        self._store.history_changed.connect(self._on_history_changed)
        self._store.title_changed.connect(self.setWindowTitle)
        self._store.canvas_switched.connect(
            lambda _: self._tb_file.refresh_canvas_combo())
        self._tool_manager.tool_changed.connect(self._on_tool_changed)

    def _on_doc_changed(self):
        self._tb_file.refresh_canvas_combo()
        self._update_status()
        if hasattr(self, "_ctx_toolbar"):
            self._ctx_toolbar.refresh_active()

    def _on_history_changed(self, can_undo: bool, can_redo: bool):
        h = self._store.history
        self._tb_file.update_undo_redo(
            can_undo, can_redo,
            f"Undo: {h.undo_description}" if can_undo else "Nothing to undo",
            f"Redo: {h.redo_description}" if can_redo else "Nothing to redo",
        )

    def _on_tool_changed(self, tool_id: str):
        names = {TOOL_MOVE: "Move", TOOL_ROTATE: "Rotate",
                 TOOL_SCALE: "Scale", TOOL_BEZIER: "Bezier Path"}
        self._tool_lbl.setText(f"  Tool: {names.get(tool_id, tool_id)}")

    # -----------------------------------------------------------------------
    # Status helpers
    # -----------------------------------------------------------------------

    def _update_zoom_label(self):
        if hasattr(self, "_scene_view"):
            self._zoom_lbl.setText(
                f"  {self._scene_view.current_zoom_percent()}%")

    def _update_status(self):
        canvas = self._store.active_canvas
        if canvas:
            n   = len(canvas.objects)
            sel = len(self._store.selection.selected_ids)
            self._status_lbl.setText(
                f"{canvas.name}  •  {n} object{'s' if n != 1 else ''}"
                f"  •  {canvas.width}×{canvas.height}")
            self._sel_lbl.setText(f"  {sel} selected" if sel else "")

    # -----------------------------------------------------------------------
    # Settings
    # -----------------------------------------------------------------------

    def _open_settings(self):
        dlg       = SettingsDialog(theme_manager.name, self._hotkeys, self)
        prev_theme = theme_manager.name

        if dlg.exec():
            self._hotkeys = dlg.get_hotkeys()
            self._apply_theme(dlg.get_theme())
            apply_hotkeys(self._hotkeys,
                          self._tb_create.actions_map,
                          self._tb_tools.tool_actions,
                          self._tb_create.labels)
            self._save_settings()
        else:
            if prev_theme != theme_manager.name:
                theme_manager.apply(prev_theme)

    def _apply_theme(self, theme_name: str):
        theme_manager.apply(theme_name)
        self._refresh_toolbar_icons()

    def _refresh_toolbar_icons(self):
        """Перерисовывает SVG иконки при смене темы."""
        self._tb_file.refresh_icons()
        self._tb_tools.refresh_icons()
        self._tb_create.refresh_icons()
        if hasattr(self, "_tree_panel"):
            self._tree_panel._tree.update()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Close
    # -----------------------------------------------------------------------

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    # -----------------------------------------------------------------------
    # Demo
    # -----------------------------------------------------------------------

    def _create_demo(self):
        c = self._controller
        c.add_rect(80, 80, 300, 180)
        c.add_ellipse(450, 100, 200, 200)
        c.add_text(80, 320, "Canvas Editor")
        c.clear_selection()
