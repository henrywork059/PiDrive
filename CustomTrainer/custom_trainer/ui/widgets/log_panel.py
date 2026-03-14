from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout


class LogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText('CustomTrainer log output will appear here...')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.output)

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime('%H:%M:%S')
        self.output.appendPlainText(f'[{stamp}] {message}')
