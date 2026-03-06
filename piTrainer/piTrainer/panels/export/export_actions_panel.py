from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class ExportActionsPanel(QGroupBox):
    def __init__(self, export_callback) -> None:
        super().__init__("Export Actions")
        self.export_btn = QPushButton("Export Selected Artifacts")
        self.export_btn.clicked.connect(export_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(self.export_btn)
