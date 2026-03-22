"""
Core domain models. No PySide6 here — pure Python data.
These are the single source of truth for the entire application.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4
from enum import Enum


def gen_id() -> str:
    return str(uuid4())[:8]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ObjectType(str, Enum):
    GROUP    = "group"
    RECT     = "rect"
    ELLIPSE  = "ellipse"
    TEXT     = "text"
    IMAGE    = "image"
    BEZIER   = "bezier"


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

@dataclass
class Transform:
    x: float       = 0.0
    y: float       = 0.0
    width: float   = 100.0
    height: float  = 100.0
    rotation: float = 0.0
    opacity: float  = 1.0

    def copy(self) -> "Transform":
        return Transform(
            self.x, self.y, self.width, self.height,
            self.rotation, self.opacity
        )


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

@dataclass
class StyleState:
    fill_color:   str   = "#4A90E2"
    stroke_color: str   = "#2C5F8A"
    stroke_width: float = 1.0
    corner_radius: float = 0.0
    # text-specific
    font_family: str  = "Arial"
    font_size:   int  = 16
    text_color:  str  = "#FFFFFF"
    text_align:  str  = "left"    # left / center / right
    bold:        bool = False
    italic:      bool = False

    def copy(self) -> "StyleState":
        s = StyleState()
        s.__dict__.update(self.__dict__)
        return s


# ---------------------------------------------------------------------------
# Object payloads
# ---------------------------------------------------------------------------

@dataclass
class TextPayload:
    text: str = "Text"

@dataclass
class ImagePayload:
    source_path: str = ""   # absolute path or ""

@dataclass
class GroupPayload:
    pass

@dataclass
class ShapePayload:
    pass

@dataclass
class BezierPoint:
    """
    Одна точка полилинии Безье.
      x, y      — позиция anchor-точки в абсолютных координатах сцены
      cx1, cy1  — контрольная точка «до» (входящий касательный вектор)
      cx2, cy2  — контрольная точка «после» (исходящий касательный вектор)
      smooth    — симметричные ручки (перемещение одной отражает другую)
    """
    x:   float = 0.0
    y:   float = 0.0
    cx1: float = 0.0   # = x по умолчанию (совмещена с anchor)
    cy1: float = 0.0
    cx2: float = 0.0
    cy2: float = 0.0
    smooth: bool = True

    def copy(self) -> "BezierPoint":
        from copy import copy as _copy
        return _copy(self)


@dataclass
class BezierPayload:
    """
    Произвольная кривая Безье из N точек в абсолютных координатах сцены.
    Каждая точка — BezierPoint с anchor + две контрольные ручки.
    closed — замкнуть контур.
    """
    points: list = field(default_factory=list)   # list[BezierPoint]
    closed: bool  = False

    def copy(self) -> "BezierPayload":
        return BezierPayload(
            points=[p.copy() for p in self.points],
            closed=self.closed
        )


# ---------------------------------------------------------------------------
# ObjectState
# ---------------------------------------------------------------------------

@dataclass
class ObjectState:
    id:          str
    type:        ObjectType
    name:        str
    parent_id:   Optional[str]        = None
    children_ids: list[str]           = field(default_factory=list)
    transform:   Transform            = field(default_factory=Transform)
    style:       StyleState           = field(default_factory=StyleState)
    payload:     object               = field(default_factory=ShapePayload)
    visible:     bool                 = True
    locked:      bool                 = False
    z_index:     int                  = 0    # глобальный z-order, пересчитывается из дерева

    def copy(self) -> "ObjectState":
        import copy
        obj = ObjectState(
            id=gen_id(),
            type=self.type,
            name=self.name + " Copy",
            parent_id=self.parent_id,
            children_ids=[],
            transform=self.transform.copy(),
            style=self.style.copy(),
            payload=copy.deepcopy(self.payload),
            visible=self.visible,
            locked=self.locked,
        )
        return obj


def make_rect(name="Rect", x=50, y=50, w=200, h=120,
              fill="#4A90E2", stroke="#2C5F8A") -> ObjectState:
    obj = ObjectState(
        id=gen_id(), type=ObjectType.RECT, name=name,
        transform=Transform(x=x, y=y, width=w, height=h),
        style=StyleState(fill_color=fill, stroke_color=stroke),
        payload=ShapePayload()
    )
    return obj

def make_ellipse(name="Ellipse", x=50, y=50, w=150, h=150,
                 fill="#E24A4A", stroke="#8A2C2C") -> ObjectState:
    obj = ObjectState(
        id=gen_id(), type=ObjectType.ELLIPSE, name=name,
        transform=Transform(x=x, y=y, width=w, height=h),
        style=StyleState(fill_color=fill, stroke_color=stroke),
        payload=ShapePayload()
    )
    return obj

def make_text(name="Text", text="Hello", x=50, y=50, w=200, h=40,
              color="#212121", font_size=18) -> ObjectState:
    obj = ObjectState(
        id=gen_id(), type=ObjectType.TEXT, name=name,
        transform=Transform(x=x, y=y, width=w, height=h),
        style=StyleState(fill_color="transparent", stroke_color="transparent",
                         stroke_width=0, text_color=color, font_size=font_size),
        payload=TextPayload(text=text)
    )
    return obj

def make_image(name="Image", path="", x=50, y=50, w=200, h=200) -> ObjectState:
    obj = ObjectState(
        id=gen_id(), type=ObjectType.IMAGE, name=name,
        transform=Transform(x=x, y=y, width=w, height=h),
        style=StyleState(fill_color="#CCCCCC", stroke_color="#999999"),
        payload=ImagePayload(source_path=path)
    )
    return obj

def make_group(name="Group", children: list[str] = None) -> ObjectState:
    obj = ObjectState(
        id=gen_id(), type=ObjectType.GROUP, name=name,
        children_ids=children or [],
        payload=GroupPayload()
    )
    return obj

def make_bezier(name="Bezier", x=100, y=100) -> ObjectState:
    """Кривая Безье с двумя начальными точками в абсолютных координатах."""
    p0 = BezierPoint(x=x,       y=y,
                     cx1=x-40,  cy1=y,
                     cx2=x+40,  cy2=y)
    p1 = BezierPoint(x=x+160,   y=y,
                     cx1=x+120, cy1=y,
                     cx2=x+200, cy2=y)
    obj = ObjectState(
        id=gen_id(),
        type=ObjectType.BEZIER,
        name=name,
        transform=Transform(x=x, y=y, width=1, height=1),
        style=StyleState(
            fill_color="transparent",
            stroke_color="#E2904A",
            stroke_width=2.5,
        ),
        payload=BezierPayload(points=[p0, p1]),
    )
    return obj


# ---------------------------------------------------------------------------
# CanvasState
# ---------------------------------------------------------------------------

@dataclass
class CanvasState:
    id:         str
    name:       str
    width:      int   = 1920
    height:     int   = 1080
    background: str   = "#FFFFFF"
    objects:    dict[str, ObjectState] = field(default_factory=dict)
    root_ids:   list[str]              = field(default_factory=list)

    def get_object(self, obj_id: str) -> Optional[ObjectState]:
        return self.objects.get(obj_id)

    def recalc_z_indices(self):
        """
        Пересчитывает z_index всех объектов из текущего дерева.

        Правила:
          - root_ids[0] = нижний слой → z_index=0
          - root_ids[-1] = верхний слой → наибольший z_index
          - дети всегда рендерятся ВЫШЕ своего родителя
          - внутри одного родителя: children_ids[0]=нижний, children_ids[-1]=верхний

        Алгоритм: DFS обход, родитель получает z перед детьми,
        затем дети получают следующие z (поверх родителя).

        Пример (root_ids = [r1, r2], r2.children = [t1]):
          r1 → z=0  (нижний)
          r2 → z=1  (выше r1)
          t1 → z=2  (ребёнок r2, выше родителя)
        """
        counter = [0]

        def assign(obj_id: str):
            obj = self.objects.get(obj_id)
            if not obj:
                return
            # Родитель получает z первым
            obj.z_index = counter[0]
            counter[0] += 1
            # Затем дети — они рендерятся поверх родителя
            for child_id in obj.children_ids:
                assign(child_id)

        # root_ids[0] = нижний → получает z=0
        for obj_id in self.root_ids:
            assign(obj_id)

    def all_ids_ordered(self) -> list[str]:
        """DFS traversal root→children — для итерации по всем объектам."""
        result = []
        def walk(ids):
            for oid in ids:
                result.append(oid)
                obj = self.objects.get(oid)
                if obj and obj.children_ids:
                    walk(obj.children_ids)
        walk(self.root_ids)
        return result


# ---------------------------------------------------------------------------
# DocumentState
# ---------------------------------------------------------------------------

@dataclass
class DocumentState:
    canvases:          dict[str, CanvasState] = field(default_factory=dict)
    active_canvas_id:  Optional[str]           = None
    file_path:         Optional[str]           = None
    dirty:             bool                    = False

    @property
    def active_canvas(self) -> Optional[CanvasState]:
        if self.active_canvas_id:
            return self.canvases.get(self.active_canvas_id)
        return None

    def add_canvas(self, canvas: CanvasState):
        self.canvases[canvas.id] = canvas
        if self.active_canvas_id is None:
            self.active_canvas_id = canvas.id

    def create_default_canvas(self) -> CanvasState:
        canvas = CanvasState(id=gen_id(), name="Canvas 1", width=1920, height=1080)
        self.add_canvas(canvas)
        return canvas


# ---------------------------------------------------------------------------
# SelectionState
# ---------------------------------------------------------------------------

@dataclass
class SelectionState:
    selected_ids: list[str]    = field(default_factory=list)
    active_id:    Optional[str] = None

    def set(self, ids: list[str]):
        self.selected_ids = list(ids)
        self.active_id = ids[0] if ids else None

    def clear(self):
        self.selected_ids = []
        self.active_id = None

    def is_selected(self, obj_id: str) -> bool:
        return obj_id in self.selected_ids

    def toggle(self, obj_id: str):
        if obj_id in self.selected_ids:
            self.selected_ids.remove(obj_id)
        else:
            self.selected_ids.append(obj_id)
        self.active_id = self.selected_ids[-1] if self.selected_ids else None
