from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class DataControlPanel(QGroupBox):
    def __init__(self, delete_frame_callback, shortcuts_callback, autoplay_callback=None) -> None:
        super().__init__("Data Control")
        self.delete_frame_callback = delete_frame_callback
        self.shortcuts_callback = shortcuts_callback
        self.autoplay_callback = autoplay_callback
        self._autoplay_active = False

        self.delete_btn = QPushButton("Delete Selected Frame")
        self.delete_btn.clicked.connect(self.delete_frame_callback)

        self.autoplay_btn = QPushButton("Auto Play Frames")
        self.autoplay_btn.clicked.connect(self._on_autoplay_clicked)
        self.autoplay_btn.setEnabled(self.autoplay_callback is not None)

        self.shortcuts_btn = QPushButton("Show Shortcuts")
        self.shortcuts_btn.clicked.connect(self.shortcuts_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(self.delete_btn)
        layout.addWidget(self.autoplay_btn)
        layout.addWidget(self.shortcuts_btn)
        layout.addStretch(1)

    def _on_autoplay_clicked(self) -> None:
        if self.autoplay_callback is not None:
            self.autoplay_callback()

    def set_autoplay_active(self, active: bool) -> None:
        self._autoplay_active = bool(active)
        self.autoplay_btn.setText("Stop Auto Play" if self._autoplay_active else "Auto Play Frames")
