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
from tools.tool_manager import (ToolManager, TOOL_MOVE, TOOL_ROTATE, TOOL_SCALE)
from ui.scene.scene_view import SceneView
from ui.panels.element_tree_panel import ElementTreePanel
from ui.panels.properties_panel import PropertiesPanel
from ui.constants import C, menu_stylesheet


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------

THEMES: dict[str, dict] = {
    "Dark": {
        "bg":        "#1A1A2A",
        "surface":   "#252535",
        "surface2":  "#2A2A3E",
        "border":    "#3A3A4A",
        "accent":    "#4A90E2",
        "accent2":   "#3A5A9A",
        "text":      "#CCCCDD",
        "text_dim":  "#888899",
        "scene_bg":  "#2D2D3A",
    },
    "Light": {
        "bg":        "#F0F0F5",
        "surface":   "#FFFFFF",
        "surface2":  "#E8E8F0",
        "border":    "#C8C8D8",
        "accent":    "#2060C0",
        "accent2":   "#1040A0",
        "text":      "#111122",
        "text_dim":  "#666677",
        "scene_bg":  "#D8D8E8",
    },
    "Midnight": {
        "bg":        "#0D0D1A",
        "surface":   "#13131F",
        "surface2":  "#1A1A2A",
        "border":    "#2A2A3A",
        "accent":    "#7A4AE2",
        "accent2":   "#5A2AC2",
        "text":      "#DDDDFF",
        "text_dim":  "#7777AA",
        "scene_bg":  "#181828",
    },
    "Warm": {
        "bg":        "#1F1A14",
        "surface":   "#2A231A",
        "surface2":  "#352B20",
        "border":    "#4A3F30",
        "accent":    "#E2904A",
        "accent2":   "#C27030",
        "text":      "#EEE0CC",
        "text_dim":  "#998877",
        "scene_bg":  "#252018",
    },
}

_current_theme: str = "Dark"


