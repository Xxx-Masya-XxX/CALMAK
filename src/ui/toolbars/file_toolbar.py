"""
ui/toolbars/file_toolbar.py — тулбар файловых операций.

Содержит: New · Open · Save · Export · Undo · Redo · Canvas Selector ·
          Add Canvas · Settings
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar, QComboBox, QInputDialog

from ui.icons import get_icon

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow
    from state.editor_store import EditorStore
    from controllers.editor_controller import EditorController


class FileToolbar(QToolBar):
    """
    Тулбар «File & Edit».

    Публичные атрибуты:
      undo_action, redo_action  — для управления enabled из MainWindow
      canvas_combo              — QComboBox для выбора канваса
    """

    def __init__(self, store: "EditorStore",
                 controller: "EditorController",
                 open_settings_cb,
                 parent: "QMainWindow" = None):
        super().__init__("File & Edit", parent)
        self._store      = store
        self._ctrl       = controller
        self._open_settings_cb = open_settings_cb

        self.setObjectName("tb_file")
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QSize(20, 20))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self._build()
        self._connect_store()

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def _build(self):
        def add(icon_name: str, tip: str, slot) -> QAction:
            a = QAction(self)
            a.setIcon(get_icon(icon_name, 20))
            a.setToolTip(tip)
            a.triggered.connect(slot)
            self.addAction(a)
            return a

        add("new",    "New document  (Ctrl+N)",
            lambda: self._ctrl.new_document(self.parent()))
        add("open",   "Open project  (Ctrl+O)",
            lambda: self._ctrl.load_document(self.parent()))
        add("save",   "Save project  (Ctrl+S)",
            lambda: self._ctrl.save_document(self.parent()))
        add("export", "Export canvas  (Ctrl+E)",
            lambda: self._ctrl.export_canvas(self.parent()))

        self.addSeparator()

        self.undo_action = add("undo", "Undo  (Ctrl+Z)", self._ctrl.undo)
        self.redo_action = add("redo", "Redo  (Ctrl+Shift+Z)", self._ctrl.redo)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)

        self.addSeparator()

        # Canvas selector
        self.canvas_combo = QComboBox()
        self.canvas_combo.setMinimumWidth(150)
        self.canvas_combo.setMaximumWidth(220)
        self.canvas_combo.currentIndexChanged.connect(self._on_canvas_combo)
        self.addWidget(self.canvas_combo)

        self._add_canvas_action = add(
            "add_canvas", "Add new canvas",
            self._on_add_canvas)

        self.addSeparator()

        add("settings", "Settings  (Ctrl+,)", self._open_settings_cb)

        # All non-separator, non-widget actions for icon refresh
        self._svg_actions: dict[str, QAction] = {
            "new":        self.actions()[0],
            "open":       self.actions()[1],
            "save":       self.actions()[2],
            "export":     self.actions()[3],
            "undo":       self.undo_action,
            "redo":       self.redo_action,
            "add_canvas": self._add_canvas_action,
        }

    # -----------------------------------------------------------------------
    # Store
    # -----------------------------------------------------------------------

    def _connect_store(self):
        self._store.canvas_switched.connect(lambda _: self.refresh_canvas_combo())
        self._store.document_changed.connect(self.refresh_canvas_combo)

    def refresh_canvas_combo(self):
        self.canvas_combo.blockSignals(True)
        self.canvas_combo.clear()
        doc = self._store.document
        for cid, canvas in doc.canvases.items():
            self.canvas_combo.addItem(canvas.name, cid)
        for i in range(self.canvas_combo.count()):
            if self.canvas_combo.itemData(i) == doc.active_canvas_id:
                self.canvas_combo.setCurrentIndex(i)
                break
        self.canvas_combo.blockSignals(False)

    def _on_canvas_combo(self, idx: int):
        cid = self.canvas_combo.itemData(idx)
        if cid:
            self._ctrl.switch_canvas(cid)

    def _on_add_canvas(self):
        name, ok = QInputDialog.getText(
            self.parent(), "New Canvas", "Canvas name:")
        if ok and name.strip():
            self._ctrl.add_canvas(name.strip())

    # -----------------------------------------------------------------------
    # Icon refresh
    # -----------------------------------------------------------------------

    def refresh_icons(self):
        """Перерисовать все иконки (вызывать после смены темы)."""
        for name, action in self._svg_actions.items():
            action.setIcon(get_icon(name, 20))
        # Settings is the last non-sep action
        last_actions = [a for a in self.actions()
                        if not a.isSeparator() and a.text() == ""]
        if last_actions:
            last_actions[-1].setIcon(get_icon("settings", 20))

    def update_undo_redo(self, can_undo: bool, can_redo: bool,
                         undo_tip: str = "", redo_tip: str = ""):
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        self.undo_action.setToolTip(undo_tip or "Undo  (Ctrl+Z)")
        self.redo_action.setToolTip(redo_tip or "Redo  (Ctrl+Shift+Z)")
