from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QWidget

from ...app_state import AppState


class ExportOptionsPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__("Export Options")
        self.state = state
        cfg = self.state.export_config

        self.out_dir = QLineEdit(cfg.out_dir)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)

        self.base_name = QLineEdit(cfg.base_name)
        self.export_keras = QCheckBox("Export .keras")
        self.export_keras.setChecked(cfg.export_keras)
        self.export_tflite = QCheckBox("Export .tflite")
        self.export_tflite.setChecked(cfg.export_tflite)
        self.quantize_int8 = QCheckBox("INT8 quantize TFLite")
        self.quantize_int8.setChecked(cfg.quantize_int8)

        out_row = QWidget()
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.addWidget(self.out_dir, 1)
        out_layout.addWidget(browse_btn)

        layout = QFormLayout(self)
        layout.addRow("Output directory", out_row)
        layout.addRow("Base file name", self.base_name)
        layout.addRow(self.export_keras)
        layout.addRow(self.export_tflite)
        layout.addRow(self.quantize_int8)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose output directory", self.out_dir.text().strip())
        if folder:
            self.out_dir.setText(folder)

    def push_to_state(self) -> None:
        cfg = self.state.export_config
        cfg.out_dir = self.out_dir.text().strip()
        cfg.base_name = self.base_name.text().strip()
        cfg.export_keras = self.export_keras.isChecked()
        cfg.export_tflite = self.export_tflite.isChecked()
        cfg.quantize_int8 = self.quantize_int8.isChecked()
