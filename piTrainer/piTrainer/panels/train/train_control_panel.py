from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QProgressBar, QPushButton, QVBoxLayout


class TrainControlPanel(QGroupBox):
    def __init__(self, prepare_callback, start_callback, stop_callback, save_model_callback) -> None:
        super().__init__("Training Controls")
        self.prepare_btn = QPushButton("Prepare Split")
        self.prepare_btn.clicked.connect(prepare_callback)
        self.start_btn = QPushButton("Start Training")
        self.start_btn.clicked.connect(start_callback)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(stop_callback)
        self.stop_btn.setEnabled(False)
        self.save_model_btn = QPushButton('Save Trained Model')
        self.save_model_btn.clicked.connect(save_model_callback)

        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0)

        row1 = QHBoxLayout(); row1.addWidget(self.prepare_btn); row1.addWidget(self.start_btn); row1.addWidget(self.stop_btn)
        row2 = QHBoxLayout(); row2.addWidget(self.save_model_btn); row2.addStretch(1)

        layout = QVBoxLayout(self); layout.addLayout(row1); layout.addLayout(row2); layout.addWidget(self.progress)

    def set_running(self, running: bool) -> None:
        self.prepare_btn.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.save_model_btn.setEnabled(not running)
        if not running:
            self.progress.setValue(0)

    def set_progress(self, value: int) -> None:
        self.progress.setValue(max(0, min(100, int(value))))
