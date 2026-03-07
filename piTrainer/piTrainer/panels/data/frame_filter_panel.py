from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FrameFilterPanel(QGroupBox):
    def __init__(self, apply_callback, clear_callback) -> None:
        super().__init__("Frame Filter")
        self.apply_callback = apply_callback
        self.clear_callback = clear_callback

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Search session / frame_id / mode / ts")
        self.text_edit.returnPressed.connect(self.apply_callback)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["All Modes", "manual", "auto", "train", "user"])
        self.mode_combo.currentIndexChanged.connect(lambda *_: self.apply_callback())

        self.speed_checkbox = QCheckBox("Use speed range")
        self.speed_checkbox.toggled.connect(self._handle_range_toggle)
        self.speed_min_spin = self._build_range_spinbox()
        self.speed_max_spin = self._build_range_spinbox(1.0)

        self.steering_checkbox = QCheckBox("Use steering range")
        self.steering_checkbox.toggled.connect(self._handle_range_toggle)
        self.steering_min_spin = self._build_range_spinbox()
        self.steering_max_spin = self._build_range_spinbox(1.0)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_callback)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_callback)

        form = QVBoxLayout(self)
        help_label = QLabel(
            "Filter the loaded frames by text, mode, speed, or steering before previewing, deleting, or training."
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)
        form.addWidget(help_label)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Text"))
        row1.addWidget(self.text_edit, 1)
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Mode"))
        row2.addWidget(self.mode_combo, 1)
        form.addLayout(row2)

        numeric_block = QWidget()
        numeric_layout = QGridLayout(numeric_block)
        numeric_layout.setContentsMargins(0, 4, 0, 0)
        numeric_layout.setHorizontalSpacing(8)
        numeric_layout.setVerticalSpacing(8)

        numeric_layout.addWidget(self.speed_checkbox, 0, 0)
        numeric_layout.addWidget(QLabel("Min"), 0, 1)
        numeric_layout.addWidget(self.speed_min_spin, 0, 2)
        numeric_layout.addWidget(QLabel("Max"), 0, 3)
        numeric_layout.addWidget(self.speed_max_spin, 0, 4)

        numeric_layout.addWidget(self.steering_checkbox, 1, 0)
        numeric_layout.addWidget(QLabel("Min"), 1, 1)
        numeric_layout.addWidget(self.steering_min_spin, 1, 2)
        numeric_layout.addWidget(QLabel("Max"), 1, 3)
        numeric_layout.addWidget(self.steering_max_spin, 1, 4)
        numeric_layout.setColumnStretch(5, 1)
        form.addWidget(numeric_block)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(apply_btn)
        button_row.addWidget(clear_btn)
        form.addLayout(button_row)

        self._sync_range_controls()

    def _build_range_spinbox(self, value: float = 0.0) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-9999.0, 9999.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.05)
        spin.setAlignment(Qt.AlignRight)
        spin.setValue(value)
        spin.valueChanged.connect(lambda *_: self.apply_callback())
        return spin

    def _sync_range_controls(self) -> None:
        speed_enabled = self.speed_checkbox.isChecked()
        steering_enabled = self.steering_checkbox.isChecked()
        self.speed_min_spin.setEnabled(speed_enabled)
        self.speed_max_spin.setEnabled(speed_enabled)
        self.steering_min_spin.setEnabled(steering_enabled)
        self.steering_max_spin.setEnabled(steering_enabled)

    def _handle_range_toggle(self, *_args) -> None:
        self._sync_range_controls()
        self.apply_callback()

    def filter_text(self) -> str:
        return self.text_edit.text().strip()

    def selected_mode(self) -> str:
        value = self.mode_combo.currentText().strip()
        return "" if value == "All Modes" else value

    def speed_filter_enabled(self) -> bool:
        return self.speed_checkbox.isChecked()

    def steering_filter_enabled(self) -> bool:
        return self.steering_checkbox.isChecked()

    def speed_range(self) -> tuple[float, float]:
        return (
            min(self.speed_min_spin.value(), self.speed_max_spin.value()),
            max(self.speed_min_spin.value(), self.speed_max_spin.value()),
        )

    def steering_range(self) -> tuple[float, float]:
        return (
            min(self.steering_min_spin.value(), self.steering_max_spin.value()),
            max(self.steering_min_spin.value(), self.steering_max_spin.value()),
        )

    def reset(self) -> None:
        self.text_edit.clear()
        self.mode_combo.setCurrentIndex(0)
        self.speed_checkbox.setChecked(False)
        self.steering_checkbox.setChecked(False)
        self.speed_min_spin.setValue(0.0)
        self.speed_max_spin.setValue(1.0)
        self.steering_min_spin.setValue(0.0)
        self.steering_max_spin.setValue(1.0)
        self._sync_range_controls()
