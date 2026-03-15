"""Компактная панель инструментов.

setFixedHeight(36) + QSizePolicy.Fixed по вертикали → toolbar не растягивается,
preview_frame получает всё доступное пространство.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFileDialog,
    QMessageBox, QSizePolicy, QLabel
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from ..models import Canvas


class Toolbar(QWidget):

    canvas_added   = Signal()
    add_rect       = Signal()
    add_ellipse    = Signal()
    add_triangle   = Signal()
    add_text       = Signal()
    export_clicked = Signal()

    LIGHT = "background-color: #ebebeb; border-bottom: 1px solid #ccc;"
    DARK  = "background-color: #333333; border-bottom: 1px solid #555;"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview_frame = None

        # ── Фиксируем высоту ──────────────────────────────────────────
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(self.LIGHT)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(4)

        def btn(label: str, sig: Signal | None = None,
                slot=None, w: int | None = None) -> QPushButton:
            b = QPushButton(label)
            b.setFixedHeight(26)
            if w:
                b.setFixedWidth(w)
            if sig is not None:
                b.clicked.connect(sig.emit)
            elif slot is not None:
                b.clicked.connect(slot)
            return b

        lay.addWidget(btn("➕ Канвас", self.canvas_added))
        lay.addWidget(self._vsep())
        lay.addWidget(btn("⬛ Rect",      self.add_rect))
        lay.addWidget(btn("⚪ Ellipse",   self.add_ellipse))
        lay.addWidget(btn("🔺 Triangle",  self.add_triangle))
        lay.addWidget(btn("📝 Текст",     self.add_text))
        lay.addStretch()

        lay.addWidget(btn("−", slot=self._zoom_out, w=26))
        self._zoom_lbl = QPushButton("100%")
        self._zoom_lbl.setFixedSize(50, 26)
        self._zoom_lbl.clicked.connect(self._reset_zoom)
        lay.addWidget(self._zoom_lbl)
        lay.addWidget(btn("+", slot=self._zoom_in, w=26))

        lay.addWidget(self._vsep())
        lay.addWidget(btn("⬇ PNG", self.export_clicked))

    @staticmethod
    def _vsep() -> QWidget:
        sep = QWidget()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background: #bbb;")
        return sep

    # ------------------------------------------------------------------

    def set_preview_frame(self, pf):
        self._preview_frame = pf

    def set_theme(self, is_dark: bool):
        self.setStyleSheet(self.DARK if is_dark else self.LIGHT)

    def update_zoom_label(self, zoom: float):
        self._zoom_lbl.setText(f"{int(zoom * 100)}%")

    def _canvas_id(self):
        p = self.parent()
        if p and hasattr(p, "_get_active_canvas_id"):
            return p._get_active_canvas_id()
        return None

    def _zoom_in(self):
        cid = self._canvas_id()
        if cid and self._preview_frame:
            self._preview_frame.zoom_in(cid)

    def _zoom_out(self):
        cid = self._canvas_id()
        if cid and self._preview_frame:
            self._preview_frame.zoom_out(cid)

    def _reset_zoom(self):
        cid = self._canvas_id()
        if cid and self._preview_frame:
            self._preview_frame.reset_zoom(cid)

    def export_to_png(self, scene, canvas: Canvas) -> bool:
        from ..services import export_to_png as svc
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в PNG", f"{canvas.name}.png", "PNG (*.png)"
        )
        if not path:
            return False
        if svc(scene, canvas, path):
            QMessageBox.information(self, "Успех", "Файл сохранён")
            return True
        QMessageBox.critical(self, "Ошибка", "Не удалось сохранить")
        return False
