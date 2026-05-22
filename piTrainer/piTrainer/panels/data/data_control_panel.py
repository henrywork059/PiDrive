from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QVBoxLayout


class DataControlPanel(QGroupBox):
    def __init__(self, delete_frame_callback) -> None:
        super().__init__("Data Control")
        self.delete_frame_callback = delete_frame_callback

        help_label = QLabel("Data-changing actions for selected record rows. Tick the confirmation box once before hiding bad frames from training. The action keeps JSONL rows and image files, but adds traceable hidden flags.")
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.confirm_delete_check = QCheckBox("I confirm frame hide/delete actions")
        self.confirm_delete_check.setToolTip(
            "Required before Delete/Hide will add hidden_from_training flags. "
            "Rows and image files are kept for traceability, and repeated confirmation popups are skipped."
        )

        self.delete_btn = QPushButton("Hide Selected Frame(s)")
        self.delete_btn.setProperty('role', 'danger')
        self.delete_btn.clicked.connect(self.delete_frame_callback)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.confirm_delete_check)
        layout.addWidget(self.delete_btn)
        layout.addStretch(1)

    def deletion_confirmed(self) -> bool:
        return bool(self.confirm_delete_check.isChecked())
