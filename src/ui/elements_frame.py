"""Панель элементов с деревом объектов канваса."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu
from PySide6.QtCore import Signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.elements import CanvasElement


class ElementsFrame(QWidget):
    """Панель с деревом элементов канваса."""
    
    # Сигналы
    element_selected = Signal(object)  # CanvasElement
    element_deleted = Signal(str)  # element_id
    element_visibility_changed = Signal(str, bool)  # element_id, visible
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self._init_ui()
        self._current_canvas = None
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Заголовок
        from PySide6.QtWidgets import QLabel
        title = QLabel("Элементы")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Дерево элементов
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Название", "Тип"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)
    
    def set_canvas(self, canvas: "CanvasElement") -> None:
        """Установить канвас и обновить дерево."""
        self._current_canvas = canvas
        self._rebuild_tree()
    
    def _rebuild_tree(self) -> None:
        """Перестроить дерево элементов."""
        self.tree.clear()
        if not self._current_canvas:
            return
        
        # Добавляем корневой канвас
        root_item = self._create_tree_item(self._current_canvas)
        self.tree.addTopLevelItem(root_item)
        self._add_children(root_item, self._current_canvas.children)
        self.tree.expandAll()
    
    def _create_tree_item(self, element: "CanvasElement") -> QTreeWidgetItem:
        """Создать элемент дерева для элемента канваса."""
        type_icons = {
            "Canvas": "📄",
            "ImageElement": "🖼️",
            "TextElement": "📝",
            "ShapeElement": "⬜",
        }
        type_name = type(element).__name__
        icon = type_icons.get(type_name, "•")
        
        item = QTreeWidgetItem([element.name, icon])
        item.setData(0, Qt.UserRole, element)
        
        # Показываем иконку видимости
        if not element.visible:
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
        
        return item
    
    def _add_children(self, parent_item: QTreeWidgetItem, children: list["CanvasElement"]) -> None:
        """Добавить дочерние элементы в дерево."""
        for child in children:
            child_item = self._create_tree_item(child)
            parent_item.addChild(child_item)
            self._add_children(child_item, child.children)
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Обработчик клика по элементу дерева."""
        element = item.data(0, Qt.UserRole)
        if element:
            self.element_selected.emit(element)
    
    def _show_context_menu(self, position) -> None:
        """Показать контекстное меню."""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        element = item.data(0, Qt.UserRole)
        if not element or isinstance(element, Canvas):
            return
        
        menu = QMenu(self)
        
        # Действия
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(lambda: self.element_deleted.emit(element.id))
        
        # Видимость
        visible_action = menu.addAction(
            "Скрыть" if element.visible else "Показать"
        )
        visible_action.triggered.connect(
            lambda: self.element_visibility_changed.emit(element.id, not element.visible)
        )
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def refresh(self) -> None:
        """Обновить дерево элементов."""
        self._rebuild_tree()


from PySide6.QtCore import Qt
from ..models.elements import Canvas
