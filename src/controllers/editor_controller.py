"""
EditorController — единая точка входа для всех мутаций.
UI вызывает методы контроллера. Контроллер создаёт команды и пушит в Store.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QMessageBox

from domain.models import (
    DocumentState, ObjectState, CanvasState,
    make_rect, make_ellipse, make_text, make_image, make_group,
    gen_id, ObjectType
)
from commands.commands import (
    AddObjectCommand, DeleteObjectCommand, MoveObjectCommand,
    ResizeObjectCommand, UpdatePropertiesCommand, ReparentObjectCommand,
    DuplicateObjectCommand, ReorderObjectCommand
)

if TYPE_CHECKING:
    from state.editor_store import EditorStore


class EditorController(QObject):
    def __init__(self, store: "EditorStore"):
        super().__init__()
        self.store = store

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def select(self, obj_ids: list[str]):
        self.store._set_selection(obj_ids)

    def select_one(self, obj_id: str):
        self.store._set_selection([obj_id])

    def clear_selection(self):
        self.store._clear_selection()

    def toggle_selection(self, obj_id: str):
        sel = list(self.store.selection.selected_ids)
        if obj_id in sel:
            sel.remove(obj_id)
        else:
            sel.append(obj_id)
        self.store._set_selection(sel)

    # -----------------------------------------------------------------------
    # Canvas management
    # -----------------------------------------------------------------------

    def switch_canvas(self, canvas_id: str):
        self.store._switch_canvas(canvas_id)

    def add_canvas(self, name: str = "New Canvas",
                   width: int = 1920, height: int = 1080):
        canvas = CanvasState(id=gen_id(), name=name, width=width, height=height)
        self.store._add_canvas(canvas)
        self.store._switch_canvas(canvas.id)

    # -----------------------------------------------------------------------
    # Object creation
    # -----------------------------------------------------------------------

    def _canvas_id(self) -> str | None:
        c = self.store.active_canvas
        return c.id if c else None

    def add_rect(self, x=100, y=100, w=200, h=120):
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        n = sum(1 for o in canvas.objects.values()
                if o.type == ObjectType.RECT) + 1
        obj = make_rect(f"Rect {n}", x, y, w, h)
        self.store._push_command(AddObjectCommand(cid, obj))
        self.select_one(obj.id)

    def add_ellipse(self, x=150, y=150, w=150, h=150):
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        n = sum(1 for o in canvas.objects.values()
                if o.type == ObjectType.ELLIPSE) + 1
        obj = make_ellipse(f"Ellipse {n}", x, y, w, h)
        self.store._push_command(AddObjectCommand(cid, obj))
        self.select_one(obj.id)

    def add_text(self, x=100, y=100, text="Text"):
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        n = sum(1 for o in canvas.objects.values()
                if o.type == ObjectType.TEXT) + 1
        obj = make_text(f"Text {n}", text, x, y, 200, 40)
        self.store._push_command(AddObjectCommand(cid, obj))
        self.select_one(obj.id)

    def add_bezier(self, x=100, y=100, w=220, h=100):
        from domain.models import make_bezier
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        n = sum(1 for o in canvas.objects.values()
                if o.type == ObjectType.BEZIER) + 1
        obj = make_bezier(f"Bezier {n}", x, y)
        self.store._push_command(AddObjectCommand(cid, obj))
        self.select_one(obj.id)

    def add_triangle(self, x=100, y=100, w=150, h=150):
        """Треугольник — path-объект (храним как rect с type=triangle)."""
        from domain.models import ObjectType, ObjectState, Transform, StyleState, ShapePayload, gen_id
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        n = sum(1 for o in canvas.objects.values()
                if o.type == ObjectType.RECT and "Triangle" in o.name) + 1
        obj = ObjectState(
            id=gen_id(),
            type=ObjectType.RECT,       # используем RECT как базу
            name=f"Triangle {n}",
            transform=Transform(x=x, y=y, width=w, height=h),
            style=StyleState(fill_color="#E2844A", stroke_color="#8A4A2C",
                             stroke_width=1.5),
            payload=ShapePayload(),
        )
        # Помечаем как треугольник через имя — рендерер проверит
        # (в будущем — отдельный ObjectType.TRIANGLE)
        self.store._push_command(AddObjectCommand(cid, obj))
        self.select_one(obj.id)

    def add_image(self, path: str = "", x=100, y=100, w=200, h=200):
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        n = sum(1 for o in canvas.objects.values()
                if o.type == ObjectType.IMAGE) + 1
        obj = make_image(f"Image {n}", path, x, y, w, h)
        self.store._push_command(AddObjectCommand(cid, obj))
        self.select_one(obj.id)

    def add_image_from_dialog(self, parent=None):
        path, _ = QFileDialog.getOpenFileName(
            parent, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self.add_image(path)

    # -----------------------------------------------------------------------
    # Object mutations
    # -----------------------------------------------------------------------

    def move_object(self, obj_id: str, x: float, y: float):
        cid = self._canvas_id()
        if not cid:
            return
        self.store._push_command(MoveObjectCommand(cid, obj_id, x, y))

    def resize_object(self, obj_id: str, x: float, y: float,
                      w: float, h: float):
        cid = self._canvas_id()
        if not cid:
            return
        self.store._push_command(ResizeObjectCommand(cid, obj_id, x, y, w, h))

    def update_properties(self, obj_id: str, updates: dict):
        cid = self._canvas_id()
        if not cid:
            return
        self.store._push_command(UpdatePropertiesCommand(cid, obj_id, updates))

    def delete_selected(self):
        cid = self._canvas_id()
        if not cid:
            return
        ids = list(self.store.selection.selected_ids)
        self.store._clear_selection()
        for obj_id in ids:
            self.store._push_command(DeleteObjectCommand(cid, obj_id))

    def duplicate_selected(self):
        cid = self._canvas_id()
        if not cid:
            return
        for obj_id in list(self.store.selection.selected_ids):
            self.store._push_command(DuplicateObjectCommand(cid, obj_id))

    def reparent_object(self, obj_id: str, new_parent_id: str | None,
                        index: int = -1):
        cid = self._canvas_id()
        if not cid:
            return
        self.store._push_command(
            ReparentObjectCommand(cid, obj_id, new_parent_id, index)
        )

    def bring_forward(self, obj_id: str):
        cid = self._canvas_id()
        if cid:
            self.store._push_command(ReorderObjectCommand(cid, obj_id, -1))

    def send_backward(self, obj_id: str):
        cid = self._canvas_id()
        if cid:
            self.store._push_command(ReorderObjectCommand(cid, obj_id, +1))

    # -----------------------------------------------------------------------
    # Undo / Redo
    # -----------------------------------------------------------------------

    def undo(self):
        self.store._undo()

    def redo(self):
        self.store._redo()

    # -----------------------------------------------------------------------
    # File I/O
    # -----------------------------------------------------------------------

    def new_document(self, parent=None):
        if self.store.document.dirty:
            reply = QMessageBox.question(
                parent, "Unsaved Changes",
                "Save changes before creating new document?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_document(parent)
            elif reply == QMessageBox.Cancel:
                return
        doc = DocumentState()
        canvas = doc.create_default_canvas()
        doc.active_canvas_id = canvas.id
        doc.dirty = False
        self.store._load_document(doc)

    def save_document(self, parent=None):
        from serialization.serializer import ProjectSerializer
        doc = self.store.document
        if not doc.file_path:
            path, _ = QFileDialog.getSaveFileName(
                parent, "Save Project", "",
                "Canvas Editor Project (*.cep)"
            )
            if not path:
                return
            if not path.endswith(".cep"):
                path += ".cep"
            doc.file_path = path
        ProjectSerializer.save(doc, doc.file_path)
        doc.dirty = False
        self.store.title_changed.emit(f"{doc.file_path} — Canvas Editor")

    def load_document(self, parent=None):
        from serialization.serializer import ProjectSerializer
        path, _ = QFileDialog.getOpenFileName(
            parent, "Open Project", "",
            "Canvas Editor Project (*.cep)"
        )
        if not path:
            return
        try:
            doc = ProjectSerializer.load(path)
            doc.file_path = path
            doc.dirty = False
            self.store._load_document(doc)
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to load: {e}")

    def export_canvas(self, parent=None):
        from export.exporter import CanvasExporter
        canvas = self.store.active_canvas
        if not canvas:
            return
        path, flt = QFileDialog.getSaveFileName(
            parent, "Export Canvas", "",
            "PNG Image (*.png);;JPEG Image (*.jpg);;BMP Image (*.bmp)"
        )
        if not path:
            return
        fmt = "PNG"
        if ".jpg" in path.lower() or "JPEG" in flt:
            fmt = "JPEG"
        elif ".bmp" in path.lower():
            fmt = "BMP"
        CanvasExporter.export(canvas, path, fmt)
        QMessageBox.information(parent, "Exported",
                                f"Canvas exported to:\n{path}")

    # -----------------------------------------------------------------------
    # Alignment helpers
    # -----------------------------------------------------------------------

    def align_objects(self, mode: str):
        """mode: left/right/top/bottom/center_h/center_v"""
        cid = self._canvas_id()
        if not cid:
            return
        canvas = self.store.active_canvas
        ids = self.store.selection.selected_ids
        if len(ids) < 2:
            return
        objects = [canvas.objects[i] for i in ids if i in canvas.objects]
        if not objects:
            return

        xs = [o.transform.x for o in objects]
        ys = [o.transform.y for o in objects]
        x2s = [o.transform.x + o.transform.width for o in objects]
        y2s = [o.transform.y + o.transform.height for o in objects]

        for obj in objects:
            t = obj.transform
            if mode == "left":
                new_x = min(xs)
                self.store._push_command(
                    MoveObjectCommand(cid, obj.id, new_x, t.y))
            elif mode == "right":
                new_x = max(x2s) - t.width
                self.store._push_command(
                    MoveObjectCommand(cid, obj.id, new_x, t.y))
            elif mode == "top":
                new_y = min(ys)
                self.store._push_command(
                    MoveObjectCommand(cid, obj.id, t.x, new_y))
            elif mode == "bottom":
                new_y = max(y2s) - t.height
                self.store._push_command(
                    MoveObjectCommand(cid, obj.id, t.x, new_y))
            elif mode == "center_h":
                cx = (min(xs) + max(x2s)) / 2
                self.store._push_command(
                    MoveObjectCommand(cid, obj.id, cx - t.width / 2, t.y))
            elif mode == "center_v":
                cy = (min(ys) + max(y2s)) / 2
                self.store._push_command(
                    MoveObjectCommand(cid, obj.id, t.x, cy - t.height / 2))
