from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class MergeSessionsPanel(QGroupBox):
    def __init__(self, merge_callback) -> None:
        super().__init__('Merge Sessions')
        self.merge_callback = merge_callback

        help_label = QLabel(
            'Merge the currently selected sessions into one new session folder. '
            'Images and JSONL rows are copied into a new merged session.'
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('merged_session_name')
        self.load_after_merge_check = QCheckBox('Load merged session after merge')
        self.load_after_merge_check.setChecked(True)

        merge_btn = QPushButton('Merge Selected Sessions')
        merge_btn.clicked.connect(self._on_merge_clicked)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('New session name'))
        name_row.addWidget(self.name_edit, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addLayout(name_row)
        layout.addWidget(self.load_after_merge_check)
        layout.addWidget(merge_btn)
        layout.addStretch(1)

    def merged_session_name(self) -> str:
        return self.name_edit.text().strip()

    def should_load_after_merge(self) -> bool:
        return self.load_after_merge_check.isChecked()

    def set_merged_session_name(self, value: str) -> None:
        self.name_edit.setText(value)

    def _on_merge_clicked(self) -> None:
        self.merge_callback()
