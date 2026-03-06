from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout


class DataControlPanel(QGroupBox):
    def __init__(self, delete_frame_callback) -> None:
        super().__init__("Data Control")
        self.delete_frame_callback = delete_frame_callback

        help_label = QLabel("Use this panel only for data-changing actions.")
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.delete_btn = QPushButton("Delete Selected Frame")
        self.delete_btn.clicked.connect(self.delete_frame_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.delete_btn)
        layout.addStretch(1)