def build_stylesheet(theme_name: str) -> str:
    t = THEMES.get(theme_name, THEMES["Dark"])
    return f"""
    QMainWindow, QWidget {{ background: {t['bg']}; color: {t['text']}; }}
    QMenuBar {{
        background: {t['surface']}; color: {t['text']};
        border-bottom: 1px solid {t['border']}; padding: 2px; font-size: 12px;
    }}
    QMenuBar::item:selected {{ background: {t['accent2']}; border-radius: 3px; }}
    QMenu {{
        background: {t['surface']}; color: {t['text']};
        border: 1px solid {t['border']}; font-size: 12px;
    }}
    QMenu::item:selected {{ background: {t['accent2']}; }}
    QMenu::separator {{ height: 1px; background: {t['border']}; margin: 2px 8px; }}
    QToolBar {{
        background: {t['surface']}; border: 1px solid {t['border']};
        spacing: 2px; padding: 2px 4px;
    }}
    QToolBar::handle {{
        background: {t['border']}; width: 6px; border-radius: 2px; margin: 2px;
    }}
    QDockWidget {{
        color: {t['text']};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {t['surface']}; padding: 4px 8px;
        font-size: 11px; color: {t['text_dim']};
        border-bottom: 1px solid {t['border']};
    }}
    QStatusBar {{
        background: {t['surface']}; color: {t['text_dim']};
        border-top: 1px solid {t['border']}; font-size: 11px;
    }}
    QSplitter::handle {{ background: {t['border']}; }}
    QScrollBar:vertical {{
        background: {t['bg']}; width: 8px; border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']}; border-radius: 4px; min-height: 20px;
    }}
    QPushButton {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 4px;
        padding: 4px 10px; font-size: 11px;
    }}
    QPushButton:hover {{ background: {t['accent2']}; border-color: {t['accent']}; }}
    QPushButton:pressed {{ background: {t['accent']}; }}
    QPushButton:checked {{
        background: {t['accent2']}; border: 1px solid {t['accent']};
    }}
    QPushButton:flat {{
        background: transparent; border: none;
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 3px;
        padding: 3px 6px; font-size: 11px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QComboBox:focus, QTextEdit:focus {{
        border-color: {t['accent']};
    }}
    QComboBox QAbstractItemView {{
        background: {t['surface']}; color: {t['text']};
        border: 1px solid {t['border']};
    }}
    QTableWidget {{
        background: {t['surface2']}; color: {t['text']};
        border: 1px solid {t['border']}; gridline-color: {t['border']};
        font-size: 11px;
    }}
    QTableWidget::item:selected {{ background: {t['accent2']}; }}
    QHeaderView::section {{
        background: {t['surface']}; color: {t['text_dim']};
        border: 1px solid {t['border']}; padding: 4px; font-size: 10px;
    }}
    QTabWidget::pane {{
        border: 1px solid {t['border']}; background: {t['bg']};
    }}
    QTabBar::tab {{
        background: {t['surface']}; color: {t['text_dim']};
        padding: 5px 14px; border: none; font-size: 11px;
    }}
    QTabBar::tab:selected {{
        background: {t['bg']}; color: {t['text']};
        border-bottom: 2px solid {t['accent']};
    }}
    QGroupBox {{
        color: {t['text_dim']}; border: 1px solid {t['border']};
        border-radius: 4px; margin-top: 10px; font-size: 11px;
        padding: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 8px; padding: 0 4px;
    }}
    QCheckBox {{ color: {t['text']}; font-size: 11px; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {t['border']}; border-radius: 3px;
        background: {t['surface2']};
    }}
    QCheckBox::indicator:checked {{
        background: {t['accent']}; border-color: {t['accent']};
    }}
    """


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
    # Tools (defaults provided)
    "tool_move":    "V",
    "tool_rotate":  "R",
    "tool_scale":   "E",
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
            "add_rect":     "Add Rectangle",
            "add_ellipse":  "Add Ellipse",
            "add_triangle": "Add Triangle",
            "add_text":     "Add Text",
            "add_image":    "Add Image",
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
        # Live preview — обновляем стиль приложения немедленно
        QApplication.instance().setStyleSheet(build_stylesheet(theme_name))

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

        global _current_theme
        _current_theme = saved_theme

        self.setWindowTitle("Canvas Editor")
        self.resize(1480, 920)

        # Apply theme before building UI — обновляем C и stylesheet
        t = THEMES.get(_current_theme, THEMES["Dark"])
        C.set_theme(t)
        QApplication.instance().setStyleSheet(
            build_stylesheet(_current_theme))

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
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, tb)

        def add(icon, label, tip, slot, checkable=False):
            a = QAction(icon + "  " + label, self)
            a.setToolTip(tip)
            a.setCheckable(checkable)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        add("🆕", "New",    "New document  (Ctrl+N)",
            lambda: self._controller.new_document(self))
        add("📂", "Open",   "Open project  (Ctrl+O)",
            lambda: self._controller.load_document(self))
        add("💾", "Save",   "Save project  (Ctrl+S)",
            lambda: self._controller.save_document(self))
        add("📤", "Export", "Export canvas  (Ctrl+E)",
            lambda: self._controller.export_canvas(self))
        tb.addSeparator()

        self._undo_action = add("↩", "Undo", "Undo  (Ctrl+Z)",
                                self._controller.undo)
        self._redo_action = add("↪", "Redo", "Redo  (Ctrl+Shift+Z)",
                                self._controller.redo)
        self._undo_action.setEnabled(False)
        self._redo_action.setEnabled(False)
        tb.addSeparator()

        # Canvas selector
        self._canvas_combo = QComboBox()
        self._canvas_combo.setMinimumWidth(150)
        self._canvas_combo.setMaximumWidth(220)
        self._canvas_combo.currentIndexChanged.connect(self._on_canvas_combo)
        tb.addWidget(self._canvas_combo)

        add_canvas = QAction("➕  Add Canvas", self)
        add_canvas.setToolTip("Add new canvas")
        add_canvas.triggered.connect(self._add_canvas_dialog)
        tb.addAction(add_canvas)

        tb.addSeparator()
        settings_act = QAction("⚙  Settings", self)
        settings_act.setToolTip("Open settings  (Ctrl+,)")
        settings_act.triggered.connect(self._open_settings)
        tb.addAction(settings_act)

    # ---- Tools toolbar (Move / Rotate / Scale)

    def _build_tools_toolbar(self):
        tb = QToolBar("Transform Tools", self)
        tb.setObjectName("tb_tools")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, tb)

        # SELECT removed — Move tool handles selection too
        tools = [
            (TOOL_MOVE,   "✥", "Move",   "tool_move"),
            (TOOL_ROTATE, "↻", "Rotate", "tool_rotate"),
            (TOOL_SCALE,  "⤡", "Scale",  "tool_scale"),
        ]

        self._tool_actions: dict[str, QAction] = {}
        self._tool_hotkey_ids: dict[str, str] = {
            TOOL_MOVE:   "tool_move",
            TOOL_ROTATE: "tool_rotate",
            TOOL_SCALE:  "tool_scale",
        }

        for tool_id, icon, label, hk_id in tools:
            default_key = DEFAULT_HOTKEYS.get(hk_id, "")
            tip = f"{label}  ({default_key})" if default_key else label
            a = QAction(f"{icon}  {label}", self)
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
        tb.addAction(self._make_action("⬆  Forward", "Bring Forward  (Ctrl+])",
                                       self._bring_forward))
        tb.addAction(self._make_action("⬇  Backward", "Send Backward  (Ctrl+[)",
                                       self._send_backward))

    # ---- Create toolbar

    def _build_create_toolbar(self):
        tb = QToolBar("Create Objects", self)
        tb.setObjectName("tb_create")
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, tb)

        self._create_actions: dict[str, QAction] = {}

        objects = [
            ("add_rect",     "▭", "Rectangle"),
            ("add_ellipse",  "◯", "Ellipse"),
            ("add_triangle", "△", "Triangle"),
            ("add_text",     "T", "Text"),
            ("add_image",    "🖼","Image"),
        ]
        for action_id, icon, label in objects:
            slot = getattr(self, f"_{action_id}_action")
            a = self._make_action(f"{icon}  {label}", f"Add {label}", slot)
            tb.addAction(a)
            self._create_actions[action_id] = a

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
        self.setCentralWidget(self._scene_view)
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
        names = {TOOL_MOVE: "Move", TOOL_ROTATE: "Rotate", TOOL_SCALE: "Scale"}
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
        global _current_theme
        dlg = SettingsDialog(_current_theme, self._hotkeys, self)
        prev_theme = _current_theme

        if dlg.exec():
            _current_theme = dlg.get_theme()
            self._hotkeys  = dlg.get_hotkeys()
            self._apply_theme(_current_theme)
            self._apply_hotkeys()
            self._save_settings()
        else:
            # Restore previous theme if user cancelled
            if prev_theme != _current_theme:
                _current_theme = prev_theme
                QApplication.instance().setStyleSheet(
                    build_stylesheet(_current_theme))

    def _apply_theme(self, theme_name: str):
        global _current_theme
        _current_theme = theme_name
        t = THEMES.get(theme_name, THEMES["Dark"])
        C.set_theme(t)   # обновляем QColor-константы
        QApplication.instance().setStyleSheet(build_stylesheet(theme_name))

    def _apply_hotkeys(self):
        """Назначает горячие клавиши из self._hotkeys всем действиям."""
        # Create object actions
        create_map = {
            "add_rect":     self._create_actions.get("add_rect"),
            "add_ellipse":  self._create_actions.get("add_ellipse"),
            "add_triangle": self._create_actions.get("add_triangle"),
            "add_text":     self._create_actions.get("add_text"),
            "add_image":    self._create_actions.get("add_image"),
        }
        for action_id, action in create_map.items():
            if action is None:
                continue
            seq = self._hotkeys.get(action_id, "")
            action.setShortcut(QKeySequence(seq) if seq else QKeySequence())
            # Update tooltip to show shortcut
            seq_str = QKeySequence(seq).toString() if seq else ""
            label = action.text().strip()
            action.setToolTip(f"{label}  ({seq_str})" if seq_str else label)

        # Tool actions
        tool_map = {
            "tool_move":   self._tool_actions.get(TOOL_MOVE),
            "tool_rotate": self._tool_actions.get(TOOL_ROTATE),
            "tool_scale":  self._tool_actions.get(TOOL_SCALE),
        }
        tool_names = {
            "tool_move":   "Move",
            "tool_rotate": "Rotate",
            "tool_scale":  "Scale",
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
        global _current_theme
        self._settings.setValue("theme", _current_theme)
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
