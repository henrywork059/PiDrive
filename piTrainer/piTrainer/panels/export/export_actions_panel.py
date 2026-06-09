from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout

from ...ui.layout_widgets import style_next_step_button


class ExportActionsPanel(QGroupBox):
    def __init__(self, export_callback) -> None:
        super().__init__("Actions")
        self.export_btn = QPushButton("Export")
        style_next_step_button(self.export_btn, "Export")
        self.export_btn.clicked.connect(export_callback)

        self.export_status_label = QLabel('Exported model: not exported yet.')
        self.export_status_label.setObjectName('exportModelSaveStatus')
        self.export_status_label.setProperty('role', 'saveStatus')
        self.export_status_label.setProperty('status', 'idle')
        self.export_status_label.setWordWrap(True)
        self.export_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.export_status_label)

    def set_export_status(self, message: str, *, success: bool = False) -> None:
        cleaned = str(message or '').strip() or 'Exported model: not exported yet.'
        lower = cleaned.lower()
        status = 'saved' if success else ('warning' if ('failed' in lower or 'could not' in lower or 'error' in lower) else 'idle')
        self.export_status_label.setText(cleaned)
        self.export_status_label.setProperty('status', status)
        self.export_status_label.style().unpolish(self.export_status_label)
        self.export_status_label.style().polish(self.export_status_label)
