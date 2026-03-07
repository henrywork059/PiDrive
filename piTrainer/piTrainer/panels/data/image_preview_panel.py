from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from ...services.data.overlay_service import apply_overlays
from ...utils.image_utils import load_scaled_pixmap


class ImagePreviewPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Image Preview")
        self.image_label = QLabel("No preview")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(320)
        self.image_label.setWordWrap(True)

        self.current_record: dict[str, Any] | None = None
        self.overlay_options: dict[str, bool] = {
            'speed_vertical': False,
            'steering_horizontal': False,
            'steering_arc': False,
        }

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)

    def set_record(self, record: dict[str, Any] | None) -> None:
        self.current_record = record
        self._render_preview()

    def set_overlay_options(self, options: dict[str, bool]) -> None:
        self.overlay_options = {
            'speed_vertical': bool(options.get('speed_vertical', False)),
            'steering_horizontal': bool(options.get('steering_horizontal', False)),
            'steering_arc': bool(options.get('steering_arc', False)),
        }
        self._render_preview()

    def _render_preview(self) -> None:
        record = self.current_record or {}
        image_path = str(record.get('abs_image', ''))
        pixmap = load_scaled_pixmap(image_path, width=560, height=420)
        if pixmap is None:
            self.image_label.setPixmap(None)
            self.image_label.setText('Image not available')
            return

        rendered = apply_overlays(pixmap, record, self.overlay_options)
        self.image_label.setText('')
        self.image_label.setPixmap(rendered)

    def clear_preview(self) -> None:
        self.current_record = None
        self.image_label.setPixmap(None)
        self.image_label.setText("No preview")
