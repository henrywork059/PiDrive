from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem, QVBoxLayout

from ...services.data.preview_service import dataframe_preview_rows, preview_columns


class PreviewPanel(QGroupBox):
    def __init__(self, selection_callback=None) -> None:
        super().__init__("Record Preview")
        self.df = pd.DataFrame()
        self.selection_callback = selection_callback

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._handle_selection_change)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df.copy()
        rows = dataframe_preview_rows(df)
        columns = preview_columns(rows)
        self.table.clear()
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        for row_idx, row in enumerate(rows):
            for col_idx, col in enumerate(columns):
                value = row.get(col, "")
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        if rows:
            self.table.selectRow(0)
            self._handle_selection_change()
        elif self.selection_callback is not None:
            self.selection_callback("")

    def _handle_selection_change(self) -> None:
        if self.selection_callback is None:
            return
        selected = self.table.selectedItems()
        if not selected:
            self.selection_callback("")
            return
        row = selected[0].row()
        if row >= len(self.df):
            self.selection_callback("")
            return
        image_path = str(self.df.iloc[row].get("abs_image", ""))
        self.selection_callback(image_path)
