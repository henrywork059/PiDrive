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
)

from ...app_state import AppState


class ValidationConfigPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__('Validation Config')
        self.state = state

        self.model_source_combo = QComboBox()
        self.model_source_combo.addItems(['Current trained model', 'Load .keras / .h5 model'])

        self.dataset_source_combo = QComboBox()
        self.dataset_source_combo.addItems(['Validation split', 'Current filtered rows', 'Training split'])

        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText('Optional: browse to a saved .keras or .h5 model file')

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 512)
        self.batch_spin.setValue(max(1, int(getattr(self.state.train_config, 'batch_size', 32))))

        self.max_rows_spin = QSpinBox()
        self.max_rows_spin.setRange(0, 1000000)
        self.max_rows_spin.setSpecialValueText('All rows')
        self.max_rows_spin.setValue(0)

        form = QFormLayout()
        form.addRow('Model Source', self.model_source_combo)
        form.addRow('Dataset Source', self.dataset_source_combo)
        form.addRow('Model File', self.model_path_edit)
        form.addRow('Batch Size', self.batch_spin)
        form.addRow('Max Rows', self.max_rows_spin)

        helper = QPushButton('Use current export folder')
        helper.clicked.connect(self.fill_from_export_dir)

        helper_row = QHBoxLayout()
        helper_row.addWidget(helper)
        helper_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(helper_row)

    def browse_model_file(self, parent) -> None:
        path, _ = QFileDialog.getOpenFileName(
            parent,
            'Choose model file',
            str(Path(self.state.export_config.out_dir).expanduser()),
            'Keras Models (*.keras *.h5);;All Files (*)',
        )
        if path:
            self.model_path_edit.setText(path)
            self.model_source_combo.setCurrentText('Load .keras / .h5 model')

    def fill_from_export_dir(self) -> None:
        out_dir = Path(self.state.export_config.out_dir).expanduser()
        for pattern in ('*.keras', '*.h5'):
            matches = sorted(out_dir.glob(pattern))
            if matches:
                self.model_path_edit.setText(str(matches[-1]))
                self.model_source_combo.setCurrentText('Load .keras / .h5 model')
                return

    def push_to_state(self) -> None:
        self.state.last_error = ''

    def model_source(self) -> str:
        return self.model_source_combo.currentText()

    def dataset_source(self) -> str:
        return self.dataset_source_combo.currentText()

    def model_path(self) -> str:
        return self.model_path_edit.text().strip()

    def batch_size(self) -> int:
        return int(self.batch_spin.value())

    def max_rows(self) -> int:
        return int(self.max_rows_spin.value())
