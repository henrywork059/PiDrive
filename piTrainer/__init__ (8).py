from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel


class SplitSummaryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Split Summary")
        self.total_rows = QLabel("0")
        self.train_rows = QLabel("0")
        self.val_rows = QLabel("0")
        self.sessions = QLabel("0")
        self.model_ready = QLabel("No")

        layout = QFormLayout(self)
        layout.addRow("Loaded rows", self.total_rows)
        layout.addRow("Train rows", self.train_rows)
        layout.addRow("Validation rows", self.val_rows)
        layout.addRow("Sessions", self.sessions)
        layout.addRow("Model ready", self.model_ready)

    def set_counts(self, total_rows: int, train_rows: int, val_rows: int, sessions: int, model_ready: bool) -> None:
        self.total_rows.setText(str(total_rows))
        self.train_rows.setText(str(train_rows))
        self.val_rows.setText(str(val_rows))
        self.sessions.setText(str(sessions))
        self.model_ready.setText("Yes" if model_ready else "No")
