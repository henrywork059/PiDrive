from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from ...services.data.overlay_service import clip_speed, clip_steering
from ...ui.sliders import CenteredFillSlider


class BulkEditPanel(QGroupBox):
    """Panel for applying one steering or speed value to selected preview rows."""

    def __init__(
        self,
        apply_steering_callback: Callable[[float], None],
        apply_speed_callback: Callable[[float], None],
        select_all_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__('Bulk Edit Selected Frames')
        self.apply_steering_callback = apply_steering_callback
        self.apply_speed_callback = apply_speed_callback
        self.select_all_callback = select_all_callback
        self._syncing_controls = False
        self._selected_count = 0

        help_label = QLabel(
            'Select multiple rows in Record Preview, then apply one value at a time. '
            'Bulk edits overwrite the selected frame labels in labels.jsonl/records.jsonl after a warning confirmation.'
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.selected_label = QLabel('Selected frames: 0')
        self.selected_label.setProperty('role', 'summaryLine')

        self.select_all_btn = QPushButton('Select All Visible Frames')
        self.select_all_btn.setProperty('role', 'amber')
        self.select_all_btn.setToolTip('Select every currently visible Record Preview row before applying a bulk edit.')
        self.select_all_btn.clicked.connect(self._select_all_visible_frames)

        self.confirm_bulk_check = QCheckBox('I understand this will overwrite selected frame labels')
        self.confirm_bulk_check.setToolTip(
            'Required before bulk steering/speed edits can be applied. A final warning dialog still appears before writing.'
        )
        self.confirm_bulk_check.toggled.connect(self._update_button_state)

        self.steering_slider = CenteredFillSlider(Qt.Horizontal, center_value=0)
        self.steering_slider.setRange(-1000, 1000)
        self.steering_slider.setValue(0)
        self.steering_slider.valueChanged.connect(self._on_steering_slider_changed)

        self.steering_spin = QDoubleSpinBox()
        self.steering_spin.setRange(-1.0, 1.0)
        self.steering_spin.setSingleStep(0.01)
        self.steering_spin.setDecimals(3)
        self.steering_spin.setValue(0.0)
        self.steering_spin.valueChanged.connect(self._on_steering_spin_changed)

        self.apply_steering_btn = QPushButton('Apply Steering Only')
        self.apply_steering_btn.setProperty('role', 'primary')
        self.apply_steering_btn.setToolTip('Overwrite only steering for the selected Record Preview rows.')
        self.apply_steering_btn.clicked.connect(self._apply_steering)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 1000)
        self.speed_slider.setValue(0)
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.0, 1.0)
        self.speed_spin.setSingleStep(0.01)
        self.speed_spin.setDecimals(3)
        self.speed_spin.setValue(0.0)
        self.speed_spin.valueChanged.connect(self._on_speed_spin_changed)

        self.apply_speed_btn = QPushButton('Apply Speed Only')
        self.apply_speed_btn.setProperty('role', 'primary')
        self.apply_speed_btn.setToolTip('Overwrite only speed/throttle for the selected Record Preview rows.')
        self.apply_speed_btn.clicked.connect(self._apply_speed)

        steering_row = QHBoxLayout()
        steering_row.addWidget(QLabel('Steering'))
        steering_row.addWidget(self.steering_slider, 1)
        steering_row.addWidget(self.steering_spin)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel('Speed'))
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_spin)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.selected_label)
        layout.addWidget(self.select_all_btn)
        layout.addWidget(self.confirm_bulk_check)
        layout.addLayout(steering_row)
        layout.addWidget(self.apply_steering_btn)
        layout.addLayout(speed_row)
        layout.addWidget(self.apply_speed_btn)
        layout.addStretch(1)
        self._update_button_state()

    def set_selected_count(self, count: int) -> None:
        self._selected_count = max(0, int(count))
        noun = 'frame' if self._selected_count == 1 else 'frames'
        self.selected_label.setText(f'Selected frames: {self._selected_count} {noun}')
        self._update_button_state()

    def bulk_edit_confirmed(self) -> bool:
        return bool(self.confirm_bulk_check.isChecked())

    def steering_value(self) -> float:
        return clip_steering(float(self.steering_spin.value()))

    def speed_value(self) -> float:
        return clip_speed(float(self.speed_spin.value()))

    def _can_apply(self) -> bool:
        return self.bulk_edit_confirmed() and self._selected_count > 0

    def _update_button_state(self) -> None:
        enabled = self._can_apply()
        self.apply_steering_btn.setEnabled(enabled)
        self.apply_speed_btn.setEnabled(enabled)

    def _select_all_visible_frames(self) -> None:
        if self.select_all_callback is not None:
            self.select_all_callback()

    def _on_steering_slider_changed(self, value: int) -> None:
        if self._syncing_controls:
            return
        self._syncing_controls = True
        self.steering_spin.setValue(clip_steering(value / 1000.0))
        self._syncing_controls = False

    def _on_steering_spin_changed(self, value: float) -> None:
        if self._syncing_controls:
            return
        self._syncing_controls = True
        self.steering_slider.setValue(int(round(clip_steering(value) * 1000.0)))
        self._syncing_controls = False

    def _on_speed_slider_changed(self, value: int) -> None:
        if self._syncing_controls:
            return
        self._syncing_controls = True
        self.speed_spin.setValue(clip_speed(value / 1000.0))
        self._syncing_controls = False

    def _on_speed_spin_changed(self, value: float) -> None:
        if self._syncing_controls:
            return
        self._syncing_controls = True
        self.speed_slider.setValue(int(round(clip_speed(value) * 1000.0)))
        self._syncing_controls = False

    def _apply_steering(self) -> None:
        self.apply_steering_callback(self.steering_value())

    def _apply_speed(self) -> None:
        self.apply_speed_callback(self.speed_value())
