"""Панель инструментов с кнопками для добавления элементов."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal


class Toolbar(QWidget):
    """Панель инструментов для добавления элементов на канвас."""
    
    # Сигналы для добавления элементов
    add_canvas = Signal()
    add_image = Signal()
    add_text = Signal()
    add_rectangle = Signal()
    add_ellipse = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(120)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Заголовок
        title = QLabel("Добавить")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Кнопки
        self.btn_canvas = QPushButton("📄 Канвас")
        self.btn_canvas.clicked.connect(self.add_canvas.emit)
        layout.addWidget(self.btn_canvas)
        
        self.btn_image = QPushButton("🖼️ Картинка")
        self.btn_image.clicked.connect(self.add_image.emit)
        layout.addWidget(self.btn_image)
        
        self.btn_text = QPushButton("📝 Текст")
        self.btn_text.clicked.connect(self.add_text.emit)
        layout.addWidget(self.btn_text)
        
        self.btn_rectangle = QPushButton("⬜ Прямоуг.")
        self.btn_rectangle.clicked.connect(self.add_rectangle.emit)
        layout.addWidget(self.btn_rectangle)
        
        self.btn_ellipse = QPushButton("⭕ Эллипс")
        self.btn_ellipse.clicked.connect(self.add_ellipse.emit)
        layout.addWidget(self.btn_ellipse)
        
        layout.addStretch()
