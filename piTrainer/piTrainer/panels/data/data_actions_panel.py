from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout


class DataActionsPanel(QGroupBox):
    def __init__(self, refresh_callback, load_callback, clear_filter_callback, shortcuts_callback) -> None:
        super().__init__("Quick Actions")
        help_label = QLabel("Common navigation and viewing actions for the Data page.")
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        refresh_btn = QPushButton("Refresh Sessions")
        refresh_btn.clicked.connect(refresh_callback)

        load_btn = QPushButton("Load Selected Sessions")
        load_btn.clicked.connect(load_callback)

        clear_filter_btn = QPushButton("Clear Preview Filter")
        clear_filter_btn.clicked.connect(clear_filter_callback)

        shortcuts_btn = QPushButton("Show Shortcuts")
        shortcuts_btn.clicked.connect(shortcuts_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(refresh_btn)
        layout.addWidget(load_btn)
        layout.addWidget(clear_filter_btn)
        layout.addWidget(shortcuts_btn)
        layout.addStretch(1)
