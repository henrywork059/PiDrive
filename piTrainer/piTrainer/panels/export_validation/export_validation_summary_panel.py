from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class ExportValidationSummaryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Export Validation Summary')
        self.model_label = QLabel('TFLite model: none selected.')
        self.model_label.setProperty('role', 'summaryLine')
        self.model_label.setWordWrap(True)
        self.model_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.dataset_label = QLabel('Datasets: validation=0 | filtered=0 | training=0')
        self.dataset_label.setProperty('role', 'summaryLine')
        self.dataset_label.setWordWrap(True)
        self.dataset_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_label = QLabel('No export validation run yet.')
        self.result_label.setProperty('role', 'summaryBlock')
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.addWidget(self.model_label)
        layout.addWidget(self.dataset_label)
        layout.addWidget(self.result_label, 1)

    def set_model_state(self, tflite_path: str, dataset_rows: dict[str, int]) -> None:
        path_text = tflite_path if tflite_path else 'None selected'
        self.model_label.setText(f'TFLite model: {path_text}')
        self.dataset_label.setText(
            'Datasets: validation={validation} | filtered={filtered} | training={training}'.format(**dataset_rows)
        )

    def set_result_text(self, text: str) -> None:
        self.result_label.setText(text)
