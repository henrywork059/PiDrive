from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout

from ...ui.layout_widgets import style_next_step_button


class ExportActionsPanel(QGroupBox):
    def __init__(self, export_callback) -> None:
        super().__init__("Actions")
        self.export_btn = QPushButton("Export")
        style_next_step_button(self.export_btn, "Export")
        self.export_btn.clicked.connect(export_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(self.export_btn)
