from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from ...services.data.preview_service import dataframe_preview_rows, preview_columns
from ...utils.image_utils import load_scaled_pixmap


class PreviewPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Preview")
        self.df = pd.DataFrame()

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._update_image_preview)

        self.image_label = QLabel("No preview")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(280)

        layout = QHBoxLayout(self)
        layout.addWidget(self.table, 2)
        layout.addWidget(self.image_label, 1)

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
            self._update_image_preview()
        else:
            self.image_label.setText("No preview")

    def _update_image_preview(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            self.image_label.setText("No preview")
            return
        row = selected[0].row()
        if row >= len(self.df):
            return
        image_path = str(self.df.iloc[row].get("abs_image", ""))
        pixmap = load_scaled_pixmap(image_path, width=420, height=300)
        if pixmap is None:
            self.image_label.setText("Image not available")
            return
        self.image_label.setPixmap(pixmap)
