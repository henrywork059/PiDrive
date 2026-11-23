"""Compact shared progress/status display for long piTrainer operations."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class TaskProgressPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.step_label = QLabel('Task: idle')
        self.step_label.setWordWrap(True)
        self.step_label.setObjectName('backgroundTaskStep')
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.result_label = QLabel('')
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_label.setObjectName('backgroundTaskResult')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)
        layout.addWidget(self.step_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.result_label)

    def begin(self, title: str) -> None:
        self.step_label.setText(f'Running: {title}')
        self.progress.setRange(0, 0)  # Indeterminate until measured.
        self.result_label.setText('In progress — no output confirmed yet.')

    def set_step(self, step: str, percent: int = -1) -> None:
        self.step_label.setText(str(step))
        if percent < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, int(percent))))

    def succeed(self, message: str, paths=()) -> None:
        self.step_label.setText(f'Succeeded: {message}')
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        paths = tuple(str(p) for p in paths if str(p).strip())
        self.result_label.setText(
            'Output path(s):\n' + '\n'.join(paths) if paths
            else 'No output files were created by this task.'
        )

    def fail(self, message: str) -> None:
        self.step_label.setText('Failed')
        self.progress.setRange(0, 100)
        self.result_label.setText(f'{message}\nNo completed output is confirmed.')

    def cancel(self, message: str) -> None:
        self.step_label.setText('Cancelled')
        self.progress.setRange(0, 100)
        self.result_label.setText(f'{message}\nNo model was accepted from this run.')

    def stop_requested(self) -> None:
        self.step_label.setText('Stop requested — waiting for a safe epoch boundary.')
