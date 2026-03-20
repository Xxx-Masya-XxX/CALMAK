"""
EditorStore — хранит всё состояние редактора.
Все панели подписываются на сигналы Store.
Никто не меняет состояние напрямую — только через EditorController.
"""
from __future__ import annotations
from PySide6.QtCore import QObject, Signal
from domain.models import DocumentState, SelectionState, gen_id, CanvasState
from commands.commands import CommandHistory


class EditorStore(QObject):
    # Сигналы → все подписчики обновляются
    document_changed          = Signal()           # любое изменение документа
    document_structure_changed = Signal()          # добавлен/удалён объект или канвас
    selection_changed         = Signal(list, object)  # (selected_ids, active_id)
    canvas_switched           = Signal(str)        # активный canvas сменился
    history_changed           = Signal(bool, bool) # (can_undo, can_redo)
    title_changed             = Signal(str)        # для заголовка окна

    def __init__(self):
        super().__init__()
        self._doc       = DocumentState()
        self._selection = SelectionState()
        self._history   = CommandHistory(max_size=200)

        # Создаём первый canvas по умолчанию
        canvas = self._doc.create_default_canvas()
        self._doc.active_canvas_id = canvas.id

    # -----------------------------------------------------------------------
    # Readonly accessors
    # -----------------------------------------------------------------------

    @property
    def document(self) -> DocumentState:
        return self._doc

    @property
    def selection(self) -> SelectionState:
        return self._selection

    @property
    def history(self) -> CommandHistory:
        return self._history

    @property
    def active_canvas(self) -> CanvasState | None:
        return self._doc.active_canvas

    # -----------------------------------------------------------------------
    # Internal mutation methods (called only by EditorController)
    # -----------------------------------------------------------------------

    # Commands that structurally change the document (add/remove objects/canvases)
    _STRUCTURAL_COMMANDS = (
        "AddObjectCommand", "DeleteObjectCommand",
        "DuplicateObjectCommand", "ReparentObjectCommand",
    )

    def _push_command(self, cmd):
        self._history.push(cmd, self._doc)
        self._emit_history()
        self.document_changed.emit()
        # Emit structural signal for add/remove/reparent so tree knows to rebuild
        if type(cmd).__name__ in self._STRUCTURAL_COMMANDS:
            self.document_structure_changed.emit()
        self._update_title()

    def _undo(self) -> bool:
        ok = self._history.undo(self._doc)
        if ok:
            self._emit_history()
            self.document_changed.emit()
            self.document_structure_changed.emit()  # safe to always emit on undo
            self._update_title()
        return ok

    def _redo(self) -> bool:
        ok = self._history.redo(self._doc)
        if ok:
            self._emit_history()
            self.document_changed.emit()
            self.document_structure_changed.emit()  # safe to always emit on redo
            self._update_title()
        return ok

    def _set_selection(self, ids: list[str]):
        self._selection.set(ids)
        self.selection_changed.emit(
            self._selection.selected_ids,
            self._selection.active_id
        )

    def _clear_selection(self):
        self._selection.clear()
        self.selection_changed.emit([], None)

    def _switch_canvas(self, canvas_id: str):
        if canvas_id in self._doc.canvases:
            self._doc.active_canvas_id = canvas_id
            self._clear_selection()
            self.canvas_switched.emit(canvas_id)
            self.document_changed.emit()

    def _add_canvas(self, canvas: CanvasState):
        self._doc.add_canvas(canvas)
        self.document_changed.emit()

    def _load_document(self, doc: DocumentState):
        self._doc = doc
        self._selection.clear()
        self._history.clear()
        self.document_changed.emit()
        self.document_structure_changed.emit()
        self._emit_history()
        self._update_title()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _emit_history(self):
        self.history_changed.emit(
            self._history.can_undo,
            self._history.can_redo
        )

    def _update_title(self):
        path = self._doc.file_path or "Untitled"
        dirty = "*" if self._doc.dirty else ""
        self.title_changed.emit(f"{dirty}{path} — Canvas Editor")
