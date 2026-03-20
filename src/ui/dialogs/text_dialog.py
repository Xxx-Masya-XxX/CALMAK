from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                QTextEdit, QPushButton, QLabel)
from domain.models import ObjectState, TextPayload


class TextEditDialog(QDialog):
    def __init__(self, obj: ObjectState, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Text — {obj.name}")
        self.resize(400, 200)
        self.setStyleSheet("""
            QDialog { background: #1E1E2E; color: #CCCCDD; }
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Text content:"))

        self._edit = QTextEdit()
        payload = obj.payload
        if isinstance(payload, TextPayload):
            self._edit.setPlainText(payload.text)
        self._edit.setStyleSheet("""
            QTextEdit {
                background: #2A2A3E;
                color: #CCCCDD;
                border: 1px solid #3A3A5A;
                border-radius: 4px;
                padding: 6px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self._edit)

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        ok.setStyleSheet("""
            QPushButton { background: #4A90E2; color: white;
                          border: none; border-radius: 4px; padding: 6px 16px; }
            QPushButton:hover { background: #5AA0F2; }
        """)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        cancel.setStyleSheet("""
            QPushButton { background: #3A3A5A; color: #CCCCDD;
                          border: none; border-radius: 4px; padding: 6px 16px; }
            QPushButton:hover { background: #4A4A6A; }
        """)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def get_text(self) -> str:
        return self._edit.toPlainText()
