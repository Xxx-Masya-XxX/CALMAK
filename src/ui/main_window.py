"""Главное окно приложения."""

import random

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QVBoxLayout, QPushButton, QFrame, QMessageBox, QMenu,
    QFileDialog, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction, QFont

from ..models import BaseObject, Canvas, TextObject
from ..controllers import SceneController
from ..services import export_to_png
from ..ui.panels import ElementsPanel, PropertiesPanel
from ..ui.preview import PreviewFrame
from ..ui.dialogs import SettingsDialog
from ..config import load_settings, save_settings


def _random_color() -> str:
    """Генерирует случайный яркий цвет в формате HEX."""
    h = random.randint(0, 360)
    s = random.randint(60, 100)
    l = random.randint(45, 65)

    c = (1 - abs(2 * l / 100 - 1)) * s / 100
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l / 100 - c / 2

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)

    return f"#{r:02X}{g:02X}{b:02X}"


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    LIGHT_THEME = """
        QMainWindow { background-color: #ffffff; }
        QTreeWidget { background-color: #ffffff; color: #000000; }
        QGraphicsView { background-color: #e0e0e0; }
        QGroupBox { color: #000000; }
        QLabel { color: #000000; }
        QComboBox { color: #000000; background-color: #ffffff; }
        QSpinBox { color: #000000; background-color: #ffffff; }
        QLineEdit { color: #000000; background-color: #ffffff; }
        QCheckBox { color: #000000; }
        QMenu { background-color: #ffffff; color: #000000; }
        QMenu::item:selected { background-color: #e0e0e0; }
        QMenuBar { background-color: #ffffff; color: #000000; }
        QMenuBar::item:selected { background-color: #e0e0e0; }
        QDialog { background-color: #ffffff; color: #000000; }
    """

    DARK_THEME = """
        QMainWindow { background-color: #2b2b2b; }
        QTreeWidget { background-color: #3c3c3c; color: #ffffff; }
        QGraphicsView { background-color: #1e1e1e; }
        QGroupBox { color: #ffffff; }
        QLabel { color: #ffffff; }
        QComboBox { color: #ffffff; background-color: #3c3c3c; }
        QSpinBox { color: #ffffff; background-color: #3c3c3c; }
        QLineEdit { color: #ffffff; background-color: #3c3c3c; }
        QCheckBox { color: #ffffff; }
        QMenu { background-color: #3c3c3c; color: #ffffff; }
        QMenu::item:selected { background-color: #505050; }
        QMenuBar { background-color: #3c3c3c; color: #ffffff; }
        QMenuBar::item:selected { background-color: #505050; }
        QDialog { background-color: #2b2b2b; color: #ffffff; }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CALMAK - Редактор")
        self.setMinimumSize(1200, 800)

        # Контроллер сцены
        self.controller = SceneController()

        # Меню
        self._create_menu_bar()

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Сплиттер
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Левая панель - дерево объектов
        self.elements_panel = ElementsPanel(self)
        self.elements_panel.setMinimumWidth(200)
        self.elements_panel.setMaximumWidth(400)
        self.elements_panel.tree.setToolTip(
            "Правый клик на объекте:\n"
            "• 'Добавить в объект' — создать дочерний объект\n"
            "• 'Сделать родителем' — сделать этот объект родителем для другого\n"
            "Дочерние объекты перемещаются вместе с родителем"
        )
        splitter.addWidget(self.elements_panel)

        # Центральная панель - превью
        preview_container = QFrame()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # Панель инструментов превью
        self.toolbar = QFrame()
        self.toolbar.setObjectName("toolbar")
        self.toolbar.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)

        self.add_canvas_btn = QPushButton("Добавить канвас")
        self.add_canvas_btn.clicked.connect(self._add_canvas)
        toolbar_layout.addWidget(self.add_canvas_btn)

        self.add_object_btn = QPushButton("Добавить объект")
        self.add_object_btn.setMenu(self._create_object_menu())
        toolbar_layout.addWidget(self.add_object_btn)

        toolbar_layout.addStretch()

        # Кнопки управления зумом
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.zoom_out_btn.setToolTip("Уменьшить масштаб (Ctrl + колесо вниз)")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar_layout.addWidget(self.zoom_out_btn)

        self.zoom_value_label = QPushButton("100%")
        self.zoom_value_label.setFixedSize(50, 30)
        self.zoom_value_label.setToolTip("Текущий масштаб")
        self.zoom_value_label.clicked.connect(self._reset_zoom)
        toolbar_layout.addWidget(self.zoom_value_label)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.zoom_in_btn.setToolTip("Увеличить масштаб (Ctrl + колесо вверх)")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar_layout.addWidget(self.zoom_in_btn)

        self.export_btn = QPushButton("Экспорт в PNG")
        self.export_btn.clicked.connect(self._export_to_png)
        toolbar_layout.addWidget(self.export_btn)

        preview_layout.addWidget(self.toolbar)

        self.preview_frame = PreviewFrame(self)
        preview_layout.addWidget(self.preview_frame, 1)

        splitter.addWidget(preview_container)
        splitter.setStretchFactor(1, 1)

        # Правая панель - свойства
        self.properties_panel = PropertiesPanel(self)
        self.properties_panel.setMinimumWidth(250)
        self.properties_panel.setMaximumWidth(400)
        splitter.addWidget(self.properties_panel)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)

        # Подключаем сигналы
        self._connect_signals()

        # Загружаем настройки
        self.load_settings()

        # Добавляем первый канвас
        self._add_canvas()

    def _connect_signals(self):
        """Подключает сигналы между компонентами."""
        # Элементы панели
        self.elements_panel.canvas_selected.connect(self._on_canvas_selected)
        self.elements_panel.object_selected.connect(self._on_object_selected)
        self.elements_panel.canvas_context_menu.connect(self._on_canvas_context_menu)
        self.elements_panel.object_parent_changed.connect(self._on_object_parent_changed)
        self.elements_panel.add_child_requested.connect(self._on_add_child_requested)

        # Превью
        self.preview_frame.object_selected.connect(self._on_object_selected)
        self.preview_frame.object_moved.connect(self._on_object_moved)

        # Панель свойств
        self.properties_panel.canvas_changed.connect(self._on_canvas_changed)
        self.properties_panel.object_changed.connect(self._on_object_changed)
        self.properties_panel.request_objects_list.connect(self._on_request_objects_list)

        # Контроллер сцены
        self.controller.set_canvas_added_callback(self._on_canvas_added)
        self.controller.set_canvas_removed_callback(self._on_canvas_removed)
        self.controller.set_object_added_callback(self._on_object_added)
        self.controller.set_object_removed_callback(self._on_object_removed)

    def _create_object_menu(self) -> QMenu:
        """Создаёт меню для добавления объектов."""
        menu = QMenu(self)

        shapes_menu = menu.addMenu("Фигуры")
        add_rect_action = shapes_menu.addAction("Прямоугольник")
        add_rect_action.triggered.connect(lambda: self._add_object("rect"))
        add_ellipse_action = shapes_menu.addAction("Эллипс")
        add_ellipse_action.triggered.connect(lambda: self._add_object("ellipse"))
        add_triangle_action = shapes_menu.addAction("Треугольник")
        add_triangle_action.triggered.connect(lambda: self._add_object("triangle"))

        add_text_action = menu.addAction("Текст")
        add_text_action.triggered.connect(lambda: self._add_object("text"))

        return menu

    def _create_menu_bar(self):
        """Создаёт верхнее меню."""
        menubar = self.menuBar()

        settings_menu = menubar.addMenu("Настройки")

        settings_action = QAction("Настройки...", self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)

        settings_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        settings_menu.addAction(exit_action)

    def _open_settings(self):
        """Открывает диалог настроек."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def load_settings(self):
        """Загружает настройки."""
        settings = load_settings()
        style_name = settings.get("style", "Fusion")
        theme_name = settings.get("theme", "dark")
        self.apply_settings(style_name, theme_name)

    def apply_settings(self, style_name: str, theme_name: str):
        """Применяет настройки."""
        QApplication.setStyle(style_name)

        is_dark = theme_name.lower() == "dark" or theme_name.lower() == "тёмная"

        if is_dark:
            self.setStyleSheet(self.DARK_THEME)
        else:
            self.setStyleSheet(self.LIGHT_THEME)

        if hasattr(self, 'toolbar'):
            self.toolbar.setStyleSheet(
                "background-color: #3c3c3c; padding: 5px;" if is_dark else "background-color: #f0f0f0; padding: 5px;"
            )

    def _add_canvas(self):
        """Добавляет новый канвас."""
        canvas_count = len(self.controller.get_all_canvases()) + 1
        canvas = Canvas(
            name=f"Canvas_{canvas_count}",
            width=800,
            height=600,
            background_color="#FFFFFF"
        )

        self.controller.add_canvas(canvas)

    def _add_object(self, obj_type: str = "rect", parent: BaseObject | None = None):
        """Добавляет новый объект на активный канвас."""
        canvas = self.controller.get_active_canvas()
        if not canvas:
            QMessageBox.warning(self, "Внимание", "Сначала создайте канвас")
            return

        if obj_type == "text":
            obj_count = len([o for o in self.controller.get_objects(canvas.id) if isinstance(o, TextObject)]) + 1
            obj = self.controller.create_text_object(
                name=f"Text_{obj_count}",
                x=50,
                y=50,
                width=200,
                height=50,
                text="Hello World",
                font_family="Arial",
                font_size=16,
                text_color="#000000"
            )
        else:
            obj_count = len(self.controller.get_objects(canvas.id)) + 1

            shape_type = "rect"
            name_prefix = "Object"
            if obj_type == "ellipse":
                shape_type = "ellipse"
                name_prefix = "Ellipse"
            elif obj_type == "triangle":
                shape_type = "triangle"
                name_prefix = "Triangle"

            obj = self.controller.create_shape_object(
                name=f"{name_prefix}_{obj_count}",
                x=50,
                y=50,
                width=100,
                height=100,
                color=_random_color(),
                shape_type=shape_type
            )

        # Устанавливаем родителя если есть
        if parent:
            self.controller.set_parent(canvas.id, obj, parent)
            obj.x = 20
            obj.y = 20

        self.controller.add_object(canvas.id, obj)

    def _select_canvas(self, canvas_id: str):
        """Переключается на указанный канвас."""
        self.controller.set_active_canvas(canvas_id)
        canvas_item = self.elements_panel.tree._model._canvas_nodes.get(canvas_id)
        if canvas_item:
            self.elements_panel.tree.setCurrentIndex(self.elements_panel.tree._model.createIndex(
                canvas_item.row_in_parent, 0, canvas_item
            ))
        self.preview_frame.set_active_canvas(canvas_id)

    # === Обработчики событий ===

    def _on_canvas_added(self, canvas: Canvas):
        """Обработчик добавления канваса."""
        self.elements_panel.add_canvas(canvas)
        self.preview_frame.add_canvas(canvas)
        self._select_canvas(canvas.id)

    def _on_canvas_removed(self, canvas_id: str):
        """Обработчик удаления канваса."""
        self.elements_panel.remove_canvas(canvas_id)
        self.preview_frame.remove_canvas(canvas_id)

    def _on_canvas_selected(self, canvas_id: str):
        """Обработчик выбора канваса."""
        canvas = self.controller.get_canvas(canvas_id)
        if canvas:
            self.controller.set_active_canvas(canvas_id)
            self.preview_frame.set_active_canvas(canvas_id)
            self.properties_panel.set_canvas(canvas)
            self._update_zoom_label()

    def _on_object_selected(self, obj: BaseObject):
        """Обработчик выбора объекта."""
        self.properties_panel.set_object(obj)

    def _on_object_moved(self, obj: BaseObject):
        """Обработчик перемещения объекта."""
        self.properties_panel.update_object_position(obj)

    def _on_canvas_context_menu(self, target):
        """Обработчик контекстного меню канваса или объекта."""
        pass  # Меню обрабатывается в elements_panel

    def _on_canvas_changed(self, canvas: Canvas):
        """Обработчик изменения свойств канваса."""
        self.preview_frame.update_canvas(canvas.id)
        self.elements_panel.update_canvas_name(canvas)

    def _on_object_changed(self, obj: BaseObject):
        """Обработчик изменения свойств объекта."""
        canvas_id = self.elements_panel.tree._model.get_canvas_id_for_obj(obj)
        if canvas_id:
            self.preview_frame.update_object(canvas_id, obj)
            self.elements_panel.update_object_name(canvas_id, obj)

    def _on_object_parent_changed(self, obj: BaseObject):
        """Обработчик изменения родителя объекта."""
        canvas_id = self.elements_panel.tree._model.get_canvas_id_for_obj(obj)
        if canvas_id:
            scene = self.preview_frame.get_scene(canvas_id)
            if scene:
                scene.rebuild_object_parent(obj)

    def _on_request_objects_list(self):
        """Обработчик запроса списка объектов."""
        canvas = self.controller.get_active_canvas()
        if canvas:
            objects = self.controller.get_objects(canvas.id)
            self.properties_panel.set_objects_list(objects)

    def _on_add_child_requested(self, parent: BaseObject, obj_type: str):
        """Обработчик добавления дочернего объекта."""
        self._add_object(obj_type, parent)

    def _on_object_added(self, canvas_id: str, obj: BaseObject):
        """Обработчик добавления объекта."""
        self.elements_panel.add_object(canvas_id, obj)
        self.preview_frame.add_object(canvas_id, obj)

    def _on_object_removed(self, canvas_id: str, obj: BaseObject):
        """Обработчик удаления объекта."""
        self.elements_panel.remove_object(canvas_id, obj)
        self.preview_frame.remove_object(canvas_id, obj)

    def _export_to_png(self):
        """Экспортирует активный канвас в PNG."""
        canvas = self.controller.get_active_canvas()
        if not canvas:
            QMessageBox.warning(self, "Внимание", "Нет активного канваса для экспорта")
            return

        scene = self.preview_frame.get_scene(canvas.id)
        if not scene:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт в PNG",
            f"{canvas.name}.png",
            "PNG Files (*.png)"
        )

        if not file_path:
            return

        if export_to_png(scene, canvas, file_path):
            QMessageBox.information(self, "Успех", f"Канвас экспортирован в {file_path}")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить файл")

    def _get_active_canvas_id(self) -> str | None:
        """Возвращает ID активного канваса."""
        canvas = self.controller.get_active_canvas()
        return canvas.id if canvas else None

    def _update_zoom_label(self):
        """Обновляет метку масштаба."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id:
            zoom = self.preview_frame.get_zoom_factor(canvas_id)
            self.zoom_value_label.setText(f"{int(zoom * 100)}%")

    def _zoom_in(self):
        """Увеличивает масштаб."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id:
            self.preview_frame.zoom_in(canvas_id)
            self._update_zoom_label()

    def _zoom_out(self):
        """Уменьшает масштаб."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id:
            self.preview_frame.zoom_out(canvas_id)
            self._update_zoom_label()

    def _reset_zoom(self):
        """Сбрасывает масштаб к 100%."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id:
            self.preview_frame.reset_zoom(canvas_id)
            self._update_zoom_label()
