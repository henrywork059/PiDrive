from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState
from ...ui.layout_widgets import CollapsibleSection, standardize_form_layout


class ExportValidationConfigPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__('Export Validation Config')
        self.state = state

        self.tflite_path_edit = QLineEdit()
        self.tflite_path_edit.setPlaceholderText('Browse to the exported .tflite model that will be copied to the car')

        self.dataset_source_combo = QComboBox()
        self.dataset_source_combo.addItems(['Validation split', 'Current filtered rows', 'Training split'])

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 512)
        self.batch_spin.setValue(max(1, int(getattr(self.state.train_config, 'batch_size', 32))))
        self.batch_spin.setToolTip('Used when the TFLite interpreter supports dynamic batches. Fixed batch-1 models are validated safely one frame at a time.')

        self.max_rows_spin = QSpinBox()
        self.max_rows_spin.setRange(0, 1000000)
        self.max_rows_spin.setSpecialValueText('All rows')
        self.max_rows_spin.setValue(0)

        helper = QPushButton('Use last/newest TFLite export')
        helper.clicked.connect(self.fill_from_export_dir)

        helper_widget = QWidget()
        helper_row = QHBoxLayout(helper_widget)
        helper_row.setContentsMargins(0, 0, 0, 0)
        helper_row.addWidget(helper)
        helper_row.addStretch(1)

        model_widget, model_form = self._section_form()
        model_form.addRow('TFLite Model', self.tflite_path_edit)
        model_form.addRow(helper_widget)

        dataset_widget, dataset_form = self._section_form()
        dataset_form.addRow('Dataset Source', self.dataset_source_combo)
        dataset_form.addRow('Batch Size', self.batch_spin)
        dataset_form.addRow('Max Rows', self.max_rows_spin)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(CollapsibleSection('TFLite Model Source', model_widget, expanded=True))
        layout.addWidget(CollapsibleSection('Dataset + Run Limits', dataset_widget, expanded=True))
        layout.addStretch(1)

        if getattr(self.state, 'last_exported_tflite_path', ''):
            self.set_tflite_path(getattr(self.state, 'last_exported_tflite_path', ''))

    def _section_form(self) -> tuple[QWidget, QFormLayout]:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        standardize_form_layout(form)
        return widget, form

    def browse_model_file(self, parent) -> None:
        path, _ = QFileDialog.getOpenFileName(
            parent,
            'Choose exported TFLite model',
            str(Path(self.state.export_config.out_dir).expanduser()),
            'TFLite Models (*.tflite);;All Files (*)',
        )
        if path:
            self.set_tflite_path(path)

    def fill_from_export_dir(self) -> None:
        last_path = Path(str(getattr(self.state, 'last_exported_tflite_path', '') or '')).expanduser()
        if str(last_path).strip() and last_path.exists():
            self.set_tflite_path(str(last_path))
            return

        out_dir = Path(self.state.export_config.out_dir).expanduser()
        matches = sorted(out_dir.glob('*.tflite'), key=lambda path: path.stat().st_mtime if path.exists() else 0.0)
        if matches:
            self.set_tflite_path(str(matches[-1]))

    def push_to_state(self) -> None:
        self.state.last_error = ''
        path = self.tflite_path()
        if path:
            self.state.last_exported_tflite_path = path

    def tflite_path(self) -> str:
        return self.tflite_path_edit.text().strip()

    def dataset_source(self) -> str:
        return self.dataset_source_combo.currentText()

    def batch_size(self) -> int:
        return int(self.batch_spin.value())

    def max_rows(self) -> int:
        return int(self.max_rows_spin.value())

    def set_tflite_path(self, path: str) -> None:
        self.tflite_path_edit.setText(str(path))
        if path:
            self.state.last_exported_tflite_path = str(path)
