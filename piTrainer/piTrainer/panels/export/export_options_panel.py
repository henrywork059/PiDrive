from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ...app_state import AppState
from ...ui.layout_widgets import CollapsibleSection, standardize_form_layout


class ExportOptionsPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__("Export Options")
        self.state = state
        cfg = self.state.export_config

        self.out_dir = QLineEdit(cfg.out_dir)
        browse_btn = QPushButton("Browse")
        browse_btn.setProperty('role', 'amber')
        browse_btn.clicked.connect(self._browse)

        self.base_name = QLineEdit(cfg.base_name)
        self.export_keras = QCheckBox("Export .keras")
        self.export_keras.setChecked(cfg.export_keras)
        self.export_tflite = QCheckBox("Export .tflite")
        self.export_tflite.setChecked(cfg.export_tflite)
        self.quantize_int8 = QCheckBox("Reduce TFLite size (quantized, float I/O)")
        self.quantize_int8.setChecked(cfg.quantize_int8)
        self.quantize_int8.setToolTip("Uses TensorFlow Lite size optimisation while keeping float32 input/output for the PiDrive runtime.")

        out_row = QWidget()
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.addWidget(self.out_dir, 1)
        out_layout.addWidget(browse_btn)

        destination_widget = QWidget()
        destination_form = QFormLayout(destination_widget)
        destination_form.setContentsMargins(0, 0, 0, 0)
        standardize_form_layout(destination_form)
        destination_form.addRow("Output directory", out_row)
        destination_form.addRow("Base file name", self.base_name)

        artifact_widget = QWidget()
        artifact_layout = QVBoxLayout(artifact_widget)
        artifact_layout.setContentsMargins(0, 0, 0, 0)
        artifact_layout.addWidget(self.export_keras)
        artifact_layout.addWidget(self.export_tflite)
        artifact_layout.addWidget(self.quantize_int8)
        artifact_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(CollapsibleSection('Destination', destination_widget, expanded=True))
        layout.addWidget(CollapsibleSection('Artifact Types', artifact_widget, expanded=True))
        layout.addStretch(1)

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
