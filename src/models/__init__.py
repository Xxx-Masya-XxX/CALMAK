"""Модели приложения."""

from .canvas import Canvas
from .objects import BaseObject, TextObject, ImageObject, ShapeObject

__all__ = ["Canvas", "BaseObject", "TextObject", "ImageObject", "ShapeObject"]
