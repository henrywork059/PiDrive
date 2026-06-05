from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QVBoxLayout


class OverlayControlPanel(QGroupBox):
    def __init__(self, change_callback) -> None:
        super().__init__('Overlays')
        self.change_callback = change_callback

        help_label = QLabel('Choose overlay guides for the preview frame. The PiSD V7 road guide uses saved settings from labels.jsonl/manifest.')
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.path_preview_cb = QCheckBox('PiSD V7 road guide')
        self.legacy_path_preview_cb = QCheckBox('Legacy path (debug)')
        self.speed_vertical_cb = QCheckBox('Speed bar')
        self.steering_horizontal_cb = QCheckBox('Steering bar')
        self.steering_arc_cb = QCheckBox('Steering arc')
        self.drive_arrow_cb = QCheckBox('Drive arrow (debug)')

        self.path_preview_cb.setChecked(True)

        for checkbox in [
            self.path_preview_cb,
            self.legacy_path_preview_cb,
            self.speed_vertical_cb,
            self.steering_horizontal_cb,
            self.steering_arc_cb,
            self.drive_arrow_cb,
        ]:
            checkbox.toggled.connect(self._emit_change)

        reset_btn = QPushButton('Clear')
        reset_btn.clicked.connect(self.reset)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.path_preview_cb)
        layout.addWidget(self.legacy_path_preview_cb)
        layout.addWidget(self.speed_vertical_cb)
        layout.addWidget(self.steering_horizontal_cb)
        layout.addWidget(self.steering_arc_cb)
        layout.addWidget(self.drive_arrow_cb)
        layout.addWidget(reset_btn)
        layout.addStretch(1)

    def options(self) -> dict[str, bool]:
        return {
            'path_preview': self.path_preview_cb.isChecked(),
            'legacy_path_preview': self.legacy_path_preview_cb.isChecked(),
            'speed_vertical': self.speed_vertical_cb.isChecked(),
            'steering_horizontal': self.steering_horizontal_cb.isChecked(),
            'steering_arc': self.steering_arc_cb.isChecked(),
            'drive_arrow': self.drive_arrow_cb.isChecked(),
        }

    def reset(self) -> None:
        for checkbox in [
            self.path_preview_cb,
            self.legacy_path_preview_cb,
            self.speed_vertical_cb,
            self.steering_horizontal_cb,
            self.steering_arc_cb,
            self.drive_arrow_cb,
        ]:
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
        self._emit_change()

    def _emit_change(self) -> None:
        if self.change_callback is not None:
            self.change_callback(self.options())
