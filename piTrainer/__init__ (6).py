from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout


class LogPanel(QGroupBox):
    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)

    def append_line(self, text: str) -> None:
        self.text.appendPlainText(text)

    def clear(self) -> None:
        self.text.clear()
