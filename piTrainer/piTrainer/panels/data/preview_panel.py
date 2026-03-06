from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...services.data.preview_service import dataframe_preview_rows, preview_columns


class PreviewPanel(QGroupBox):
    def __init__(self, selection_callback=None, autoplay_callback=None) -> None:
        super().__init__("Record Preview")
        self.df = pd.DataFrame()
        self.selection_callback = selection_callback
        self.autoplay_callback = autoplay_callback

        self.summary_label = QLabel("Load sessions to preview recorded frames.")
        self.summary_label.setProperty('role', 'muted')
        self.summary_label.setWordWrap(True)

        self.autoplay_btn = QPushButton("Auto Play Frames")
        self.autoplay_btn.clicked.connect(self._handle_autoplay_clicked)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._handle_selection_change)

        header = QHBoxLayout()
        header.addWidget(self.summary_label, 1)
        header.addWidget(self.autoplay_btn)

        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(250)
        self.autoplay_timer.timeout.connect(self._advance_autoplay)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.table)
        self._refresh_summary()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.stop_autoplay()
        self._set_autoplay_button_state(False)
        self.df = df.reset_index(drop=True).copy()
        rows = dataframe_preview_rows(self.df)
        columns = preview_columns(rows)
        self.table.clear()
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        for row_idx, row in enumerate(rows):
            for col_idx, col in enumerate(columns):
                value = row.get(col, "")
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        self._refresh_summary()
        if rows:
            self.table.selectRow(0)
            self._handle_selection_change()
        elif self.selection_callback is not None:
            self.selection_callback("")

    def selected_record(self):
        row = self.current_row()
        if row < 0 or row >= len(self.df):
            return None
        return self.df.iloc[row].to_dict()

    def current_row(self) -> int:
        selected = self.table.selectedItems()
        if not selected:
            return -1
        return selected[0].row()

    def toggle_autoplay(self) -> bool:
        if self.autoplay_timer.isActive():
            self.stop_autoplay()
            self._set_autoplay_button_state(False)
            return False
        if len(self.df) <= 1:
            self._set_autoplay_button_state(False)
            return False
        self.autoplay_timer.start()
        self._set_autoplay_button_state(True)
        return True

    def stop_autoplay(self) -> None:
        if self.autoplay_timer.isActive():
            self.autoplay_timer.stop()

    def set_autoplay_active(self, active: bool) -> None:
        self._set_autoplay_button_state(active)

    def _handle_autoplay_clicked(self) -> None:
        if self.autoplay_callback is not None:
            self.autoplay_callback()
        else:
            self.toggle_autoplay()

    def _advance_autoplay(self) -> None:
        total = self.table.rowCount()
        if total <= 1:
            self.stop_autoplay()
            self._set_autoplay_button_state(False)
            return
        row = self.current_row()
        next_row = 0 if row < 0 else (row + 1) % total
        self.table.selectRow(next_row)
        self._handle_selection_change()

    def _handle_selection_change(self) -> None:
        if self.selection_callback is None:
            return
        row = self.current_row()
        if row < 0 or row >= len(self.df):
            self.selection_callback("")
            self._refresh_summary()
            return
        image_path = str(self.df.iloc[row].get("abs_image", ""))
        self.selection_callback(image_path)
        self._refresh_summary()

    def _set_autoplay_button_state(self, active: bool) -> None:
        self.autoplay_btn.setText("Stop Auto Play" if active else "Auto Play Frames")

    def _refresh_summary(self) -> None:
        total = len(self.df)
        row = self.current_row()
        if total == 0:
            self.summary_label.setText("No frames to preview. Load sessions or change the filter.")
            return
        if row < 0:
            self.summary_label.setText(f"Showing {total} frame(s). Select a row to inspect it.")
            return
        record = self.selected_record() or {}
        session = str(record.get('session', ''))
        frame_id = str(record.get('frame_id', ''))
        mode = str(record.get('mode', ''))
        self.summary_label.setText(
            f"Showing {total} frame(s). Selected: row {row + 1}, session '{session}', frame '{frame_id}', mode '{mode}'."
        )
