from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...services.data.preview_service import dataframe_preview_rows, preview_columns


class PreviewPanel(QGroupBox):
    def __init__(self, selection_callback=None, playback_state_callback=None) -> None:
        super().__init__("Record Preview")
        self.df = pd.DataFrame()
        self.selection_callback = selection_callback
        self.playback_state_callback = playback_state_callback

        self.summary_label = QLabel("Load sessions to preview recorded frames.")
        self.summary_label.setProperty('role', 'muted')
        self.summary_label.setWordWrap(True)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._handle_selection_change)

        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(250)
        self.autoplay_timer.timeout.connect(self._advance_autoplay)

        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)
        self._refresh_summary()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.stop_autoplay()
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
            self.selection_callback(None)
        self._emit_playback_state()

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

    def set_playback_fps(self, fps: float) -> None:
        safe_fps = max(0.5, float(fps))
        interval_ms = max(1, int(round(1000.0 / safe_fps)))
        self.autoplay_timer.setInterval(interval_ms)
        self._emit_playback_state()

    def playback_fps(self) -> float:
        interval = max(1, int(self.autoplay_timer.interval()))
        return 1000.0 / float(interval)

    def start_autoplay(self) -> bool:
        if len(self.df) <= 1:
            self._emit_playback_state()
            return False
        self.autoplay_timer.start()
        self._emit_playback_state()
        return True

    def stop_autoplay(self) -> None:
        if self.autoplay_timer.isActive():
            self.autoplay_timer.stop()
        self._emit_playback_state()

    def restart_autoplay(self) -> bool:
        if self.table.rowCount() <= 0:
            self.stop_autoplay()
            return False
        self.table.selectRow(0)
        self._handle_selection_change()
        return self.start_autoplay()

    def autoplay_active(self) -> bool:
        return bool(self.autoplay_timer.isActive())

    def total_rows(self) -> int:
        return int(self.table.rowCount())

    def _advance_autoplay(self) -> None:
        total = self.table.rowCount()
        if total <= 1:
            self.stop_autoplay()
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
            self.selection_callback(None)
            self._refresh_summary()
            self._emit_playback_state()
            return
        self.selection_callback(self.selected_record())
        self._refresh_summary()
        self._emit_playback_state()

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

    def _emit_playback_state(self) -> None:
        if self.playback_state_callback is not None:
            row = self.current_row()
            self.playback_state_callback(
                {
                    'active': self.autoplay_active(),
                    'current_index': 0 if row < 0 else row,
                    'total': self.total_rows(),
                    'fps': self.playback_fps(),
                }
            )
