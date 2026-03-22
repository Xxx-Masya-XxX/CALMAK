"""
ui/dialogs/settings_dialog.py — диалог настроек приложения.

Вкладки:
  • Appearance — выбор темы с live-превью
  • Hotkeys    — настройка горячих клавиш для инструментов и создания объектов
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QTabWidget, QWidget,
    QVBoxLayout, QGroupBox, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QKeySequenceEdit, QPushButton, QAbstractItemView,
)

from ui.theme import THEMES, theme_manager
from ui.hotkeys import DEFAULT_HOTKEYS


class SettingsDialog(QDialog):
    """
    Диалог настроек.

    Использование::

        dlg = SettingsDialog(theme_manager.name, self._hotkeys, self)
        prev = theme_manager.name
        if dlg.exec():
            apply(dlg.get_theme())
            use(dlg.get_hotkeys())
        else:
            theme_manager.apply(prev)   # откат превью
    """

    def __init__(self, current_theme: str,
                 hotkeys: dict[str, str],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(480, 400)
        self._chosen_theme = current_theme
        self._hotkeys      = dict(hotkeys)
        self._build_ui()

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

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

    # ---- Appearance --------------------------------------------------------

    def _appearance_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 16, 12, 8)
        lay.setSpacing(12)

        grp = QGroupBox("Theme")
        gl  = QVBoxLayout(grp)
        gl.addWidget(QLabel("Choose application color theme:"))

        self._theme_combo = QComboBox()
        for name in THEMES:
            self._theme_combo.addItem(name)
        self._theme_combo.setCurrentText(self._chosen_theme)
        self._theme_combo.currentTextChanged.connect(self._on_theme_preview)
        gl.addWidget(self._theme_combo)

        hint = QLabel("Preview changes live — cancel to discard.")
        hint.setStyleSheet("font-size:10px;")
        gl.addWidget(hint)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ---- Hotkeys -----------------------------------------------------------

    def _hotkeys_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 16, 12, 8)
        lay.setSpacing(8)

        info = QLabel(
            "Assign optional keyboard shortcuts.\n"
            "Leave empty to disable. Press a key combination in the field.")
        info.setWordWrap(True)
        info.setStyleSheet("font-size:10px;")
        lay.addWidget(info)

        _labels: dict[str, str] = {
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

        self._hotkey_table = QTableWidget(len(_labels), 2)
        self._hotkey_table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self._hotkey_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self._hotkey_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        self._hotkey_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._hotkey_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._hotkey_table.verticalHeader().setVisible(False)

        self._key_edits: dict[str, QKeySequenceEdit] = {}
        for row, (action_id, label) in enumerate(_labels.items()):
            item = QTableWidgetItem(label)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._hotkey_table.setItem(row, 0, item)

            edit = QKeySequenceEdit(
                QKeySequence(self._hotkeys.get(action_id, "")))
            self._hotkey_table.setCellWidget(row, 1, edit)
            self._key_edits[action_id] = edit

        lay.addWidget(self._hotkey_table)

        clear_btn = QPushButton("Clear All Shortcuts")
        clear_btn.setFixedWidth(160)
        clear_btn.clicked.connect(self._clear_all)
        lay.addWidget(clear_btn, alignment=Qt.AlignLeft)
        return w

    # -----------------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------------

    def _on_theme_preview(self, theme_name: str):
        self._chosen_theme = theme_name
        theme_manager.apply(theme_name)

    def _clear_all(self):
        for edit in self._key_edits.values():
            edit.setKeySequence(QKeySequence())

    # -----------------------------------------------------------------------
    # Result
    # -----------------------------------------------------------------------

    def get_theme(self) -> str:
        return self._chosen_theme

    def get_hotkeys(self) -> dict[str, str]:
        return {
            action_id: edit.keySequence().toString()
            for action_id, edit in self._key_edits.items()
        }
