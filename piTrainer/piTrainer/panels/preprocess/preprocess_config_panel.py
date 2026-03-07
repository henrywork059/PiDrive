from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from ...app_state import AppState


class PreprocessConfigPanel(QGroupBox):
    MODE_ITEMS = ['Any mode', 'Manual only', 'Exclude manual']
    SOURCE_ITEMS = ['Loaded dataset (all rows)', 'Current filtered rows']

    def __init__(self, state: AppState) -> None:
        super().__init__('Preprocess Config')
        self.state = state

        help_label = QLabel(
            'Build a preprocessing recipe for the currently loaded dataset. Apply it to update the active training rows '
            'without touching the original source files.'
        )
        help_label.setWordWrap(True)
        help_label.setProperty('role', 'muted')

        self.source_combo = QComboBox()
        self.source_combo.addItems(self.SOURCE_ITEMS)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.MODE_ITEMS)

        self.require_images = QCheckBox('Keep only rows with existing image files')
        self.require_images.setChecked(True)

        self.enable_steering_range = QCheckBox('Filter steering range')
        self.steering_min = QDoubleSpinBox()
        self.steering_max = QDoubleSpinBox()
        for widget in (self.steering_min, self.steering_max):
            widget.setRange(-100.0, 100.0)
            widget.setDecimals(3)
            widget.setSingleStep(0.05)
        self.steering_min.setValue(-1.0)
        self.steering_max.setValue(1.0)

        self.enable_speed_range = QCheckBox('Filter speed range')
        self.speed_min = QDoubleSpinBox()
        self.speed_max = QDoubleSpinBox()
        for widget in (self.speed_min, self.speed_max):
            widget.setRange(-100.0, 100.0)
            widget.setDecimals(3)
            widget.setSingleStep(0.05)
        self.speed_min.setValue(-1.0)
        self.speed_max.setValue(1.0)

        self.image_h = QSpinBox()
        self.image_h.setRange(32, 1080)
        self.image_w = QSpinBox()
        self.image_w.setRange(32, 1920)

        self._range_row_steer = self._make_range_row(self.steering_min, self.steering_max)
        self._range_row_speed = self._make_range_row(self.speed_min, self.speed_max)

        form = QFormLayout()
        form.addRow('Source rows', self.source_combo)
        form.addRow('Mode filter', self.mode_combo)
        form.addRow(self.require_images)
        form.addRow(self.enable_steering_range)
        form.addRow('Steering min / max', self._range_row_steer)
        form.addRow(self.enable_speed_range)
        form.addRow('Speed min / max', self._range_row_speed)
        form.addRow('Output image height', self.image_h)
        form.addRow('Output image width', self.image_w)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addLayout(form)
        layout.addStretch(1)

        self.enable_steering_range.toggled.connect(self._update_enabled_state)
        self.enable_speed_range.toggled.connect(self._update_enabled_state)
        self.sync_from_state()
        self._update_enabled_state()

    def _make_range_row(self, left: QDoubleSpinBox, right: QDoubleSpinBox) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(left)
        row.addWidget(right)
        return container

    def _update_enabled_state(self) -> None:
        steer_enabled = self.enable_steering_range.isChecked()
        speed_enabled = self.enable_speed_range.isChecked()
        self.steering_min.setEnabled(steer_enabled)
        self.steering_max.setEnabled(steer_enabled)
        self.speed_min.setEnabled(speed_enabled)
        self.speed_max.setEnabled(speed_enabled)

    def sync_from_state(self) -> None:
        self.image_h.setValue(self.state.train_config.img_h)
        self.image_w.setValue(self.state.train_config.img_w)
        self.mode_combo.setCurrentText('Manual only' if self.state.train_config.only_manual else 'Any mode')

    def reset_to_defaults(self) -> None:
        self.source_combo.setCurrentIndex(0)
        self.mode_combo.setCurrentText('Manual only' if self.state.train_config.only_manual else 'Any mode')
        self.require_images.setChecked(True)
        self.enable_steering_range.setChecked(False)
        self.enable_speed_range.setChecked(False)
        self.steering_min.setValue(-1.0)
        self.steering_max.setValue(1.0)
        self.speed_min.setValue(-1.0)
        self.speed_max.setValue(1.0)
        self.image_h.setValue(self.state.train_config.img_h)
        self.image_w.setValue(self.state.train_config.img_w)
        self._update_enabled_state()

    def source_mode(self) -> str:
        return self.source_combo.currentText()

    def recipe(self) -> dict[str, object]:
        steering_range = None
        if self.enable_steering_range.isChecked():
            steering_range = (self.steering_min.value(), self.steering_max.value())
        speed_range = None
        if self.enable_speed_range.isChecked():
            speed_range = (self.speed_min.value(), self.speed_max.value())
        return {
            'source_mode': self.source_combo.currentText(),
            'mode_filter': self.mode_combo.currentText(),
            'require_images': self.require_images.isChecked(),
            'steering_range': steering_range,
            'speed_range': speed_range,
            'image_height': self.image_h.value(),
            'image_width': self.image_w.value(),
        }
