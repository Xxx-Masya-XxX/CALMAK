"""
Command pattern for undo/redo.
Every state mutation goes through a Command.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.models import (
        DocumentState, ObjectState, Transform, StyleState, CanvasState
    )


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Command(ABC):
    description: str = "Command"

    @abstractmethod
    def execute(self, doc: "DocumentState") -> None: ...

    @abstractmethod
    def undo(self, doc: "DocumentState") -> None: ...


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class CommandHistory:
    def __init__(self, max_size: int = 100):
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._max_size = max_size

    def push(self, cmd: Command, doc: "DocumentState"):
        cmd.execute(doc)
        self._undo_stack.append(cmd)
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        doc.dirty = True

    def undo(self, doc: "DocumentState") -> bool:
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo(doc)
        self._redo_stack.append(cmd)
        doc.dirty = True
        return True

    def redo(self, doc: "DocumentState") -> bool:
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute(doc)
        self._undo_stack.append(cmd)
        doc.dirty = True
        return True

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_description(self) -> str:
        return self._undo_stack[-1].description if self._undo_stack else ""

    @property
    def redo_description(self) -> str:
        return self._redo_stack[-1].description if self._redo_stack else ""

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()


# ---------------------------------------------------------------------------
# Object commands
# ---------------------------------------------------------------------------

class AddObjectCommand(Command):
    def __init__(self, canvas_id: str, obj: "ObjectState",
                 parent_id: str | None = None):
        self.canvas_id  = canvas_id
        self.obj        = obj
        self.parent_id  = parent_id
        self.description = f"Add {obj.type.value} '{obj.name}'"

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        canvas.objects[self.obj.id] = self.obj
        if self.parent_id and self.parent_id in canvas.objects:
            parent = canvas.objects[self.parent_id]
            if self.obj.id not in parent.children_ids:
                parent.children_ids.append(self.obj.id)
            self.obj.parent_id = self.parent_id
        else:
            if self.obj.id not in canvas.root_ids:
                canvas.root_ids.append(self.obj.id)
            self.obj.parent_id = None
        canvas.recalc_z_indices()

    def undo(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        if self.parent_id and self.parent_id in canvas.objects:
            parent = canvas.objects[self.parent_id]
            parent.children_ids = [i for i in parent.children_ids
                                    if i != self.obj.id]
        else:
            canvas.root_ids = [i for i in canvas.root_ids if i != self.obj.id]
        canvas.objects.pop(self.obj.id, None)
        canvas.recalc_z_indices()


class DeleteObjectCommand(Command):
    def __init__(self, canvas_id: str, obj_id: str):
        self.canvas_id   = canvas_id
        self.obj_id      = obj_id
        self._saved_obj  = None
        self._saved_parent_children: list[str] = []
        self._saved_root: list[str] = []
        self.description = "Delete object"

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        obj = canvas.objects.get(self.obj_id)
        if not obj:
            return
        self._saved_obj = deepcopy(obj)
        self._saved_root = list(canvas.root_ids)
        if obj.parent_id and obj.parent_id in canvas.objects:
            parent = canvas.objects[obj.parent_id]
            self._saved_parent_children = list(parent.children_ids)
            parent.children_ids = [i for i in parent.children_ids
                                    if i != self.obj_id]
        else:
            canvas.root_ids = [i for i in canvas.root_ids if i != self.obj_id]
        canvas.objects.pop(self.obj_id)
        self.description = f"Delete '{obj.name}'"
        canvas.recalc_z_indices()

    def undo(self, doc: "DocumentState"):
        if not self._saved_obj:
            return
        canvas = doc.canvases[self.canvas_id]
        canvas.objects[self.obj_id] = self._saved_obj
        if self._saved_obj.parent_id and \
                self._saved_obj.parent_id in canvas.objects:
            parent = canvas.objects[self._saved_obj.parent_id]
            parent.children_ids = self._saved_parent_children
        else:
            canvas.root_ids = self._saved_root
        canvas.recalc_z_indices()


class MoveObjectCommand(Command):
    """
    Двигает объект и рекурсивно всех его потомков на тот же delta.
    Координаты в DocumentState — абсолютные, поэтому дочерние
    элементы должны сдвигаться вместе с родителем.
    """
    def __init__(self, canvas_id: str, obj_id: str,
                 new_x: float, new_y: float):
        self.canvas_id = canvas_id
        self.obj_id    = obj_id
        self.new_x     = new_x
        self.new_y     = new_y
        # saved: {obj_id: (old_x, old_y)} для всего поддерева
        self._saved: dict[str, tuple[float, float]] = {}
        self.description = "Move object"

    def _collect_subtree(self, canvas, obj_id: str) -> list[str]:
        """DFS: объект + все потомки."""
        result = []
        stack = [obj_id]
        while stack:
            oid = stack.pop()
            result.append(oid)
            obj = canvas.objects.get(oid)
            if obj:
                stack.extend(obj.children_ids)
        return result

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        root_obj = canvas.objects[self.obj_id]
        dx = self.new_x - root_obj.transform.x
        dy = self.new_y - root_obj.transform.y

        # Сохраняем старые позиции всего поддерева
        self._saved.clear()
        for oid in self._collect_subtree(canvas, self.obj_id):
            obj = canvas.objects.get(oid)
            if obj:
                self._saved[oid] = (obj.transform.x, obj.transform.y)

        # Двигаем всё поддерево на delta
        for oid, (ox, oy) in self._saved.items():
            obj = canvas.objects.get(oid)
            if obj:
                obj.transform.x = ox + dx
                obj.transform.y = oy + dy

    def undo(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        for oid, (ox, oy) in self._saved.items():
            obj = canvas.objects.get(oid)
            if obj:
                obj.transform.x = ox
                obj.transform.y = oy


class ResizeObjectCommand(Command):
    def __init__(self, canvas_id: str, obj_id: str,
                 x: float, y: float, w: float, h: float):
        self.canvas_id = canvas_id
        self.obj_id = obj_id
        self.new_x, self.new_y, self.new_w, self.new_h = x, y, w, h
        self._old: tuple = (0, 0, 0, 0)
        self.description = "Resize object"

    def execute(self, doc: "DocumentState"):
        t = doc.canvases[self.canvas_id].objects[self.obj_id].transform
        self._old = (t.x, t.y, t.width, t.height)
        t.x, t.y, t.width, t.height = self.new_x, self.new_y, self.new_w, self.new_h

    def undo(self, doc: "DocumentState"):
        t = doc.canvases[self.canvas_id].objects[self.obj_id].transform
        t.x, t.y, t.width, t.height = self._old


class UpdatePropertiesCommand(Command):
    def __init__(self, canvas_id: str, obj_id: str, updates: dict):
        self.canvas_id = canvas_id
        self.obj_id    = obj_id
        self.updates   = updates
        self._old_values: dict = {}
        self.description = "Update properties"

    def _apply(self, obj: "ObjectState", updates: dict):
        for key, value in updates.items():
            if "." in key:
                attr, sub = key.split(".", 1)
                target = getattr(obj, attr)
                setattr(target, sub, value)
            elif key == "name":
                obj.name = value
            elif key == "visible":
                obj.visible = value
            elif key == "locked":
                obj.locked = value
            elif key == "payload_text":
                from domain.models import TextPayload
                if isinstance(obj.payload, TextPayload):
                    obj.payload.text = value
            elif key == "payload_image":
                from domain.models import ImagePayload
                if isinstance(obj.payload, ImagePayload):
                    obj.payload.source_path = value

    def _snapshot(self, obj: "ObjectState") -> dict:
        snap = {}
        for key in self.updates:
            if "." in key:
                attr, sub = key.split(".", 1)
                snap[key] = getattr(getattr(obj, attr), sub)
            elif key == "name":
                snap[key] = obj.name
            elif key == "visible":
                snap[key] = obj.visible
            elif key == "locked":
                snap[key] = obj.locked
            elif key == "payload_text":
                from domain.models import TextPayload
                if isinstance(obj.payload, TextPayload):
                    snap[key] = obj.payload.text
            elif key == "payload_image":
                from domain.models import ImagePayload
                if isinstance(obj.payload, ImagePayload):
                    snap[key] = obj.payload.source_path
        return snap

    def execute(self, doc: "DocumentState"):
        obj = doc.canvases[self.canvas_id].objects[self.obj_id]
        self._old_values = self._snapshot(obj)
        self._apply(obj, self.updates)

    def undo(self, doc: "DocumentState"):
        obj = doc.canvases[self.canvas_id].objects[self.obj_id]
        self._apply(obj, self._old_values)


class ReparentObjectCommand(Command):
    def __init__(self, canvas_id: str, obj_id: str,
                 new_parent_id: str | None, index: int = -1):
        self.canvas_id     = canvas_id
        self.obj_id        = obj_id
        self.new_parent_id = new_parent_id
        self.index         = index
        self._old_parent_id: str | None = None
        self._old_root: list[str] = []
        self._old_parent_children: list[str] = []
        self.description = "Reparent object"

    def _remove_from_current(self, canvas, obj):
        if obj.parent_id and obj.parent_id in canvas.objects:
            p = canvas.objects[obj.parent_id]
            self._old_parent_children = list(p.children_ids)
            p.children_ids = [i for i in p.children_ids if i != self.obj_id]
        else:
            self._old_root = list(canvas.root_ids)
            canvas.root_ids = [i for i in canvas.root_ids if i != self.obj_id]

    def _add_to_parent(self, canvas, obj, parent_id, index):
        if parent_id and parent_id in canvas.objects:
            parent = canvas.objects[parent_id]
            if index < 0 or index >= len(parent.children_ids):
                parent.children_ids.append(self.obj_id)
            else:
                parent.children_ids.insert(index, self.obj_id)
            obj.parent_id = parent_id
        else:
            if index < 0 or index >= len(canvas.root_ids):
                canvas.root_ids.append(self.obj_id)
            else:
                canvas.root_ids.insert(index, self.obj_id)
            obj.parent_id = None

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        obj = canvas.objects[self.obj_id]
        self._old_parent_id = obj.parent_id
        self._remove_from_current(canvas, obj)
        self._add_to_parent(canvas, obj, self.new_parent_id, self.index)
        canvas.recalc_z_indices()

    def undo(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        obj = canvas.objects[self.obj_id]
        if self.new_parent_id and self.new_parent_id in canvas.objects:
            p = canvas.objects[self.new_parent_id]
            p.children_ids = [i for i in p.children_ids if i != self.obj_id]
        else:
            canvas.root_ids = [i for i in canvas.root_ids if i != self.obj_id]
        if self._old_parent_id and self._old_parent_id in canvas.objects:
            p = canvas.objects[self._old_parent_id]
            p.children_ids = self._old_parent_children
            obj.parent_id = self._old_parent_id
        else:
            canvas.root_ids = self._old_root
            obj.parent_id = None
        canvas.recalc_z_indices()


class DuplicateObjectCommand(Command):
    def __init__(self, canvas_id: str, obj_id: str):
        self.canvas_id = canvas_id
        self.obj_id    = obj_id
        self._new_obj  = None
        self.description = "Duplicate object"

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        obj = canvas.objects[self.obj_id]
        self._new_obj = obj.copy()
        self._new_obj.transform.x += 20
        self._new_obj.transform.y += 20
        canvas.objects[self._new_obj.id] = self._new_obj
        if obj.parent_id and obj.parent_id in canvas.objects:
            parent = canvas.objects[obj.parent_id]
            parent.children_ids.append(self._new_obj.id)
            self._new_obj.parent_id = obj.parent_id
        else:
            canvas.root_ids.append(self._new_obj.id)
            self._new_obj.parent_id = None
        canvas.recalc_z_indices()

    def undo(self, doc: "DocumentState"):
        if not self._new_obj:
            return
        canvas = doc.canvases[self.canvas_id]
        if self._new_obj.parent_id in canvas.objects:
            p = canvas.objects[self._new_obj.parent_id]
            p.children_ids = [i for i in p.children_ids
                               if i != self._new_obj.id]
        else:
            canvas.root_ids = [i for i in canvas.root_ids
                                if i != self._new_obj.id]
        canvas.objects.pop(self._new_obj.id, None)
        canvas.recalc_z_indices()


class ReorderObjectCommand(Command):
    """Move object up/down in z-order within its parent."""
    def __init__(self, canvas_id: str, obj_id: str, direction: int):
        self.canvas_id = canvas_id
        self.obj_id    = obj_id
        self.direction = direction  # -1=up(forward), +1=down(backward)
        self._old_list: list[str] = []
        self.description = "Reorder layer"

    def _get_list(self, canvas) -> list[str]:
        obj = canvas.objects[self.obj_id]
        if obj.parent_id and obj.parent_id in canvas.objects:
            return canvas.objects[obj.parent_id].children_ids
        return canvas.root_ids

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        lst = self._get_list(canvas)
        self._old_list = list(lst)
        idx = lst.index(self.obj_id)
        new_idx = max(0, min(len(lst) - 1, idx + self.direction))
        lst.insert(new_idx, lst.pop(idx))
        canvas.recalc_z_indices()

    def undo(self, doc: "DocumentState"):
        canvas = doc.canvases[self.canvas_id]
        lst = self._get_list(canvas)
        lst[:] = self._old_list
        canvas.recalc_z_indices()


class TreeRearrangeCommand(Command):
    """
    Сохраняет полный снимок иерархии канваса (root_ids, parent_id,
    children_ids, z_index для каждого объекта) и восстанавливает его при undo.
    Используется после drag/drop в дереве элементов.
    """
    description = "Rearrange layers"

    def __init__(self, canvas_id: str, snapshot_before: dict, snapshot_after: dict):
        self.canvas_id       = canvas_id
        self._before         = snapshot_before   # {root_ids, objects: {id: {...}}}
        self._after          = snapshot_after

    @staticmethod
    def take_snapshot(canvas) -> dict:
        """Снимок иерархии канваса."""
        return {
            "root_ids": list(canvas.root_ids),
            "objects": {
                oid: {
                    "parent_id":    obj.parent_id,
                    "children_ids": list(obj.children_ids),
                    "z_index":      obj.z_index,
                }
                for oid, obj in canvas.objects.items()
            }
        }

    @staticmethod
    def apply_snapshot(canvas, snap: dict):
        canvas.root_ids = list(snap["root_ids"])
        for oid, s in snap["objects"].items():
            obj = canvas.objects.get(oid)
            if obj:
                obj.parent_id    = s["parent_id"]
                obj.children_ids = list(s["children_ids"])
                obj.z_index      = s["z_index"]

    def execute(self, doc: "DocumentState"):
        canvas = doc.canvases.get(self.canvas_id)
        if canvas:
            self.apply_snapshot(canvas, self._after)

    def undo(self, doc: "DocumentState"):
        canvas = doc.canvases.get(self.canvas_id)
        if canvas:
            self.apply_snapshot(canvas, self._before)
