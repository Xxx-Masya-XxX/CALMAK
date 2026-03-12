"""Секция трансформации: позиция, размер, поворот, родитель."""

from PySide6.QtWidgets import (
    QFormLayout, QDoubleSpinBox, QCheckBox,
    QComboBox, QHBoxLayout, QLabel
)

from .base_section import BaseSection
from ....models.objects.base_object import BaseObject


class TransformSection(BaseSection):
    """X, Y, ширина, высота, поворот, блокировка, родитель."""

    def __init__(self, parent=None):
        self._objects_list: list[BaseObject] = []
        super().__init__("Трансформация", parent)

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(4)

        # Блокировка
        self.locked_check = QCheckBox()
        self.locked_check.stateChanged.connect(self._on_locked)
        layout.addRow("Заблокирован:", self.locked_check)

        # X
        x_row = QHBoxLayout()
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.setDecimals(1)
        self.x_spin.valueChanged.connect(self._on_transform)
        self._x_lock_lbl = QLabel()
        self._x_lock_lbl.setStyleSheet("color: #888;")
        x_row.addWidget(self.x_spin)
        x_row.addWidget(self._x_lock_lbl)
        layout.addRow("X (локальн.):", x_row)

        # Y
        y_row = QHBoxLayout()
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.setDecimals(1)
        self.y_spin.valueChanged.connect(self._on_transform)
        self._y_lock_lbl = QLabel()
        self._y_lock_lbl.setStyleSheet("color: #888;")
        y_row.addWidget(self.y_spin)
        y_row.addWidget(self._y_lock_lbl)
        layout.addRow("Y (локальн.):", y_row)

        # Глобальные координаты
        self.global_label = QLabel()
        self.global_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addRow("Глобальные:", self.global_label)

        # Родитель
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("Нет", None)
        self.parent_combo.currentIndexChanged.connect(self._on_parent)
        layout.addRow("Родитель:", self.parent_combo)

        # Размеры
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setDecimals(1)
        self.width_spin.valueChanged.connect(self._on_transform)
        layout.addRow("Ширина:", self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setDecimals(1)
        self.height_spin.valueChanged.connect(self._on_transform)
        layout.addRow("Высота:", self.height_spin)

        # Поворот
        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-360, 360)
        self.rotation_spin.setDecimals(1)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.valueChanged.connect(self._on_transform)
        layout.addRow("Поворот:", self.rotation_spin)

    def set_objects_list(self, objects: list[BaseObject]):
        self._objects_list = objects
        if self._obj:
            self._refresh_parent_combo(self._obj)

    def _load(self, obj: BaseObject):
        self.locked_check.setChecked(obj.locked)
        self.x_spin.setValue(obj.x)
        self.y_spin.setValue(obj.y)
        self.width_spin.setValue(obj.width)
        self.height_spin.setValue(obj.height)
        self.rotation_spin.setValue(obj.rotation)
        gx, gy = obj.get_global_position()
        self.global_label.setText(f"{gx:.1f}, {gy:.1f}")
        self._update_lock_ui(obj.locked)
        self._refresh_parent_combo(obj)

    def update_position(self, obj: BaseObject):
        """Обновляет только координаты без перезагрузки всей секции."""
        self._blocking = True
        self.x_spin.setValue(obj.x)
        self.y_spin.setValue(obj.y)
        self.rotation_spin.setValue(obj.rotation)
        gx, gy = obj.get_global_position()
        self.global_label.setText(f"{gx:.1f}, {gy:.1f}")
        self._blocking = False

    def _refresh_parent_combo(self, obj: BaseObject):
        self.parent_combo.blockSignals(True)
        self.parent_combo.clear()
        self.parent_combo.addItem("Нет", None)
        for o in self._objects_list:
            if o.id != obj.id and not self._is_descendant(o, obj):
                self.parent_combo.addItem(o.name, o.id)
        for i in range(self.parent_combo.count()):
            if self.parent_combo.itemData(i) == obj.parent_id:
                self.parent_combo.setCurrentIndex(i)
                break
        self.parent_combo.blockSignals(False)

    def _is_descendant(self, candidate: BaseObject, ancestor: BaseObject) -> bool:
        if candidate.parent_id is None:
            return False
        if candidate.parent_id == ancestor.id:
            return True
        for o in self._objects_list:
            if o.id == candidate.parent_id:
                return self._is_descendant(o, ancestor)
        return False

    def _update_lock_ui(self, locked: bool):
        icon = "🔒" if locked else ""
        self._x_lock_lbl.setText(icon)
        self._y_lock_lbl.setText(icon)
        self.x_spin.setEnabled(not locked)
        self.y_spin.setEnabled(not locked)

    def _on_locked(self, state: int):
        if self._obj:
            self._obj.locked = state == 2
            self._update_lock_ui(self._obj.locked)
            self._emit()

    def _on_transform(self):
        if self._obj:
            self._obj.x = self.x_spin.value()
            self._obj.y = self.y_spin.value()
            self._obj.width = self.width_spin.value()
            self._obj.height = self.height_spin.value()
            self._obj.rotation = self.rotation_spin.value()
            gx, gy = self._obj.get_global_position()
            self.global_label.setText(f"{gx:.1f}, {gy:.1f}")
            self._emit()

    def _on_parent(self, index: int):
        if self._blocking or not self._obj:
            return
        parent_id = self.parent_combo.itemData(index)
        self._obj.parent_id = parent_id
        parent_obj = next((o for o in self._objects_list if o.id == parent_id), None)
        self._obj._parent = parent_obj
        self._emit()
