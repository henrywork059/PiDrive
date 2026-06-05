from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QPlainTextEdit, QVBoxLayout


class PreprocessResultPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Preprocess Preview')
        self.status_label = QLabel('Status: not run yet.')
        self.status_label.setWordWrap(True)
        self.status_label.setProperty('role', 'preprocessStatus')
        self.status_label.setProperty('status', 'idle')

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlaceholderText('Preprocess preview and results appear here.')
        self.text.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.text)

    def _set_status(self, text: str, status: str) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty('status', status)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.update()

    def set_status_idle(self, text: str = 'Status: not run yet.') -> None:
        self._set_status(text, 'idle')

    def set_status_running(self, text: str = 'Preprocess running...') -> None:
        self._set_status(text, 'running')

    def set_status_preview(self, text: str) -> None:
        self._set_status(text, 'preview')

    def set_status_done(self, text: str) -> None:
        self._set_status(text, 'done')

    def set_status_warning(self, text: str) -> None:
        self._set_status(text, 'warning')

    def set_preview_text(self, text: str) -> None:
        self.text.setPlainText(text)
