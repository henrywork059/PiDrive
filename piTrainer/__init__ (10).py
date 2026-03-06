from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel


class ModelStatusPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Model Status")
        self.ready = QLabel("No")
        self.train_rows = QLabel("0")
        self.val_rows = QLabel("0")
        self.epochs_ran = QLabel("0")

        layout = QFormLayout(self)
        layout.addRow("Model ready", self.ready)
        layout.addRow("Train rows", self.train_rows)
        layout.addRow("Validation rows", self.val_rows)
        layout.addRow("Epochs recorded", self.epochs_ran)

    def set_status(self, model_ready: bool, train_rows: int, val_rows: int, epochs_ran: int) -> None:
        self.ready.setText("Yes" if model_ready else "No")
        self.train_rows.setText(str(train_rows))
        self.val_rows.setText(str(val_rows))
        self.epochs_ran.setText(str(epochs_ran))
