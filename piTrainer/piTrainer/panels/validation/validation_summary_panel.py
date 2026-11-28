from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class ValidationSummaryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Summary')
        self.model_label = QLabel('Model: none ready.')
        self.model_label.setProperty('role', 'summaryLine')
        self.model_label.setWordWrap(True)
        self.model_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.dataset_label = QLabel('Rows: val=0 | filtered=0 | train=0')
        self.dataset_label.setProperty('role', 'summaryLine')
        self.dataset_label.setWordWrap(True)
        self.dataset_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.scope_label = QLabel('Selected source: not yet available')
        self.scope_label.setTextFormat(Qt.PlainText)
        self.scope_label.setWordWrap(True)
        self.scope_label.setObjectName('validationSelectedScope')
        self.result_label = QLabel('No validation yet.')
        self.result_label.setProperty('role', 'summaryBlock')
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.addWidget(self.model_label)
        layout.addWidget(self.dataset_label)
        layout.addWidget(self.scope_label)
        layout.addWidget(self.result_label, 1)

    def set_model_state(self, in_memory_ready: bool, current_model_path: str, dataset_rows: dict[str, int]) -> None:
        path_text = current_model_path if current_model_path else 'None selected'
        self.model_label.setText(
            f"Model: {'in memory' if in_memory_ready else 'not ready'} | File: {path_text}"
        )
        self.dataset_label.setText(
            'Rows: val={validation} | filtered={filtered} | train={training}'.format(**dataset_rows)
        )

    def set_selected_scope(self, source: str, count: int, limit: int) -> None:
        # Preserve the existing source key and validation semantics. Explain
        # the historical All visible rows label rather than implying Data's filter.
        description = ('Active training rows (not the Data review filter)'
                       if source == 'All visible rows' else source)
        cap = str(limit) if limit > 0 else 'all'
        self.scope_label.setText(f'Selected source: {description} | {count} candidate row(s) | max: {cap}. '
                                 'Actual evaluated rows are reported in the last run result.')

    def set_result_text(self, text: str) -> None:
        self.result_label.setText(text)
