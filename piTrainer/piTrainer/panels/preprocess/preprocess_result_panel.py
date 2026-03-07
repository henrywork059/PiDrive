from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout


class PreprocessResultPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Preprocess Preview')
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)

    def set_preview_text(self, text: str) -> None:
        self.text.setPlainText(text)
