from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class ValidationSummaryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Validation Summary')
        self.model_label = QLabel('Model source: no in-memory model yet.')
        self.model_label.setWordWrap(True)
        self.dataset_label = QLabel('Datasets: validation=0 | filtered=0 | training=0')
        self.dataset_label.setWordWrap(True)
        self.result_label = QLabel('No validation run yet.')
        self.result_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.model_label)
        layout.addWidget(self.dataset_label)
        layout.addWidget(self.result_label, 1)

    def set_model_state(self, in_memory_ready: bool, current_model_path: str, dataset_rows: dict[str, int]) -> None:
        path_text = current_model_path if current_model_path else 'None selected'
        self.model_label.setText(
            f"In-memory model: {'ready' if in_memory_ready else 'not ready'} | External model path: {path_text}"
        )
        self.dataset_label.setText(
            'Datasets: validation={validation} | filtered={filtered} | training={training}'.format(**dataset_rows)
        )

    def set_result_text(self, text: str) -> None:
        self.result_label.setText(text)
