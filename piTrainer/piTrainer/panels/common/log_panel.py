from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout


class LogPanel(QGroupBox):
    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setAccessibleName(f"{title} messages")
        self.text.setAccessibleDescription("Read-only messages. Select or copy text; Tab moves to the next control.")
        self.text.setFocusPolicy(Qt.StrongFocus)
        self.text.setTabChangesFocus(True)
        self.text.setPlaceholderText('Messages and progress will appear here.')
        self.text.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)

    def append_line(self, text: str) -> None:
        self.text.appendPlainText(text)

    def clear(self) -> None:
        self.text.clear()
