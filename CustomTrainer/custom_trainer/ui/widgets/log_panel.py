from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    append_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setPlaceholderText('Run actions to see logs here...')

        clear_button = QPushButton('Clear Log', self)
        clear_button.clicked.connect(self.clear)

        controls = QHBoxLayout()
        controls.addStretch(1)
        controls.addWidget(clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(controls)
        layout.addWidget(self.text, 1)

        self.append_requested.connect(self.append_line)

    def log(self, message: str) -> None:
        self.append_requested.emit(message)

    @Slot(str)
    def append_line(self, message: str) -> None:
        self.text.appendPlainText(message)
        bar = self.text.verticalScrollBar()
        bar.setValue(bar.maximum())

    @Slot()
    def clear(self) -> None:
        self.text.clear()
