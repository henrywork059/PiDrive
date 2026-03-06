from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class DataControlPanel(QGroupBox):
    def __init__(self, delete_frame_callback, shortcuts_callback) -> None:
        super().__init__("Data Control")
        self.delete_frame_callback = delete_frame_callback
        self.shortcuts_callback = shortcuts_callback

        self.delete_btn = QPushButton("Delete Selected Frame")
        self.delete_btn.clicked.connect(self.delete_frame_callback)

        self.shortcuts_btn = QPushButton("Show Shortcuts")
        self.shortcuts_btn.clicked.connect(self.shortcuts_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(self.delete_btn)
        layout.addWidget(self.shortcuts_btn)
        layout.addStretch(1)
