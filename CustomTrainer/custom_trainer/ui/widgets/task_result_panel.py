"""Small reusable read-only result panel for Validate, Export and Export Validate."""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from custom_trainer.services.task_result_summary import TaskResult


class TaskResultPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.record: TaskResult | None = None
        self.heading = QLabel("Last result: Not run", self)
        self.heading.setProperty("role", "muted")
        self.detail = QPlainTextEdit(self)
        self.detail.setReadOnly(True)
        self.detail.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.detail.setMaximumHeight(150)
        self.detail.setPlainText("Start an operation to see the exact model, dataset, status and output path.")
        self.open_button = QPushButton("Open Location", self)
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_location)
        row = QHBoxLayout()
        row.addWidget(self.heading, 1)
        row.addWidget(self.open_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(row)
        layout.addWidget(self.detail)

    def show_result(self, record: TaskResult) -> None:
        self.record = record
        self.heading.setText(f"Last result: {record.state}")
        self.detail.setPlainText(record.display_text())
        self.open_button.setEnabled(record.verified_path() is not None)

    def open_location(self) -> None:
        # The path may have been deleted or replaced since task completion.
        record = self.record
        path = record.verified_path() if record is not None else None
        if path is None:
            self.open_button.setEnabled(False)
            QMessageBox.warning(self, "Output unavailable", "No verified completed output remains at the recorded path.")
            return
        folder = path if path.is_dir() else path.parent
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            QMessageBox.warning(self, "Could not open location", f"File manager could not open:\n{folder}")
