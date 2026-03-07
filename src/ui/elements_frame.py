"""Панель элементов - дерево объектов."""

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMenu
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction

from ..models import BaseObject, Canvas, TextObject


class ObjectItem(QTreeWidgetItem):
    """Элемент объекта в дереве."""
    
    def __init__(self, parent: QTreeWidgetItem, obj: BaseObject):
        super().__init__(parent, [obj.name])
        self.obj = obj
        self.setData(0, 1, obj)
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)
        self.setExpanded(True)


class ElementsTree(QTreeWidget):
    """Дерево объектов сцены."""

    canvas_selected = Signal(str)  # canvas_id
    object_selected = Signal(BaseObject)
    object_parent_changed = Signal(BaseObject)  # сигнал об изменении родителя
    add_child_requested = Signal(object, str)  # родитель, тип объекта
    canvas_context_menu = Signal(object)  # Canvas или BaseObject (родитель)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Канвасы")
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)

        self._canvas_items: dict[str, QTreeWidgetItem] = {}
        self._object_items: dict[str, dict[str, ObjectItem]] = {}  # canvas_id -> {obj_id -> item}
        self._obj_to_item: dict[str, ObjectItem] = {}  # obj_id -> item

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Для отслеживания перетаскивания
        self._dragged_item = None

    def startDrag(self, supportedActions):
        """Начинает перетаскивание."""
        items = self.selectedItems()
        if items:
            self._dragged_item = items[0]
        super().startDrag(supportedActions)
    
    def add_canvas(self, canvas: Canvas) -> QTreeWidgetItem:
        """Добавляет канвас в дерево."""
        item = QTreeWidgetItem(self, [canvas.name])
        item.setData(0, 1, canvas)
        item.setExpanded(True)
        item.setForeground(0, Qt.GlobalColor.darkBlue)
        self._canvas_items[canvas.id] = item
        self._object_items[canvas.id] = {}
        return item
    
    def remove_canvas(self, canvas_id: str):
        """Удаляет канвас из дерева."""
        if canvas_id in self._canvas_items:
            item = self._canvas_items[canvas_id]
            index = self.indexOfTopLevelItem(item)
            if index >= 0:
                self.takeTopLevelItem(index)
            del self._canvas_items[canvas_id]
        if canvas_id in self._object_items:
            del self._object_items[canvas_id]
    
    def add_object(self, canvas_id: str, obj: BaseObject) -> ObjectItem:
        """Добавляет объект в дерево."""
        if canvas_id not in self._canvas_items:
            return None
        
        canvas_item = self._canvas_items[canvas_id]
        object_item = ObjectItem(canvas_item, obj)
        
        if canvas_id not in self._object_items:
            self._object_items[canvas_id] = {}
        self._object_items[canvas_id][obj.id] = object_item
        self._obj_to_item[obj.id] = object_item
        
        # Если есть родитель, перемещаем объект под него
        if obj.parent_id and obj.parent_id in self._obj_to_item:
            parent_item = self._obj_to_item[obj.parent_id]
            parent_item.addChild(object_item)
            parent_item.setExpanded(True)
        
        return object_item
    
    def remove_object(self, canvas_id: str, obj: BaseObject):
        """Удаляет объект из дерева."""
        if canvas_id in self._object_items:
            if obj.id in self._object_items[canvas_id]:
                item = self._object_items[canvas_id][obj.id]
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    # Если нет родителя, удаляем из канваса
                    canvas_item = self._canvas_items.get(canvas_id)
                    if canvas_item:
                        index = canvas_item.indexOfChild(item)
                        if index >= 0:
                            canvas_item.removeChild(item)
                del self._object_items[canvas_id][obj.id]
                if obj.id in self._obj_to_item:
                    del self._obj_to_item[obj.id]
    
    def move_object(self, canvas_id: str, obj: BaseObject, new_parent_id: str | None):
        """Перемещает объект под нового родителя или на корневой уровень.

        При смене родителя координаты пересчитываются:
        - Сохраняем глобальную позицию объекта
        - Конвертируем в локальные координаты нового родителя
        
        Примечание: Этот метод только обновляет данные модели, не перемещая элемент в дереве.
        Для перемещения элемента в дереве используйте Qt API напрямую.
        """
        if canvas_id not in self._object_items:
            return

        if obj.id not in self._object_items[canvas_id]:
            return

        # Находим старого и нового родителей
        old_parent_obj = None
        new_parent_obj = None

        if obj.parent_id:
            old_parent_obj = self._obj_to_item.get(obj.parent_id)
            if old_parent_obj:
                old_parent_obj = old_parent_obj.obj

        if new_parent_id and new_parent_id in self._obj_to_item:
            new_parent_obj = self._obj_to_item[new_parent_id].obj

        # Сохраняем глобальную позицию объекта перед перемещением
        if old_parent_obj:
            old_parent_global = old_parent_obj.get_global_position()
            global_x = old_parent_global[0] + obj.x
            global_y = old_parent_global[1] + obj.y
        else:
            global_x = obj.x
            global_y = obj.y

        # Обновляем parent_id объекта и связь _parent
        obj.parent_id = new_parent_id
        obj._parent = new_parent_obj

        # Пересчитываем локальные координаты относительно нового родителя
        if new_parent_obj:
            new_parent_global = new_parent_obj.get_global_position()
            obj.x = global_x - new_parent_global[0]
            obj.y = global_y - new_parent_global[1]
        else:
            # Нет родителя - используем глобальные координаты
            obj.x = global_x
            obj.y = global_y
    
    def get_selected_canvas(self) -> Canvas | None:
        """Возвращает выбранный канвас."""
        items = self.selectedItems()
        if items:
            item = items[0]
            data = item.data(0, 1)
            if isinstance(data, Canvas):
                return data
            elif isinstance(item.parent(), QTreeWidgetItem):
                parent_data = item.parent().data(0, 1)
                if isinstance(parent_data, Canvas):
                    return parent_data
        return None
    
    def get_selected_object(self) -> BaseObject | None:
        """Возвращает выбранный объект."""
        items = self.selectedItems()
        if items:
            item = items[0]
            if isinstance(item, ObjectItem):
                return item.obj
        return None
    
    def get_canvas_id_for_object(self, obj: BaseObject) -> str | None:
        """Получает ID канваса для объекта."""
        for canvas_id, objects in self._object_items.items():
            if obj.id in objects:
                return canvas_id
        return None
    
    def update_canvas_name(self, canvas: Canvas):
        """Обновляет имя канваса в дереве."""
        if canvas.id in self._canvas_items:
            item = self._canvas_items[canvas.id]
            item.setText(0, canvas.name)
    
    def update_object_name(self, canvas_id: str, obj: BaseObject):
        """Обновляет имя объекта в дереве."""
        if canvas_id in self._object_items:
            if obj.id in self._object_items[canvas_id]:
                item = self._object_items[canvas_id][obj.id]
                item.setText(0, obj.name)
    
    def _on_selection_changed(self):
        """Обработчик изменения выделения."""
        canvas = self.get_selected_canvas()
        if canvas:
            self.canvas_selected.emit(canvas.id)
        
        obj = self.get_selected_object()
        if obj:
            self.object_selected.emit(obj)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Обработчик двойного клика."""
        if isinstance(item, ObjectItem):
            self.object_selected.emit(item.obj)
    
    def _show_context_menu(self, position):
        """Показывает контекстное меню."""
        item = self.itemAt(position)
        if isinstance(item, ObjectItem):
            menu = QMenu(self)

            # Меню для добавления дочернего объекта
            add_child_menu = menu.addMenu("Добавить в объект")
            
            # Фигуры
            shapes_submenu = add_child_menu.addMenu("Фигуры")
            add_rect_action = shapes_submenu.addAction("Прямоугольник")
            add_rect_action.triggered.connect(
                lambda: self._on_add_child(item.obj, "rect")
            )
            add_ellipse_action = shapes_submenu.addAction("Эллипс")
            add_ellipse_action.triggered.connect(
                lambda: self._on_add_child(item.obj, "ellipse")
            )
            add_triangle_action = shapes_submenu.addAction("Треугольник")
            add_triangle_action.triggered.connect(
                lambda: self._on_add_child(item.obj, "triangle")
            )
            
            add_text_action = add_child_menu.addAction("Текст")
            add_text_action.triggered.connect(
                lambda: self._on_add_child(item.obj, "text")
            )

            # Меню для установки родителя
            set_parent_menu = menu.addMenu("Сделать родителем")

            # Опция убрать родителя
            remove_parent_action = set_parent_menu.addAction("Без родителя")
            remove_parent_action.triggered.connect(
                lambda: self._on_set_parent(item.obj, None)
            )

            # Список доступных родителей
            canvas_id = self.get_canvas_id_for_object(item.obj)
            if canvas_id:
                for obj_id, obj_item in self._object_items[canvas_id].items():
                    if obj_id != item.obj.id and obj_id != item.obj.parent_id:
                        parent_obj = obj_item.obj
                        action = set_parent_menu.addAction(f"{parent_obj.name}")
                        action.triggered.connect(
                            lambda checked, p=parent_obj: self._on_set_parent(item.obj, p)
                        )
            
            menu.exec_(self.viewport().mapToGlobal(position))
        elif isinstance(item, QTreeWidgetItem) and item.data(0, 1):
            data = item.data(0, 1)
            if isinstance(data, Canvas):
                menu = QMenu(self)
                add_obj_action = QAction("Добавить объект", self)
                add_obj_action.triggered.connect(lambda: self.canvas_context_menu.emit(data))
                menu.addAction(add_obj_action)
                menu.exec_(self.viewport().mapToGlobal(position))
    
    def _on_add_child(self, parent_obj: BaseObject, obj_type: str):
        """Обработчик добавления дочернего объекта."""
        # Испускаем сигнал с родителем
        self.add_child_requested.emit(parent_obj, obj_type)

    def _on_set_parent(self, obj: BaseObject, parent: BaseObject | None):
        """Обработчик установки родителя."""
        canvas_id = self.get_canvas_id_for_object(obj)
        if canvas_id:
            parent_id = parent.id if parent else None
            self.move_object(canvas_id, obj, parent_id)

            # Испускаем сигнал об изменении родителя для обновления превью
            self.object_parent_changed.emit(obj)

    def dragMoveEvent(self, event):
        """Обработка перетаскивания."""
        # Разрешаем стандартное перетаскивание
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        """Обработка отпускания перетаскиваемого объекта."""
        # Сначала даём Qt переместить элемент в дереве
        super().dropEvent(event)
        
        # Теперь обновляем данные модели
        if self._dragged_item:
            dragged_obj = self._dragged_item.data(0, 1)
            
            # Определяем нового родителя
            parent_item = self._dragged_item.parent()
            new_parent_obj = None
            
            if parent_item and isinstance(parent_item, ObjectItem):
                # Родитель - другой объект
                new_parent_obj = parent_item.obj
            elif parent_item and isinstance(parent_item, QTreeWidgetItem):
                # Родитель - канвас (корневой уровень)
                new_parent_obj = None
            
            # Обновляем parent_id и связь _parent
            if isinstance(dragged_obj, BaseObject):
                canvas_id = self.get_canvas_id_for_object(dragged_obj)
                if canvas_id:
                    # Перемещаем объект к новому родителю (с пересчётом координат)
                    self.move_object(canvas_id, dragged_obj, new_parent_obj.id if new_parent_obj else None)
                    
                    # Испускаем сигнал об изменении родителя
                    self.object_parent_changed.emit(dragged_obj)
        
        self._dragged_item = None

    def _is_descendant(self, potential_child: BaseObject, potential_parent: BaseObject) -> bool:
        """Проверяет является ли potential_child потомком potential_parent."""
        if potential_child.parent_id is None:
            return False
        
        if potential_child.parent_id == potential_parent.id:
            return True
        
        # Рекурсивно проверяем родителя
        for obj_id, obj_item in self._obj_to_item.items():
            if obj_id == potential_child.parent_id:
                return self._is_descendant(obj_item.obj, potential_parent)
        
        return False


class ElementsPanel(QWidget):
    """Панель элементов управления."""
    
    canvas_selected = Signal(str)  # canvas_id
    object_selected = Signal(BaseObject)
    object_parent_changed = Signal(BaseObject)
    add_child_requested = Signal(object, str)  # родитель, тип объекта
    canvas_context_menu = Signal(object)  # Canvas или BaseObject (родитель)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = ElementsTree(self)
        self.layout.addWidget(self.tree)
        
        self.tree.canvas_selected.connect(self.canvas_selected.emit)
        self.tree.object_selected.connect(self.object_selected.emit)
        self.tree.canvas_context_menu.connect(self.canvas_context_menu.emit)
        self.tree.object_parent_changed.connect(self.object_parent_changed.emit)
        self.tree.add_child_requested.connect(self.add_child_requested.emit)
    
    def add_canvas(self, canvas: Canvas):
        """Добавляет канвас в панель."""
        self.tree.add_canvas(canvas)
    
    def remove_canvas(self, canvas_id: str):
        """Удаляет канвас из панели."""
        self.tree.remove_canvas(canvas_id)
    
    def add_object(self, canvas_id: str, obj: BaseObject):
        """Добавляет объект в панель."""
        self.tree.add_object(canvas_id, obj)
    
    def remove_object(self, canvas_id: str, obj: BaseObject):
        """Удаляет объект из панели."""
        self.tree.remove_object(canvas_id, obj)
    
    def move_object(self, canvas_id: str, obj: BaseObject, parent_id: str | None):
        """Перемещает объект под нового родителя."""
        self.tree.move_object(canvas_id, obj, parent_id)
    
    def update_object_name(self, canvas_id: str, obj: BaseObject):
        """Обновляет имя объекта в панели."""
        self.tree.update_object_name(canvas_id, obj)
