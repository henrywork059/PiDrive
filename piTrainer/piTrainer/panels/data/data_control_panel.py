from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout


class DataControlPanel(QGroupBox):
    def __init__(self, delete_frame_callback, recover_last_callback, recover_all_callback) -> None:
        super().__init__("Delete and Recover")
        self.delete_frame_callback = delete_frame_callback
        self.recover_last_callback = recover_last_callback
        self.recover_all_callback = recover_all_callback

        help_label = QLabel(
            "Hide selected frame rows from training, or recover previously hidden rows. "
            "Hide is a soft delete: JSONL rows and image files are kept until hidden data is permanently cleaned."
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.confirm_delete_check = QCheckBox("I confirm frame hide/delete actions")
        self.confirm_delete_check.setToolTip(
            "Required before Delete/Hide will add hidden_from_training flags. "
            "Rows and image files are kept for traceability, and repeated confirmation popups are skipped."
        )

        self.delete_btn = QPushButton("Delete / Hide Selected Frame(s)")
        self.delete_btn.setProperty('role', 'danger')
        self.delete_btn.clicked.connect(self.delete_frame_callback)

        recover_label = QLabel("Recover hidden frames")
        recover_label.setProperty('role', 'sectionLabel')

        self.recover_count_spin = QSpinBox()
        self.recover_count_spin.setRange(1, 999999)
        self.recover_count_spin.setValue(1)
        self.recover_count_spin.setAlignment(Qt.AlignRight)
        self.recover_count_spin.setToolTip("Number of most-recently hidden frames to unhide.")

        recover_last_btn = QPushButton("Recover Last")
        recover_last_btn.setProperty('role', 'secondary')
        recover_last_btn.clicked.connect(self.recover_last_callback)

        recover_all_btn = QPushButton("Recover All Hidden Frames")
        recover_all_btn.setProperty('role', 'secondary')
        recover_all_btn.clicked.connect(self.recover_all_callback)

        recover_last_row = QHBoxLayout()
        recover_last_row.addWidget(QLabel("Last"))
        recover_last_row.addWidget(self.recover_count_spin)
        recover_last_row.addWidget(QLabel("frame(s)"))
        recover_last_row.addStretch(1)
        recover_last_row.addWidget(recover_last_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.confirm_delete_check)
        layout.addWidget(self.delete_btn)
        layout.addSpacing(8)
        layout.addWidget(recover_label)
        layout.addLayout(recover_last_row)
        layout.addWidget(recover_all_btn)
        layout.addStretch(1)

    def deletion_confirmed(self) -> bool:
        return bool(self.confirm_delete_check.isChecked())

    def recover_count(self) -> int:
        return int(self.recover_count_spin.value())
