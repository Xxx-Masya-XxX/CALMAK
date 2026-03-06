"""Главное окно приложения."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QVBoxLayout, QPushButton, QFrame, QMessageBox, QMenu,
    QFileDialog, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction

from ..models import BaseObject, Canvas, TextObject
from ..core import ProjectManager
from .elements_frame import ElementsPanel
from .preview_frame import PreviewFrame
from .properties_frame import PropertiesPanel
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    # Стили для тем
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

        # Менеджер проекта
        self.project = ProjectManager()
        
        # Создаём меню
        self._create_menu_bar()

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаём сплиттер для панелей
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
        
        # Кнопка добавления объекта с меню
        self.add_object_btn = QPushButton("Добавить объект")
        self.add_object_btn.setMenu(self._create_object_menu())
        toolbar_layout.addWidget(self.add_object_btn)

        toolbar_layout.addStretch()

        # Кнопка экспорта
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
        self.elements_panel.canvas_selected.connect(self._on_canvas_selected)
        self.elements_panel.object_selected.connect(self._on_object_selected)
        self.elements_panel.canvas_context_menu.connect(self._on_canvas_context_menu)
        self.elements_panel.object_parent_changed.connect(self._on_object_parent_changed)
        self.elements_panel.add_child_requested.connect(self._on_add_child_requested)

        self.preview_frame.object_selected.connect(self._on_object_selected)
        self.preview_frame.object_moved.connect(self._on_object_moved)
        
        self.properties_panel.canvas_changed.connect(self._on_canvas_changed)
        self.properties_panel.object_changed.connect(self._on_object_changed)
        
        # Добавляем первый канвас
        self._add_canvas()
    
    def _create_object_menu(self) -> QMenu:
        """Создаёт меню для добавления объектов."""
        menu = QMenu(self)

        # Фигуры
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
        
        # Меню Настройки
        settings_menu = menubar.addMenu("Настройки")
        
        # Действие открытия настроек
        settings_action = QAction("Настройки...", self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)
        
        # Разделитель
        settings_menu.addSeparator()
        
        # Действие выхода
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        settings_menu.addAction(exit_action)
    
    def _open_settings(self):
        """Открывает диалог настроек."""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def apply_settings(self, style_name: str, theme_name: str):
        """Применяет настройки из диалога."""
        # Применяем стиль
        QApplication.setStyle(style_name)
        
        # Применяем тему
        is_dark = theme_name.lower() == "dark" or theme_name.lower() == "тёмная"
        
        if is_dark:
            self.setStyleSheet(self.DARK_THEME)
        else:
            self.setStyleSheet(self.LIGHT_THEME)
        
        # Обновляем стили для toolbar
        if hasattr(self, 'toolbar'):
            self.toolbar.setStyleSheet(
                "background-color: #3c3c3c; padding: 5px;" if is_dark else "background-color: #f0f0f0; padding: 5px;"
            )
    
    def _add_canvas(self):
        """Добавляет новый канвас."""
        canvas_count = len(self.project.get_all_canvases()) + 1
        canvas = Canvas(
            name=f"Canvas_{canvas_count}",
            width=800,
            height=600,
            background_color="#FFFFFF"
        )
        
        self.project.add_canvas(canvas)
        self.elements_panel.add_canvas(canvas)
        self.preview_frame.add_canvas(canvas)
        
        # Переключаемся на новый канвас
        self._select_canvas(canvas.id)
    
    def _add_object(self, obj_type: str = "rect", parent: BaseObject | None = None):
        """Добавляет новый объект на активный канвас."""
        canvas = self.project.get_active_canvas()
        if not canvas:
            QMessageBox.warning(self, "Внимание", "Сначала создайте канвас")
            return

        if obj_type == "text":
            obj_count = len([o for o in self.project.get_objects(canvas.id) if isinstance(o, TextObject)]) + 1
            obj = TextObject(
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
            obj_count = len(self.project.get_objects(canvas.id)) + 1
            
            # Определяем тип фигуры
            shape_type = "rect"
            name_prefix = "Object"
            if obj_type == "ellipse":
                shape_type = "ellipse"
                name_prefix = "Ellipse"
            elif obj_type == "triangle":
                shape_type = "triangle"
                name_prefix = "Triangle"
            
            obj = BaseObject(
                name=f"{name_prefix}_{obj_count}",
                x=50,
                y=50,
                width=100,
                height=100,
                color="#4CAF50",
                shape_type=shape_type
            )

        # Устанавливаем родителя если есть
        if parent:
            obj.parent_id = parent.id
            # Позиция относительно родителя (внутри)
            obj.x = parent.x + 20
            obj.y = parent.y + 20

        self.project.add_object(canvas.id, obj)
        self.elements_panel.add_object(canvas.id, obj)
        self.preview_frame.add_object(canvas.id, obj)
    
    def _select_canvas(self, canvas_id: str):
        """Переключается на указанный канвас."""
        self.project.set_active_canvas(canvas_id)
        canvas_item = self.elements_panel.tree._canvas_items.get(canvas_id)
        if canvas_item:
            self.elements_panel.tree.setCurrentItem(canvas_item)
        self.preview_frame.set_active_canvas(canvas_id)
    
    def _on_canvas_selected(self, canvas_id: str):
        """Обработчик выбора канваса."""
        canvas = self.project.get_canvas(canvas_id)
        if canvas:
            self.project.set_active_canvas(canvas_id)
            self.preview_frame.set_active_canvas(canvas_id)
            self.properties_panel.set_canvas(canvas)
    
    def _on_object_selected(self, obj: BaseObject):
        """Обработчик выбора объекта."""
        self.properties_panel.set_object(obj)

    def _on_object_moved(self, obj: BaseObject):
        """Обработчик перемещения объекта (обновление в реальном времени)."""
        self.properties_panel.update_object_position(obj)
    
    def _on_canvas_context_menu(self, target):
        """Обработчик контекстного меню канваса или объекта."""
        # Показываем меню с выбором типа объекта
        menu = QMenu(self)

        add_rect_action = menu.addAction("Квадрат")
        add_text_action = menu.addAction("Текст")

        # Определяем родителя
        parent = None
        if isinstance(target, Canvas):
            add_rect_action.triggered.connect(lambda: self._add_object("rect"))
            add_text_action.triggered.connect(lambda: self._add_object("text"))
        elif isinstance(target, BaseObject):
            parent = target
            add_rect_action.triggered.connect(lambda: self._add_object("rect", parent))
            add_text_action.triggered.connect(lambda: self._add_object("text", parent))

        menu.exec_(self.elements_panel.mapToGlobal(self.elements_panel.tree.viewport().rect().bottomRight()))
    
    def _on_canvas_changed(self, canvas: Canvas):
        """Обработчик изменения свойств канваса."""
        # Обновляем превью
        self.preview_frame.update_canvas(canvas.id)
        # Обновляем дерево
        self.elements_panel.update_canvas_name(canvas)
    
    def _on_object_changed(self, obj: BaseObject):
        """Обработчик изменения свойств объекта."""
        canvas_id = self.elements_panel.tree.get_canvas_id_for_object(obj)
        if canvas_id:
            # Обновляем превью
            self.preview_frame.update_object(canvas_id, obj)
            # Обновляем имя в дереве
            self.elements_panel.update_object_name(canvas_id, obj)

    def _on_object_parent_changed(self, obj: BaseObject):
        """Обработчик изменения родителя объекта."""
        canvas_id = self.elements_panel.tree.get_canvas_id_for_object(obj)
        if canvas_id:
            # Перестраиваем иерархию в превью
            scene = self.preview_frame.get_scene(canvas_id)
            if scene:
                scene.rebuild_object_parent(obj)

    def _on_add_child_requested(self, parent: BaseObject, obj_type: str):
        """Обработчик добавления дочернего объекта."""
        self._add_object(obj_type, parent)

    def _export_to_png(self):
        """Экспортирует активный канвас в PNG."""
        canvas = self.project.get_active_canvas()
        if not canvas:
            QMessageBox.warning(self, "Внимание", "Нет активного канваса для экспорта")
            return
        
        # Получаем сцену активного канваса
        scene = self.preview_frame.get_scene(canvas.id)
        if not scene:
            return
        
        # Открываем диалог сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт в PNG",
            f"{canvas.name}.png",
            "PNG Files (*.png)"
        )
        
        if not file_path:
            return
        
        # Снимаем выделение для чистого рендера
        scene.clear_selection()
        
        # Рендерим сцену в pixmap
        # Устанавливаем размер сцены равным размеру канваса
        scene.setSceneRect(0, 0, canvas.width, canvas.height)
        
        # Создаём pixmap нужного размера
        pixmap = QPixmap(int(canvas.width), int(canvas.height))
        pixmap.fill(QColor(canvas.background_color))
        
        # Рисуем сцену на pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter)
        painter.end()
        
        # Сохраняем в файл
        if pixmap.save(file_path):
            QMessageBox.information(self, "Успех", f"Канвас экспортирован в {file_path}")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить файл")
