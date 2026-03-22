"""
ProjectSerializer — сохраняет/загружает проект в JSON.
Формат: .cep (Canvas Editor Project)
"""
from __future__ import annotations
import json
from domain.models import (
    DocumentState, CanvasState, ObjectState, ObjectType,
    Transform, StyleState,
    TextPayload, ImagePayload, ShapePayload, GroupPayload,
    BezierPayload, BezierPoint, gen_id
)


class ProjectSerializer:

    @staticmethod
    def save(doc: DocumentState, path: str):
        data = {
            "version": "1.0",
            "active_canvas_id": doc.active_canvas_id,
            "canvases": {
                cid: ProjectSerializer._canvas_to_dict(canvas)
                for cid, canvas in doc.canvases.items()
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(path: str) -> DocumentState:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc = DocumentState()
        for cid, cdata in data.get("canvases", {}).items():
            canvas = ProjectSerializer._canvas_from_dict(cdata)
            doc.canvases[cid] = canvas

        active = data.get("active_canvas_id")
        if active and active in doc.canvases:
            doc.active_canvas_id = active
        elif doc.canvases:
            doc.active_canvas_id = next(iter(doc.canvases))

        return doc

    # -----------------------------------------------------------------------

    @staticmethod
    def _canvas_to_dict(canvas: CanvasState) -> dict:
        return {
            "id": canvas.id,
            "name": canvas.name,
            "width": canvas.width,
            "height": canvas.height,
            "background": canvas.background,
            "root_ids": canvas.root_ids,
            "objects": {
                oid: ProjectSerializer._obj_to_dict(obj)
                for oid, obj in canvas.objects.items()
            }
        }

    @staticmethod
    def _canvas_from_dict(d: dict) -> CanvasState:
        canvas = CanvasState(
            id=d["id"],
            name=d["name"],
            width=d.get("width", 1920),
            height=d.get("height", 1080),
            background=d.get("background", "#1E1E2E"),
        )
        canvas.root_ids = d.get("root_ids", [])
        for oid, odata in d.get("objects", {}).items():
            obj = ProjectSerializer._obj_from_dict(odata)
            canvas.objects[oid] = obj
        return canvas

    @staticmethod
    def _obj_to_dict(obj: ObjectState) -> dict:
        payload_data = {}
        if isinstance(obj.payload, TextPayload):
            payload_data = {"text": obj.payload.text}
        elif isinstance(obj.payload, ImagePayload):
            payload_data = {"source_path": obj.payload.source_path}
        elif isinstance(obj.payload, BezierPayload):
            p = obj.payload
            payload_data = {
                "closed": p.closed,
                "points": [
                    {"x": pt.x, "y": pt.y,
                     "cx1": pt.cx1, "cy1": pt.cy1,
                     "cx2": pt.cx2, "cy2": pt.cy2,
                     "smooth": pt.smooth}
                    for pt in p.points
                ],
            }

        return {
            "id": obj.id,
            "type": obj.type.value,
            "name": obj.name,
            "parent_id": obj.parent_id,
            "children_ids": obj.children_ids,
            "visible": obj.visible,
            "locked": obj.locked,
            "z_index": obj.z_index,
            "transform": {
                "x": obj.transform.x,
                "y": obj.transform.y,
                "width": obj.transform.width,
                "height": obj.transform.height,
                "rotation": obj.transform.rotation,
                "opacity": obj.transform.opacity,
            },
            "style": {
                "fill_color": obj.style.fill_color,
                "stroke_color": obj.style.stroke_color,
                "stroke_width": obj.style.stroke_width,
                "corner_radius": obj.style.corner_radius,
                "font_family": obj.style.font_family,
                "font_size": obj.style.font_size,
                "text_color": obj.style.text_color,
                "text_align": obj.style.text_align,
                "bold": obj.style.bold,
                "italic": obj.style.italic,
            },
            "payload": payload_data,
        }

    @staticmethod
    def _obj_from_dict(d: dict) -> ObjectState:
        obj_type = ObjectType(d["type"])

        t_data = d.get("transform", {})
        transform = Transform(
            x=t_data.get("x", 0),
            y=t_data.get("y", 0),
            width=t_data.get("width", 100),
            height=t_data.get("height", 100),
            rotation=t_data.get("rotation", 0),
            opacity=t_data.get("opacity", 1.0),
        )

        s_data = d.get("style", {})
        style = StyleState(
            fill_color=s_data.get("fill_color", "#4A90E2"),
            stroke_color=s_data.get("stroke_color", "#2C5F8A"),
            stroke_width=s_data.get("stroke_width", 1.0),
            corner_radius=s_data.get("corner_radius", 0.0),
            font_family=s_data.get("font_family", "Arial"),
            font_size=s_data.get("font_size", 16),
            text_color=s_data.get("text_color", "#FFFFFF"),
            text_align=s_data.get("text_align", "left"),
            bold=s_data.get("bold", False),
            italic=s_data.get("italic", False),
        )

        p_data = d.get("payload", {})
        if obj_type == ObjectType.TEXT:
            payload = TextPayload(text=p_data.get("text", ""))
        elif obj_type == ObjectType.IMAGE:
            payload = ImagePayload(source_path=p_data.get("source_path", ""))
        elif obj_type == ObjectType.BEZIER:
            from domain.models import BezierPoint
            pts = [
                BezierPoint(
                    x=pt.get("x", 0), y=pt.get("y", 0),
                    cx1=pt.get("cx1", 0), cy1=pt.get("cy1", 0),
                    cx2=pt.get("cx2", 0), cy2=pt.get("cy2", 0),
                    smooth=pt.get("smooth", True),
                )
                for pt in p_data.get("points", [])
            ]
            payload = BezierPayload(
                points=pts,
                closed=p_data.get("closed", False),
            )
        elif obj_type == ObjectType.GROUP:
            payload = GroupPayload()
        else:
            payload = ShapePayload()

        obj = ObjectState(
            id=d["id"],
            type=obj_type,
            name=d.get("name", "Object"),
            parent_id=d.get("parent_id"),
            children_ids=d.get("children_ids", []),
            transform=transform,
            style=style,
            payload=payload,
            visible=d.get("visible", True),
            locked=d.get("locked", False),
            z_index=d.get("z_index", 0),
        )
        return obj
