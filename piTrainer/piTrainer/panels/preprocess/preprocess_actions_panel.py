from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class PreprocessActionsPanel(QGroupBox):
    def __init__(self, preview_callback, apply_callback, reset_callback, sync_callback, save_settings_callback, save_data_callback) -> None:
        super().__init__('Preprocess Actions')

        preview_btn = QPushButton('Preview Preprocess')
        preview_btn.clicked.connect(preview_callback)

        apply_btn = QPushButton('Confirm and Start Preprocess')
        apply_btn.clicked.connect(apply_callback)

        reset_btn = QPushButton('Reset Preprocess')
        reset_btn.clicked.connect(reset_callback)

        save_settings_btn = QPushButton('Save Preprocess Settings')
        save_settings_btn.clicked.connect(save_settings_callback)

        save_data_btn = QPushButton('Save Preprocessed Data')
        save_data_btn.clicked.connect(save_data_callback)

        sync_btn = QPushButton('Sync Image Size to Train Tab')
        sync_btn.clicked.connect(sync_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(preview_btn)
        layout.addWidget(apply_btn)
        layout.addWidget(reset_btn)
        layout.addWidget(save_settings_btn)
        layout.addWidget(save_data_btn)
        layout.addWidget(sync_btn)
        layout.addStretch(1)
