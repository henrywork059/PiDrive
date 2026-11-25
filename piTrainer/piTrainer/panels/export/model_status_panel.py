from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel

from ...ui.layout_widgets import standardize_form_layout


class ModelStatusPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Model")
        self.ready = QLabel("No")
        self.train_rows = QLabel("Unknown")
        self.val_rows = QLabel("Unknown")
        self.epochs_ran = QLabel("Unknown")
        self.run_id = QLabel("Unknown")
        self.run_id.setAccessibleName("Model training run")
        self.run_id.setWordWrap(True)

        for label in (self.ready, self.train_rows, self.val_rows, self.epochs_ran, self.run_id):
            label.setProperty('role', 'statValue')
        layout = standardize_form_layout(QFormLayout(self))
        layout.addRow("Model ready", self.ready)
        layout.addRow("Run train rows", self.train_rows)
        layout.addRow("Run val rows", self.val_rows)
        layout.addRow("Epochs", self.epochs_ran)
        layout.addRow("Training run", self.run_id)

    def set_status(self, model_ready: bool, train_rows: int | None, val_rows: int | None,
                   epochs_ran: int | None, run_id: str | None = None) -> None:
        self.ready.setText("Yes" if model_ready else "No")
        for label, value in ((self.train_rows, train_rows), (self.val_rows, val_rows), (self.epochs_ran, epochs_ran)):
            label.setText(str(value) if value is not None else "Unknown")
        self.run_id.setText(str(run_id)[:12] if run_id else "Unknown")
        self.run_id.setToolTip(str(run_id) if run_id else "No tracked run for this model")
