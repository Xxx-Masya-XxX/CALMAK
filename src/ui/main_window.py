"""Главное окно приложения."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt

from .menubar import AppMenuBar
from .preview.preview_frame import PreviewFrame
from .properties_panel import PropertiesPanel
from .toolbar import Toolbar
from .elements_panel import ElementsPanel
from .dialogs.settings_dialog import SettingsDialog

from ..models import Canvas, BaseObject, ShapeObject, TextObject
from ..config import load_settings


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self._settings = load_settings()
        self._is_dark  = self._settings.get("theme", "light") == "dark"
        if self._is_dark:
            self.setStyleSheet(self._dark_ss())

        self.setWindowTitle("CALMAK")
        self.resize(1400, 900)

        self._canvases: dict[str, Canvas] = {}
        self._active_canvas_id: str | None = None
        self._canvas_counter = 0

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _dark_ss(self) -> str:
        return """
            QMainWindow, QWidget { background-color: #2b2b2b; color: #fff; }
            QMenuBar              { background-color: #3c3c3c; color: #fff; }
            QMenuBar::item:selected { background-color: #505050; }
            QMenu                 { background-color: #3c3c3c; color: #fff; }
            QMenu::item:selected  { background-color: #505050; }
            QSplitter::handle     { background-color: #505050; }
            QTreeView             { background-color: #2b2b2b; color: #fff; border: none; }
            QTreeView::item:selected { background-color: #404040; }
            QScrollArea           { border: none; }
        """

    def _build_ui(self):
        self.setMenuBar(AppMenuBar(self))

        # Toolbar — фиксированная высота (задана внутри класса: 36 px)
        self.toolbar = Toolbar(self)

        central = QWidget()
        self.setCentralWidget(central)

        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Toolbar не растягивается (QSizePolicy.Fixed по вертикали внутри Toolbar)
        vbox.addWidget(self.toolbar)

        self.elements_panel   = ElementsPanel(self)
        self.preview_frame    = PreviewFrame(self)
        self.properties_panel = PropertiesPanel(self)

        self.toolbar.set_preview_frame(self.preview_frame)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.elements_panel)
        splitter.addWidget(self.preview_frame)
        splitter.addWidget(self.properties_panel)
        splitter.setSizes([250, 900, 300])
        splitter.setStretchFactor(1, 1)   # preview растягивается

        # Splitter занимает ВСЁ оставшееся место после toolbar
        vbox.addWidget(splitter, stretch=1)

        self._apply_theme()

    def _connect_signals(self):
        self.toolbar.canvas_added.connect(self._add_canvas)
        self.toolbar.add_rect.connect(lambda: self._add_shape("rect"))
        self.toolbar.add_ellipse.connect(lambda: self._add_shape("ellipse"))
        self.toolbar.add_triangle.connect(lambda: self._add_shape("triangle"))
        self.toolbar.add_text.connect(self._add_text)
        self.toolbar.export_clicked.connect(self._export_canvas)

        self.elements_panel.canvas_selected.connect(self._on_canvas_selected)
        self.elements_panel.object_selected.connect(self._on_obj_selected)
        self.elements_panel.delete_requested.connect(self._delete_item)

        self.preview_frame.object_selected.connect(self._on_obj_selected)
        self.preview_frame.object_moved.connect(self._on_obj_moved)
        self.preview_frame.object_geometry_changed.connect(self._on_obj_geometry)
        self.preview_frame.zoom_changed.connect(self.toolbar.update_zoom_label)

        self.properties_panel.object_property_changed.connect(self._on_prop_changed)

        mb = self.menuBar()
        if isinstance(mb, AppMenuBar):
            mb.settings_requested.connect(self._open_settings)
            mb.exit_requested.connect(self.close)

    def _apply_theme(self):
        self.toolbar.set_theme(self._is_dark)
        self.properties_panel.set_theme(self._is_dark)
        self.elements_panel.set_theme(self._is_dark)

    # ------------------------------------------------------------------
    # Канвасы
    # ------------------------------------------------------------------

    def _add_canvas(self):
        self._canvas_counter += 1
        canvas = Canvas(
            name=f"Canvas {self._canvas_counter}",
            width=2480, height=3508, background_color="#FFFFFF"
        )
        self._canvases[canvas.id] = canvas
        self._active_canvas_id = canvas.id
        self.elements_panel.add_canvas(canvas)
        self.preview_frame.add_canvas(canvas)
        self.preview_frame.set_active_canvas(canvas.id)

    def _remove_canvas(self, canvas_id: str):
        if canvas_id not in self._canvases:
            return
        if self._active_canvas_id == canvas_id:
            other = [c for c in self._canvases if c != canvas_id]
            self._active_canvas_id = other[0] if other else None
            if self._active_canvas_id:
                self.preview_frame.set_active_canvas(self._active_canvas_id)
        del self._canvases[canvas_id]
        self.elements_panel.remove_canvas(canvas_id)
        self.preview_frame.remove_canvas(canvas_id)

    def _get_active_canvas(self) -> Canvas | None:
        cid = self._active_canvas_id
        return self._canvases.get(cid) if cid else None

    def _get_active_canvas_id(self) -> str | None:
        return self._active_canvas_id

    def _on_canvas_selected(self, canvas_id: str):
        if canvas_id in self._canvases:
            self._active_canvas_id = canvas_id
            self.preview_frame.set_active_canvas(canvas_id)
            # Показываем свойства канваса в панели
            self.properties_panel.set_object(self._canvases[canvas_id])

    # ------------------------------------------------------------------
    # Объекты
    # ------------------------------------------------------------------

    def _add_shape(self, shape_type: str):
        canvas = self._get_active_canvas()
        if canvas is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте канвас!")
            return
        obj = ShapeObject(
            name=shape_type.capitalize(),
            x=100, y=100, width=200, height=200,
            shape_type=shape_type, color="#CCCCCC"
        )
        self._add_object(canvas.id, obj)

    def _add_text(self):
        canvas = self._get_active_canvas()
        if canvas is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала создайте канвас!")
            return
        obj = TextObject(
            name="Text", text="Ваш текст",
            x=100, y=100, width=400, height=100,
            font_size=48, text_color="#000000"
        )
        self._add_object(canvas.id, obj)

    def _add_object(self, canvas_id: str, obj: BaseObject):
        self.elements_panel.add_object(canvas_id, obj)
        self.preview_frame.add_object(canvas_id, obj)
        self.elements_panel.select_object(obj)
        self.preview_frame.select_object(canvas_id, obj)

    # ------------------------------------------------------------------
    # Обработчики событий
    # ------------------------------------------------------------------

    def _on_obj_selected(self, obj: BaseObject):
        self.properties_panel.set_object(obj)

    def _on_obj_moved(self, obj: BaseObject):
        """Объект перемещён — только обновляем числа в панели свойств."""
        self.properties_panel.refresh_values()
        canvas_id = self.elements_panel.get_canvas_id_for_object(obj)
        if canvas_id:
            self.elements_panel.update_object(canvas_id, obj)

    def _on_obj_geometry(self, obj: BaseObject):
        """Real-time resize."""
        self.properties_panel.refresh_values()

    def _on_prop_changed(self, obj, key: str, value):
        """Свойство изменено через панель — обновляем превью и дерево."""
        if isinstance(obj, Canvas):
            # Обновляем канвас на превью
            self.preview_frame.update_canvas(obj.id)
            # Обновляем имя в дереве если изменилось
            if key == "name":
                self.elements_panel.update_canvas_name(obj)
        elif isinstance(obj, BaseObject):
            canvas_id = self.elements_panel.get_canvas_id_for_object(obj)
            if canvas_id:
                self.preview_frame.update_object(canvas_id, obj)
                self.elements_panel.update_object(canvas_id, obj)

    def _delete_item(self, item):
        if isinstance(item, Canvas):
            if QMessageBox.question(
                self, "Подтверждение", f"Удалить канвас '{item.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self._remove_canvas(item.id)
        elif isinstance(item, BaseObject):
            canvas_id = self.elements_panel.get_canvas_id_for_object(item)
            if canvas_id:
                self.elements_panel.remove_object(canvas_id, item)
                self.preview_frame.remove_object(canvas_id, item)
                self.properties_panel.set_object(None)

    def _export_canvas(self):
        canvas = self._get_active_canvas()
        if canvas is None:
            QMessageBox.warning(self, "Предупреждение", "Нет активного канваса!")
            return
        scene = self.preview_frame.get_scene(canvas.id)
        if scene:
            self.toolbar.export_to_png(scene, canvas)

    # ------------------------------------------------------------------
    # Настройки
    # ------------------------------------------------------------------

    def apply_settings(self, style_name: str, theme_name: str):
        if style_name in ("Fusion", "Windows", "WindowsVista"):
            self.qApp.setStyle(style_name)
        is_dark = theme_name.lower() == "dark"
        if is_dark != self._is_dark:
            self._is_dark = is_dark
            self.setStyleSheet(self._dark_ss() if is_dark else "")
            self._apply_theme()

    def _open_settings(self):
        SettingsDialog(self).exec()

    def closeEvent(self, event):
        event.accept()