from __future__ import annotations

from PySide6.QtCore import Qt
from ...ui.typography import align_numeric_table_item
from PySide6.QtWidgets import (QAbstractItemView, QGroupBox, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)


class ConversionComparisonPanel(QGroupBox):
    def __init__(self, callback):
        super().__init__("Conversion comparison")
        self.comparison = None
        self.compare_button = QPushButton("Compare last completed results")
        self.compare_button.setAccessibleName("Compare last completed Keras and TFLite predictions")
        self.compare_button.clicked.connect(callback)
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.summary_label.setWordWrap(True)
        self.table = QTableWidget(0, 10)
        self.table.setAccessibleName("Largest matched prediction differences")
        self.table.setHorizontalHeaderLabels(["Row", "Session", "Frame", "Flip",
                                               "Keras steer", "TFLite steer", "|Δ steer|", "Keras speed", "TFLite speed", "|Δ speed|"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(150)
        self.table.setTextElideMode(Qt.ElideMiddle)
        self.row_detail = QLabel()
        self.row_detail.setTextFormat(Qt.PlainText)
        self.row_detail.setWordWrap(True)
        self.row_detail.setAccessibleName('Selected comparison record and both predictions')
        self.row_detail.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.table.currentCellChanged.connect(self._show_selected_record)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.compare_button)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.row_detail)
        self.invalidate()

    def invalidate(self):
        self.comparison = None
        self.table.setRowCount(0)
        self.row_detail.clear()
        self.summary_label.setToolTip("")
        self.summary_label.setText("Compare the last completed Validate and TFLite Check results. "
                                   "A matching recorded run and identical evaluated rows are required.")

    def set_comparison(self, result):
        self.invalidate()
        self.comparison = result
        if not result["available"]:
            self.summary_label.setText("Comparison unavailable: " + result["reason"])
            return
        n = result["rows_used"]
        self.summary_label.setText(
            f"Matched historical results: {n} rows | Run {result['run_id'][:12]}…\n"
            f"Steering |Δ| max {result['steering_max']:.3e}, mean {result['steering_mean']:.3e}\n"
            f"Speed |Δ| max {result['speed_max']:.3e}, mean {result['speed_mean']:.3e}\n"
            f"Showing {len(result['rows'])} largest differences (all rows included in metrics). "
            "Row hashes identify metadata, not image bytes. Numerical agreement is not driving accuracy or deployment approval.")
        self.summary_label.setToolTip(
            f"Run: {result['run_id']}\nEvaluated rows: {result['rows_sha256']}\n"
            f"Keras receipt: {result['keras_receipt']}\nTFLite receipt: {result['lite_receipt']}\n"
            f"Recorded TFLite model SHA-256: {result['model_sha256']}")
        self.table.setRowCount(len(result["rows"]))
        for i, row in enumerate(result["rows"]):
            values = (row["row"], row["session"], row["frame"], "Yes" if row["flipped"] else "No",
                      f"{row['keras_steering']:.7g}", f"{row['lite_steering']:.7g}",
                      f"{row['steering_delta']:.3e}", f"{row['keras_speed']:.7g}",
                      f"{row['lite_speed']:.7g}", f"{row['speed_delta']:.3e}")
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                if col == 0 or col >= 4:
                    align_numeric_table_item(item)
                self.table.setItem(i, col, item)
        self.table.resizeColumnsToContents()
        # Keep long identifiers from consuming the whole narrow viewport.
        # Full values stay in cells, tooltips and the selected-record detail.
        for col, cap in ((1, 150), (2, 96)):
            self.table.setColumnWidth(col, min(self.table.columnWidth(col), cap))
        if self.table.rowCount():
            self.table.setCurrentCell(0, 0)

    def _show_selected_record(self, row, *_):
        records = (self.comparison or {}).get("rows", [])
        if not 0 <= row < len(records):
            self.row_detail.clear()
            return
        value = records[row]
        self.row_detail.setText(
            f"Row {value['row']} · {value['session']} · {value['frame']} · Flip: {value['flipped']}\n"
            f"Steering: {value['keras_steering']:.7g} → {value['lite_steering']:.7g} | Δ {value['steering_delta']:.3e}\n"
            f"Speed: {value['keras_speed']:.7g} → {value['lite_speed']:.7g} | Δ {value['speed_delta']:.3e}")
