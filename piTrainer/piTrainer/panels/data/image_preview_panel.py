from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from ...utils.image_utils import load_scaled_pixmap


class ImagePreviewPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Image Preview")
        self.image_label = QLabel("No preview")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(320)
        self.image_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)

    def set_image_path(self, image_path: str) -> None:
        pixmap = load_scaled_pixmap(image_path, width=560, height=420)
        if pixmap is None:
            self.image_label.setPixmap(None)
            self.image_label.setText("Image not available")
            return
        self.image_label.setText("")
        self.image_label.setPixmap(pixmap)

    def clear_preview(self) -> None:
        self.image_label.setPixmap(None)
        self.image_label.setText("No preview")
