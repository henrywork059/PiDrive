"""Read-only comparison of training-run records by stable R40 run IDs."""
from __future__ import annotations

from pathlib import Path
import re

from ...ui.typography import align_numeric_table_item
from ...ui.context_icons import set_context_icon

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ...services.train.experiment_service import comparison_rows, inspect_model_provenance


class TrainComparisonPanel(QGroupBox):
    def __init__(self, refresh_callback) -> None:
        super().__init__("Compare Training Runs")
        self._records: dict[str, dict] = {}
        self._validation_receipts: list[dict] = []
        self.run_a = QComboBox()
        self.run_b = QComboBox()
        self.run_a.setAccessibleName("First training run")
        self.run_b.setAccessibleName("Second training run")
        self.run_a.setToolTip("First training run (stable run ID)")
        self.run_b.setToolTip("Second training run (stable run ID)")
        self.refresh_btn = QPushButton("Refresh Runs")
        set_context_icon(self.refresh_btn, "refresh")
        self.refresh_btn.clicked.connect(refresh_callback)
        self.inspect_btn = QPushButton("Inspect Model")
        set_context_icon(self.inspect_btn, "search")
        self.inspect_btn.clicked.connect(self.inspect_model)
        self.info = QLabel("No saved training run summaries found.")
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.PlainText)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Metric", "Run A", "Run B"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 235)

        selector = QHBoxLayout()
        selector.addWidget(QLabel("A"))
        selector.addWidget(self.run_a, 1)
        selector.addWidget(QLabel("B"))
        selector.addWidget(self.run_b, 1)
        selector.addWidget(self.refresh_btn)
        selector.addWidget(self.inspect_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(selector)
        layout.addWidget(self.info)
        layout.addWidget(self.table, 1)

        self.run_a.currentIndexChanged.connect(self._render)
        self.run_b.currentIndexChanged.connect(self._render)

    def set_records(self, records: list[dict], receipts: list[dict] | None = None) -> None:
        self._validation_receipts = list(receipts or [])
        old_a, old_b = self.run_a.currentData(), self.run_b.currentData()
        self._records = {r["run_id"]: r for r in records if isinstance(r, dict) and r.get("run_id")}
        self.run_a.blockSignals(True)
        self.run_b.blockSignals(True)
        self.run_a.clear()
        self.run_b.clear()
        for record in records:
            run_id = record.get("run_id")
            if run_id not in self._records:
                continue
            label = f"{str(record.get('started_at_utc', 'Unknown'))[:19]} | {record.get('status', 'Unknown')} | {run_id[:8]}"
            self.run_a.addItem(label, run_id)
            self.run_b.addItem(label, run_id)
        if self.run_a.count():
            index_a = self.run_a.findData(old_a)
            self.run_a.setCurrentIndex(index_a if index_a >= 0 else 0)
        if self.run_b.count():
            index_b = self.run_b.findData(old_b)
            self.run_b.setCurrentIndex(index_b if index_b >= 0 else min(1, self.run_b.count() - 1))
        self.run_a.blockSignals(False)
        self.run_b.blockSignals(False)
        self._render()

    def _render(self, *_args) -> None:
        left_id = self.run_a.currentData()
        right_id = self.run_b.currentData()
        self.table.setRowCount(0)
        if not left_id:
            self.info.setText("Unknown — no R40 run summaries in this working folder. Historical models are not inferred.")
            return
        a = self._records.get(left_id)
        b = self._records.get(right_id) if right_id != left_id else None
        if not a:
            self.info.setText("Unknown — the selected run metadata is unavailable.")
            return
        self.info.setText(f"Run A: {left_id}\nRun B: {right_id if b else 'Select a different run to compare'}\nUnknown means metadata was not recorded, not zero.")
        rows = comparison_rows(a, b)
        def validation_context(run_id):
            matches = [item for item in self._validation_receipts if item.get("training_run_id") == run_id] if run_id else []
            if not matches:
                return "Unknown — no linked local validation summary"
            return "\n".join(str(item.get("receipt_path") or "Unknown") for item in matches[:5])
        rows.append(("Local validation summaries (latest 5)", validation_context(left_id),
                     validation_context(right_id if b else None)))
        self._render_rows(rows)

    def _render_rows(self, rows) -> None:
        self.table.setRowCount(len(rows))
        for index, (field, value_a, value_b) in enumerate(rows):
            for col, value in enumerate((field, value_a, value_b)):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                if col:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    # Do not reinterpret paths, identifiers, Unknown or mixed units.
                    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", str(value)):
                        align_numeric_table_item(item)
                self.table.setItem(index, col, item)
        self.table.resizeRowsToContents()

    def inspect_model(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Inspect trained model provenance", str(Path.home()),
            "Trained models (*.keras *.tflite);;All files (*)",
        )
        if not path:
            return
        self.inspect_model_path(path)

    def inspect_model_path(self, path: str) -> None:
        record, message = inspect_model_provenance(path)
        selected = str(Path(path).expanduser().resolve())
        if record is None:
            self.table.setRowCount(0)
            self.info.setText(f"{message}\nSelected model: {selected}")
            return
        run_id = record.get("run_id")
        # Only verified local sidecars may populate the existing run selectors.
        if run_id and record.get("status") == "succeeded":
            if run_id not in self._records:
                self._records[run_id] = record
                label = f"External model | {run_id[:8]}"
                self.run_a.blockSignals(True)
                self.run_b.blockSignals(True)
                self.run_a.addItem(label, run_id)
                self.run_b.addItem(label, run_id)
                self.run_a.blockSignals(False)
                self.run_b.blockSignals(False)
            index = self.run_a.findData(run_id)
            if index >= 0:
                self.run_a.setCurrentIndex(index)
        # Display selected artifact metadata, not a stale same-ID local record.
        rows = comparison_rows(record, None)
        checksum = (record.get("model_binding") or {}).get("model_sha256")
        matches = [item for item in self._validation_receipts
                   if checksum and item.get("model_sha256") == checksum]
        receipt_details = [
            f"Validation: {item.get('validation_id') or 'Unknown'} | "
            f"Training run: {item.get('training_run_id') or 'Unknown'}\n"
            f"{item.get('receipt_path') or 'Unknown'}"
            for item in matches[:5]
        ]
        rows.extend([
            ("Selected model", selected, "Unknown"),
            ("Selected model SHA-256", checksum or "Unknown", "Unknown"),
            ("Local checks of this file hash (latest 5)",
             "\n".join(receipt_details) or "Unknown — no matching local validation summary", "Unknown"),
        ])
        self._render_rows(rows)
        self.info.setText(f"{message}\nSelected model: {selected}\nRun ID: {run_id or 'Unknown'}\n"
                          "Read-only model inspection; select runs or Refresh Runs to compare.")
