from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class ValidationActionsPanel(QGroupBox):
    def __init__(self, browse_model_callback, validate_callback, clear_callback) -> None:
        super().__init__('Validation Actions')
        self.browse_button = QPushButton('Browse Model...')
        self.run_button = QPushButton('Run Validation')
        self.clear_button = QPushButton('Clear Results')

        self.browse_button.clicked.connect(browse_model_callback)
        self.run_button.clicked.connect(validate_callback)
        self.clear_button.clicked.connect(clear_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.clear_button)
        layout.addStretch(1)
