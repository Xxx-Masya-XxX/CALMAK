"""Панель инструментов для превью."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QFont

from ..models import Canvas


class PreviewToolbar(QObject):
    """Панель инструментов для управления превью."""

    # Сигналы
    canvas_added = Signal()
    add_rect = Signal()
    add_ellipse = Signal()
    add_triangle = Signal()
    add_text = Signal()
    export_clicked = Signal()

    LIGHT_THEME = "background-color: #f0f0f0; padding: 5px;"
    DARK_THEME = "background-color: #3c3c3c; padding: 5px;"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._parent = parent
        self._frame: QFrame | None = None
        self._add_canvas_btn: QPushButton | None = None
        self._add_rect_btn: QPushButton | None = None
        self._add_ellipse_btn: QPushButton | None = None
        self._add_triangle_btn: QPushButton | None = None
        self._add_text_btn: QPushButton | None = None
        self._zoom_out_btn: QPushButton | None = None
        self._zoom_value_label: QPushButton | None = None
        self._zoom_in_btn: QPushButton | None = None
        self._export_btn: QPushButton | None = None
        self._preview_frame = None

    def set_preview_frame(self, preview_frame) -> None:
        """Устанавливает ссылку на PreviewFrame."""
        self._preview_frame = preview_frame

    def create_toolbar(self, parent_layout: QHBoxLayout) -> None:
        """Создаёт и добавляет панель инструментов в указанный layout."""
        # Основной фрейм
        self._frame = QFrame()
        self._frame.setObjectName("toolbar")
        self._frame.setStyleSheet(self.LIGHT_THEME)
        toolbar_layout = QHBoxLayout(self._frame)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)

        # Кнопка "Добавить канвас"
        self._add_canvas_btn = QPushButton("➕ Канвас")
        self._add_canvas_btn.clicked.connect(lambda: self.canvas_added.emit())
        toolbar_layout.addWidget(self._add_canvas_btn)

        toolbar_layout.addSpacing(10)

        # Кнопки добавления объектов
        self._add_rect_btn = QPushButton("⬛ Прямоугольник")
        self._add_rect_btn.clicked.connect(lambda: self.add_rect.emit())
        toolbar_layout.addWidget(self._add_rect_btn)

        self._add_ellipse_btn = QPushButton("⚪ Эллипс")
        self._add_ellipse_btn.clicked.connect(lambda: self.add_ellipse.emit())
        toolbar_layout.addWidget(self._add_ellipse_btn)

        self._add_triangle_btn = QPushButton("🔺 Треугольник")
        self._add_triangle_btn.clicked.connect(lambda: self.add_triangle.emit())
        toolbar_layout.addWidget(self._add_triangle_btn)

        self._add_text_btn = QPushButton("📝 Текст")
        self._add_text_btn.clicked.connect(lambda: self.add_text.emit())
        toolbar_layout.addWidget(self._add_text_btn)

        toolbar_layout.addStretch()

        # Кнопки управления зумом
        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedSize(30, 30)
        self._zoom_out_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self._zoom_out_btn.setToolTip("Уменьшить масштаб (Ctrl + колесо вниз)")
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar_layout.addWidget(self._zoom_out_btn)

        self._zoom_value_label = QPushButton("100%")
        self._zoom_value_label.setFixedSize(50, 30)
        self._zoom_value_label.setToolTip("Текущий масштаб")
        self._zoom_value_label.clicked.connect(self._reset_zoom)
        toolbar_layout.addWidget(self._zoom_value_label)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedSize(30, 30)
        self._zoom_in_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self._zoom_in_btn.setToolTip("Увеличить масштаб (Ctrl + колесо вверх)")
        self._zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar_layout.addWidget(self._zoom_in_btn)

        self._export_btn = QPushButton("Экспорт в PNG")
        self._export_btn.clicked.connect(lambda: self.export_clicked.emit())
        toolbar_layout.addWidget(self._export_btn)

        parent_layout.addWidget(self._frame)

    def set_theme(self, is_dark: bool) -> None:
        """Устанавливает тему оформления."""
        if self._frame:
            self._frame.setStyleSheet(
                self.DARK_THEME if is_dark else self.LIGHT_THEME
            )

    def update_zoom_label(self, zoom: float) -> None:
        """Обновляет метку масштаба."""
        if self._zoom_value_label:
            self._zoom_value_label.setText(f"{int(zoom * 100)}%")

    def _get_active_canvas_id(self) -> str | None:
        """Получает ID активного канваса."""
        if self._parent and hasattr(self._parent, '_get_active_canvas_id'):
            return self._parent._get_active_canvas_id()
        return None

    def _zoom_in(self):
        """Увеличивает масштаб."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id and self._preview_frame:
            self._preview_frame.zoom_in(canvas_id)

    def _zoom_out(self):
        """Уменьшает масштаб."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id and self._preview_frame:
            self._preview_frame.zoom_out(canvas_id)

    def _reset_zoom(self):
        """Сбрасывает масштаб к 100%."""
        canvas_id = self._get_active_canvas_id()
        if canvas_id and self._preview_frame:
            self._preview_frame.reset_zoom(canvas_id)

    def export_to_png(self, scene, canvas: Canvas) -> bool:
        """Экспортирует канвас в PNG."""
        from ..services import export_to_png as export_service

        if not self._parent:
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            self._parent,
            "Экспорт в PNG",
            f"{canvas.name}.png",
            "PNG Files (*.png)"
        )

        if not file_path:
            return False

        if export_service(scene, canvas, file_path):
            QMessageBox.information(
                self._parent, "Успех", f"Канвас экспортирован в {file_path}"
            )
            return True
        else:
            QMessageBox.critical(
                self._parent, "Ошибка", "Не удалось сохранить файл"
            )
            return False

    @property
    def frame(self) -> QFrame | None:
        """Возвращает фрейм панели инструментов."""
        return self._frame
