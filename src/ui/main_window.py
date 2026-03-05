"""Главное окно приложения для создания каллажей."""

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter, QFileDialog, QMessageBox, QMenuBar, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ..models.elements import Canvas, ImageElement, TextElement, ShapeElement
from .toolbar import Toolbar
from .elements_frame import ElementsFrame
from .preview_frame import PreviewFrame
from .properties_frame import PropertiesFrame


class MainWindow(QMainWindow):
    """Главное окно редактора каллажей."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор каллажей")
        self.setMinimumSize(1200, 800)
        
        self._current_canvas: Canvas | None = None
        self._selected_element = None
        
        self._init_ui()
        self._init_menu()
        self._connect_signals()
        
        # Создаём канвас по умолчанию
        self._create_new_canvas()
    
    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter для изменения размеров панелей
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель с toolbar и деревом элементов
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.toolbar = Toolbar()
        self.elements_frame = ElementsFrame()
        
        left_layout.addWidget(self.toolbar)
        left_layout.addWidget(self.elements_frame)
        
        # Центральная панель с предпросмотром
        self.preview_frame = PreviewFrame()
        
        # Правая панель со свойствами
        self.properties_frame = PropertiesFrame()
        
        # Добавляем панели в splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(self.preview_frame)
        splitter.addWidget(self.properties_frame)
        
        # Устанавливаем размеры splitter
        splitter.setStretchFactor(0, 0)  # Левая панель фиксированная
        splitter.setStretchFactor(1, 1)  # Центральная панель растягивается
        splitter.setStretchFactor(2, 0)  # Правая панель фиксированная
        
        main_layout.addWidget(splitter)
    
    def _init_menu(self):
        """Инициализация меню."""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        new_action = QAction("Новый", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._create_new_canvas)
        file_menu.addAction(new_action)
        
        open_action = QAction("Открыть...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("Экспорт как изображение...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_image)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Правка
        edit_menu = menubar.addMenu("Правка")
        
        delete_action = QAction("Удалить элемент", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self._delete_selected_element)
        edit_menu.addAction(delete_action)
        
        # Справка
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Подключение сигналов."""
        # Toolbar
        self.toolbar.add_canvas.connect(self._create_new_canvas)
        self.toolbar.add_image.connect(self._add_image)
        self.toolbar.add_text.connect(self._add_text)
        self.toolbar.add_rectangle.connect(lambda: self._add_shape("rectangle"))
        self.toolbar.add_ellipse.connect(lambda: self._add_shape("ellipse"))
        
        # Elements frame
        self.elements_frame.element_selected.connect(self._on_element_selected)
        self.elements_frame.element_deleted.connect(self._on_element_deleted)
        self.elements_frame.element_visibility_changed.connect(self._on_element_visibility_changed)
        
        # Preview frame
        self.preview_frame.element_moved.connect(self._on_element_moved)
        
        # Properties frame
        self.properties_frame.property_changed.connect(self._on_property_changed)
    
    def _create_new_canvas(self):
        """Создать новый канвас."""
        self._current_canvas = Canvas()
        self._selected_element = self._current_canvas
        
        self.elements_frame.set_canvas(self._current_canvas)
        self.preview_frame.set_canvas(self._current_canvas)
        self.properties_frame.set_element(self._current_canvas)
    
    def _add_image(self):
        """Добавить изображение."""
        if not self._current_canvas:
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            element = ImageElement(
                name=f"Image {len(self._current_canvas.children) + 1}",
                x=50,
                y=50,
                width=200,
                height=200,
                image_path=file_path
            )
            self._add_element_to_canvas(element)
    
    def _add_text(self):
        """Добавить текст."""
        if not self._current_canvas:
            return
        
        element = TextElement(
            name=f"Text {len(self._current_canvas.children) + 1}",
            x=50,
            y=50,
        )
        self._add_element_to_canvas(element)
    
    def _add_shape(self, shape_type: str):
        """Добавить фигуру."""
        if not self._current_canvas:
            return
        
        element = ShapeElement(
            name=f"Shape {len(self._current_canvas.children) + 1}",
            x=50,
            y=50,
            width=150,
            height=150,
            shape_type=shape_type
        )
        self._add_element_to_canvas(element)
    
    def _add_element_to_canvas(self, element):
        """Добавить элемент на канвас."""
        self._current_canvas.add_child(element)
        self._refresh_all()
        self._on_element_selected(element)
    
    def _refresh_all(self):
        """Обновить все панели."""
        self.elements_frame.refresh()
        self.preview_frame.refresh()
        if self._selected_element:
            self.properties_frame.refresh()
    
    def _on_element_selected(self, element):
        """Обработчик выбора элемента."""
        self._selected_element = element
        self.properties_frame.set_element(element)
    
    def _on_element_deleted(self, element_id: str):
        """Обработчик удаления элемента."""
        if not self._current_canvas:
            return
        
        self._current_canvas.remove_child(element_id)
        self._selected_element = None
        self._refresh_all()
        self.properties_frame.set_element(None)
    
    def _on_element_visibility_changed(self, element_id: str, visible: bool):
        """Обработчик изменения видимости элемента."""
        element = self._current_canvas.find_element(element_id)
        if element:
            element.visible = visible
            self._refresh_all()
    
    def _on_element_moved(self, element_id: str, x: float, y: float):
        """Обработчик перемещения элемента."""
        element = self._current_canvas.find_element(element_id)
        if element:
            element.x = x
            element.y = y
            # Обновляем только поля позиции в properties_frame
            self.properties_frame.update_position_fields(x, y)
    
    def _on_property_changed(self, element_id: str, property_name: str, value):
        """Обработчик изменения свойства элемента."""
        element = self._current_canvas.find_element(element_id)
        if element and hasattr(element, property_name):
            setattr(element, property_name, value)
            # Обновляем только дерево и превью, не properties_frame (чтобы не терять фокус)
            self.elements_frame.refresh()
            self.preview_frame.refresh()
    
    def _delete_selected_element(self):
        """Удалить выбранный элемент."""
        if self._selected_element and self._selected_element != self._current_canvas:
            self._on_element_deleted(self._selected_element.id)
    
    def _open_project(self):
        """Открыть проект."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть проект",
            "",
            "JSON (*.json)"
        )
        
        if file_path:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._current_canvas = Canvas.from_dict(data)
                self._selected_element = self._current_canvas
                self._refresh_all()
                self.properties_frame.set_element(self._current_canvas)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть проект: {e}")
    
    def _save_project(self):
        """Сохранить проект."""
        if not self._current_canvas:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить проект",
            "",
            "JSON (*.json)"
        )
        
        if file_path:
            try:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self._current_canvas.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить проект: {e}")
    
    def _export_image(self):
        """Экспортировать канвас как изображение."""
        if not self._current_canvas:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать как изображение",
            "",
            "PNG (*.png);;JPEG (*.jpg)"
        )
        
        if file_path:
            try:
                from PIL import Image, ImageDraw
                
                # Создаём изображение
                img = Image.new('RGBA', (int(self._current_canvas.width), int(self._current_canvas.height)), (255, 255, 255, 255))
                draw = ImageDraw.Draw(img)
                
                # Рисуем элементы (упрощённая версия)
                self._draw_elements(draw, self._current_canvas.children)
                
                # Сохраняем
                img.save(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать изображение: {e}")
    
    def _draw_elements(self, draw, elements):
        """Нарисовать элементы на PIL изображении."""
        for element in elements:
            if not element.visible:
                continue
            
            from ..models.elements import ImageElement, TextElement, ShapeElement
            
            if isinstance(element, ImageElement):
                if element.image_path:
                    try:
                        img = Image.open(element.image_path).convert('RGBA')
                        img = img.resize((int(element.width), int(element.height)))
                        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 0)), 1 - element.opacity)
                        img.paste(img, (int(element.x), int(element.y)), img)
                    except:
                        pass
            
            elif isinstance(element, TextElement):
                # PIL не поддерживает все шрифты без pillow-font
                draw.text(
                    (element.x, element.y),
                    element.text,
                    fill=element.color
                )
            
            elif isinstance(element, ShapeElement):
                coords = [element.x, element.y, element.x + element.width, element.y + element.height]
                
                if element.shape_type == "rectangle":
                    draw.rectangle(coords, fill=element.fill_color, outline=element.stroke_color, width=element.stroke_width)
                elif element.shape_type == "ellipse":
                    draw.ellipse(coords, fill=element.fill_color, outline=element.stroke_color, width=element.stroke_width)
            
            # Рекурсивно рисуем дочерние элементы
            if hasattr(element, 'children'):
                self._draw_elements(draw, element.children)
    
    def _show_about(self):
        """Показать диалог о программе."""
        QMessageBox.about(
            self,
            "О программе",
            "Редактор каллажей\n\nСоздавайте красивые композиции из изображений, текста и фигур."
        )
