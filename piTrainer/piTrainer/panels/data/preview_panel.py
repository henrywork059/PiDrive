from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...services.data.preview_service import dataframe_preview_rows, preview_columns


class PreviewPanel(QGroupBox):
    def __init__(self, selection_callback=None, playback_state_callback=None) -> None:
        super().__init__('Record Preview')
        self.df = pd.DataFrame()
        self.selection_callback = selection_callback
        self.playback_state_callback = playback_state_callback

        self.summary_label = QLabel('Load sessions to preview recorded frames.')
        self.summary_label.setProperty('role', 'muted')
        self.summary_label.setWordWrap(True)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(True)
        self.table.setMinimumHeight(170)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalScrollBar().setTracking(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.itemSelectionChanged.connect(self._handle_selection_change)

        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(250)
        self.autoplay_timer.timeout.connect(self._advance_autoplay)

        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)
        self._refresh_summary()

    @staticmethod
    def record_identity(record) -> tuple[str, str, str, str]:
        if not record:
            return ('', '', '', '')
        return (
            str(record.get('session', '')),
            str(record.get('frame_id', '')),
            str(record.get('ts', '')),
            str(record.get('abs_image', '')),
        )

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.stop_autoplay()
        self.df = df.reset_index(drop=True).copy()
        rows = dataframe_preview_rows(self.df)
        columns = preview_columns(rows)
        self.table.clear()
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setSortingEnabled(False)
        for row_idx, row in enumerate(rows):
            for col_idx, col in enumerate(columns):
                value = row.get(col, '')
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row_idx)
                self.table.setItem(row_idx, col_idx, item)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        self._refresh_summary()
        if rows:
            self.table.selectRow(0)
            self.table.setCurrentCell(0, 0)
            self._keep_first_column_visible()
            self._handle_selection_change()
        elif self.selection_callback is not None:
            self.selection_callback(None)
        self._emit_playback_state()

    def selected_record(self):
        row = self.current_row()
        if row < 0 or row >= len(self.df):
            return None
        return self.df.iloc[row].to_dict()

    def selected_records(self) -> list[dict]:
        records: list[dict] = []
        for row in self.selected_source_rows():
            if 0 <= row < len(self.df):
                records.append(self.df.iloc[row].to_dict())
        return records

    def selected_source_rows(self) -> list[int]:
        selection = self.table.selectionModel()
        if selection is None:
            return []
        rows: list[int] = []
        for index in selection.selectedRows():
            item = self.table.item(index.row(), 0)
            source_row = item.data(Qt.UserRole) if item is not None else index.row()
            try:
                rows.append(int(source_row))
            except (TypeError, ValueError):
                rows.append(int(index.row()))
        # Keep source order stable for delete/reporting, and de-duplicate row selections.
        return sorted(dict.fromkeys(rows))

    def current_row(self) -> int:
        item = self.table.currentItem()
        if item is None:
            rows = self.selected_source_rows()
            return rows[0] if rows else -1
        source_row = item.data(Qt.UserRole)
        try:
            return int(source_row)
        except (TypeError, ValueError):
            return item.row()

    def _current_view_row(self) -> int:
        item = self.table.currentItem()
        if item is not None:
            return int(item.row())
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() is not None else []
        return int(rows[0].row()) if rows else -1

    def _view_row_for_source_row(self, source_row: int) -> int:
        for view_row in range(self.table.rowCount()):
            item = self.table.item(view_row, 0)
            if item is None:
                continue
            try:
                if int(item.data(Qt.UserRole)) == int(source_row):
                    return view_row
            except (TypeError, ValueError):
                continue
        return -1

    def select_record_identity(self, identity: tuple[str, str, str, str]) -> bool:
        if not identity:
            return False
        for source_row in range(len(self.df)):
            record = self.df.iloc[source_row].to_dict()
            if self.record_identity(record) == identity:
                view_row = self._view_row_for_source_row(source_row)
                if view_row < 0:
                    return False
                self.table.clearSelection()
                self.table.selectRow(view_row)
                self.table.setCurrentCell(view_row, 0)
                self._handle_selection_change()
                return True
        return False

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
        self.table.clearSelection()
        self.table.selectRow(0)
        self.table.setCurrentCell(0, 0)
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
        view_row = self._current_view_row()
        next_view_row = 0 if view_row < 0 else (view_row + 1) % total
        self.table.clearSelection()
        self.table.selectRow(next_view_row)
        self.table.setCurrentCell(next_view_row, 0)
        self._handle_selection_change()

    def _keep_first_column_visible(self) -> None:
        if self.table.columnCount() <= 0:
            return
        scrollbar = self.table.horizontalScrollBar()
        scrollbar.setValue(scrollbar.minimum())
        view_row = self._current_view_row()
        if view_row >= 0:
            first_item = self.table.item(view_row, 0)
            if first_item is not None:
                self.table.scrollToItem(first_item, QAbstractItemView.EnsureVisible)
                scrollbar.setValue(scrollbar.minimum())

    def _schedule_first_column_visible(self) -> None:
        QTimer.singleShot(0, self._keep_first_column_visible)

    def _handle_selection_change(self) -> None:
        self._schedule_first_column_visible()
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
        view_row = self._current_view_row()
        if total == 0:
            self.summary_label.setText('No frames to preview. Load sessions or change the filter.')
            return
        if row < 0:
            self.summary_label.setText(f'Displaying {total} frame(s). Select a row to inspect it.')
            return
        record = self.selected_record() or {}
        session = str(record.get('session', ''))
        frame_id = str(record.get('frame_id', ''))
        mode = str(record.get('mode', ''))
        steering = float(record.get('steering', 0.0) or 0.0)
        throttle = float(record.get('throttle', 0.0) or 0.0)
        selected_count = len(self.selected_source_rows())
        selected_note = f" {selected_count} row(s) selected." if selected_count > 1 else ""
        display_row = view_row + 1 if view_row >= 0 else row + 1
        self.summary_label.setText(
            f"Displaying {total} frame(s). Current: row {display_row}, session '{session}', frame '{frame_id}', mode '{mode}', steering {steering:.3f}, speed {throttle:.3f}.{selected_note}"
        )

    def _emit_playback_state(self) -> None:
        if self.playback_state_callback is not None:
            row = self._current_view_row()
            self.playback_state_callback(
                {
                    'active': self.autoplay_active(),
                    'current_index': 0 if row < 0 else row,
                    'total': self.total_rows(),
                    'fps': self.playback_fps(),
                }
            )
