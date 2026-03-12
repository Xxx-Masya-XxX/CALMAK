"""Патчи для preview_frame.py и main_window.py."""

# ===========================================================
# preview_frame.py — добавить сигналы и подключение
# ===========================================================

PREVIEW_FRAME_SIGNALS = """
    # Добавить к существующим сигналам PreviewFrame:
    object_selected         = Signal(BaseObject)
    object_moved            = Signal(BaseObject)
    zoom_changed            = Signal(float)
    object_resized          = Signal(BaseObject)           # ← новый
    object_geometry_changed = Signal(BaseObject)           # ← новый
"""

PREVIEW_FRAME_ADD_CANVAS = """
    # В методе add_canvas() добавить две строки после object_moved:
    scene.object_selected.connect(self.object_selected.emit)
    scene.object_moved.connect(self.object_moved.emit)
    scene.object_resized.connect(self.object_resized.emit)              # ← новый
    scene.object_geometry_changed.connect(self.object_geometry_changed.emit)  # ← новый
"""

# ===========================================================
# main_window.py — подключить и добавить обработчики
# ===========================================================

MAIN_WINDOW_CONNECT = """
    # В _connect_signals() добавить:
    self.preview_frame.object_resized.connect(self._on_object_resized)
    self.preview_frame.object_geometry_changed.connect(self._on_object_geometry_changed)
"""

MAIN_WINDOW_HANDLERS = """
    def _on_object_resized(self, obj: BaseObject):
        \"\"\"Финальное обновление после окончания resize.\"\"\"
        canvas_id = self.elements_panel.tree._model.get_canvas_id_for_obj(obj)
        if canvas_id:
            self.preview_frame.update_object(canvas_id, obj)
        self.properties_panel.update_object_geometry(obj)

    def _on_object_geometry_changed(self, obj: BaseObject):
        \"\"\"Real-time обновление панели свойств во время resize.\"\"\"
        self.properties_panel.update_object_geometry(obj)
"""

# ===========================================================
# properties_panel.py — добавить метод update_object_geometry
# ===========================================================

PROPERTIES_PANEL_METHOD = """
    def update_object_geometry(self, obj: BaseObject):
        \"\"\"Обновляет X, Y, ширину и высоту в TransformSection (real-time).\"\"\"
        if self._current_object and self._current_object.id == obj.id:
            t = self.transform
            t._blocking = True
            t.x_spin.setValue(obj.x)
            t.y_spin.setValue(obj.y)
            t.width_spin.setValue(obj.width)
            t.height_spin.setValue(obj.height)
            gx, gy = obj.get_global_position()
            t.global_label.setText(f\"{gx:.1f}, {gy:.1f}\")
            t._blocking = False
"""
