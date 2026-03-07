from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class PlaybackControlPanel(QGroupBox):
    def __init__(self, play_callback, stop_callback, restart_callback, speed_change_callback) -> None:
        super().__init__('Playback Control')
        self.play_callback = play_callback
        self.stop_callback = stop_callback
        self.restart_callback = restart_callback
        self.speed_change_callback = speed_change_callback

        help_label = QLabel('Control preview playback here. Adjust playback speed and move through filtered frames automatically.')
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.status_label = QLabel('Stopped')
        self.status_label.setAlignment(Qt.AlignLeft)

        self.play_btn = QPushButton('Play')
        self.play_btn.clicked.connect(self.play_callback)

        self.stop_btn = QPushButton('Stop')
        self.stop_btn.clicked.connect(self.stop_callback)

        self.restart_btn = QPushButton('Restart')
        self.restart_btn.clicked.connect(self.restart_callback)

        controls_row = QHBoxLayout()
        controls_row.addWidget(self.play_btn)
        controls_row.addWidget(self.stop_btn)
        controls_row.addWidget(self.restart_btn)

        speed_label = QLabel('Speed (frames/sec)')
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 30.0)
        self.speed_spin.setSingleStep(0.5)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setValue(4.0)
        self.speed_spin.valueChanged.connect(self.speed_change_callback)

        speed_row = QHBoxLayout()
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.speed_spin, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addLayout(controls_row)
        layout.addLayout(speed_row)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    def playback_fps(self) -> float:
        return float(self.speed_spin.value())

    def set_playback_active(self, active: bool) -> None:
        self.play_btn.setEnabled(not active)
        self.stop_btn.setEnabled(active)
        self.status_label.setText('Playing' if active else 'Stopped')

    def set_frame_position(self, current_index: int, total: int) -> None:
        if total <= 0:
            self.status_label.setText('Stopped')
            return
        base = 'Playing' if not self.play_btn.isEnabled() else 'Stopped'
        self.status_label.setText(f'{base} | Frame {current_index + 1} / {total} | {self.playback_fps():.1f} fps')
