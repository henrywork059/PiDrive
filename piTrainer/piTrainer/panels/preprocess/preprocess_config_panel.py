from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState


class PreprocessConfigPanel(QGroupBox):
    MODE_ITEMS = ['Any mode', 'Manual only', 'Exclude manual']
    SOURCE_ITEMS = ['Loaded dataset (all rows)', 'Current filtered rows']

    def __init__(self, state: AppState) -> None:
        super().__init__('Preprocess Config')
        self.state = state

        help_label = QLabel(
            'Build a preprocessing recipe for the currently loaded dataset. You can filter rows, balance overly common '
            'near-straight driving samples, drop duplicate or overly dense frames, boost harder turns, resize training '
            'images, and synthesize extra training rows such as mirrored steering samples or color-shifted copies, '
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

        self.drop_duplicate_images = QCheckBox('Drop duplicate image paths')
        self.drop_duplicate_images.setChecked(False)

        self.frame_stride = QSpinBox()
        self.frame_stride.setRange(1, 60)
        self.frame_stride.setValue(1)
        self.frame_stride.setToolTip('Keep every Nth row after filtering to reduce near-duplicate consecutive frames.')

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

        self.balance_straight = QCheckBox('Balance near-zero steering rows')
        self.straight_threshold = QDoubleSpinBox()
        self.straight_threshold.setRange(0.001, 1.0)
        self.straight_threshold.setDecimals(3)
        self.straight_threshold.setSingleStep(0.01)
        self.straight_threshold.setValue(0.05)

        self.straight_keep_ratio = QDoubleSpinBox()
        self.straight_keep_ratio.setRange(0.01, 1.0)
        self.straight_keep_ratio.setDecimals(2)
        self.straight_keep_ratio.setSingleStep(0.05)
        self.straight_keep_ratio.setValue(0.35)

        self.turn_boost = QCheckBox('Boost turning examples')
        self.turn_threshold = QDoubleSpinBox()
        self.turn_threshold.setRange(0.01, 1.0)
        self.turn_threshold.setDecimals(3)
        self.turn_threshold.setSingleStep(0.01)
        self.turn_threshold.setValue(0.18)
        self.turn_copies = QSpinBox()
        self.turn_copies.setRange(1, 8)
        self.turn_copies.setValue(1)

        self.mirror_enabled = QCheckBox('Add one left-right mirrored copy per row')
        self.color_variants = QSpinBox()
        self.color_variants.setRange(0, 4)
        self.color_variants.setValue(0)
        self.color_variants.setToolTip('Adds deterministic color-shifted copies for each filtered row.')

        self.image_h = QSpinBox()
        self.image_h.setRange(32, 1080)
        self.image_w = QSpinBox()
        self.image_w.setRange(32, 1920)

        self._range_row_steer = self._make_range_row(self.steering_min, self.steering_max)
        self._range_row_speed = self._make_range_row(self.speed_min, self.speed_max)
        self._straight_row = self._make_range_row(self.straight_threshold, self.straight_keep_ratio)
        self._turn_row = self._make_range_row(self.turn_threshold, self.turn_copies)

        form = QFormLayout()
        form.addRow('Source rows', self.source_combo)
        form.addRow('Mode filter', self.mode_combo)
        form.addRow(self.require_images)
        form.addRow(self.drop_duplicate_images)
        form.addRow('Keep every Nth row', self.frame_stride)
        form.addRow(self.enable_steering_range)
        form.addRow('Steering min / max', self._range_row_steer)
        form.addRow(self.enable_speed_range)
        form.addRow('Speed min / max', self._range_row_speed)
        form.addRow(self.balance_straight)
        form.addRow('Straight threshold / keep ratio', self._straight_row)
        form.addRow(self.turn_boost)
        form.addRow('Turn threshold / extra copies', self._turn_row)
        form.addRow(self.mirror_enabled)
        form.addRow('Color variants per row', self.color_variants)
        form.addRow('Output image height', self.image_h)
        form.addRow('Output image width', self.image_w)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addLayout(form)
        layout.addStretch(1)

        self.enable_steering_range.toggled.connect(self._update_enabled_state)
        self.enable_speed_range.toggled.connect(self._update_enabled_state)
        self.balance_straight.toggled.connect(self._update_enabled_state)
        self.turn_boost.toggled.connect(self._update_enabled_state)
        self.sync_from_state()
        self._update_enabled_state()

    def _make_range_row(self, left, right) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(left)
        row.addWidget(right)
        return container

    def _update_enabled_state(self) -> None:
        steer_enabled = self.enable_steering_range.isChecked()
        speed_enabled = self.enable_speed_range.isChecked()
        balance_enabled = self.balance_straight.isChecked()
        turn_enabled = self.turn_boost.isChecked()
        self.steering_min.setEnabled(steer_enabled)
        self.steering_max.setEnabled(steer_enabled)
        self.speed_min.setEnabled(speed_enabled)
        self.speed_max.setEnabled(speed_enabled)
        self.straight_threshold.setEnabled(balance_enabled)
        self.straight_keep_ratio.setEnabled(balance_enabled)
        self.turn_threshold.setEnabled(turn_enabled)
        self.turn_copies.setEnabled(turn_enabled)

    def sync_from_state(self) -> None:
        self.image_h.setValue(self.state.train_config.img_h)
        self.image_w.setValue(self.state.train_config.img_w)
        self.mode_combo.setCurrentText('Manual only' if self.state.train_config.only_manual else 'Any mode')

    def reset_to_defaults(self) -> None:
        self.source_combo.setCurrentIndex(0)
        self.mode_combo.setCurrentText('Manual only' if self.state.train_config.only_manual else 'Any mode')
        self.require_images.setChecked(True)
        self.drop_duplicate_images.setChecked(False)
        self.frame_stride.setValue(1)
        self.enable_steering_range.setChecked(False)
        self.enable_speed_range.setChecked(False)
        self.balance_straight.setChecked(False)
        self.turn_boost.setChecked(False)
        self.mirror_enabled.setChecked(False)
        self.color_variants.setValue(0)
        self.steering_min.setValue(-1.0)
        self.steering_max.setValue(1.0)
        self.speed_min.setValue(-1.0)
        self.speed_max.setValue(1.0)
        self.straight_threshold.setValue(0.05)
        self.straight_keep_ratio.setValue(0.35)
        self.turn_threshold.setValue(0.18)
        self.turn_copies.setValue(1)
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
            'drop_duplicate_images': self.drop_duplicate_images.isChecked(),
            'frame_stride': self.frame_stride.value(),
            'steering_range': steering_range,
            'speed_range': speed_range,
            'balance_straight': self.balance_straight.isChecked(),
            'straight_threshold': self.straight_threshold.value(),
            'straight_keep_ratio': self.straight_keep_ratio.value(),
            'turn_boost': self.turn_boost.isChecked(),
            'turn_threshold': self.turn_threshold.value(),
            'turn_copies': self.turn_copies.value(),
            'mirror_enabled': self.mirror_enabled.isChecked(),
            'color_variants': self.color_variants.value(),
            'image_height': self.image_h.value(),
            'image_width': self.image_w.value(),
        }
