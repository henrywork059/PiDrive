from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from ...app_state import AppState


class RootPathPanel(QGroupBox):
    def __init__(self, state: AppState, refresh_callback) -> None:
        super().__init__("Records Root")
        self.state = state
        self.refresh_callback = refresh_callback

        self.path_edit = QLineEdit(self.state.records_root)
        self.path_edit.editingFinished.connect(self._apply_path)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)

        refresh_btn = QPushButton("Refresh Sessions")
        refresh_btn.clicked.connect(self._refresh)

        row = QHBoxLayout()
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse_btn)
        row.addWidget(refresh_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Folder containing session folders and records.jsonl files."))
        layout.addLayout(row)

    def _apply_path(self) -> None:
        self.state.records_root = self.path_edit.text().strip()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose records root", self.path_edit.text().strip())
        if folder:
            self.path_edit.setText(folder)
            self._apply_path()
            self.refresh_callback()

    def _refresh(self) -> None:
        self._apply_path()
        self.refresh_callback()
