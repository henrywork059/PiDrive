from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCore import QModelIndex, QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QLabel,
    QVBoxLayout,
)
from PySide6.QtCore import QItemSelectionModel

from ...services.data.preview_service import dataframe_preview_rows, preview_columns
from .preview_model import RecordPreviewModel
from .preview_table import CyclingPreviewTable


class PreviewPanel(QGroupBox):
    def __init__(self, selection_callback=None, playback_state_callback=None) -> None:
        super().__init__('Records')
        self.df = pd.DataFrame()
        self.selection_callback = selection_callback
        self.playback_state_callback = playback_state_callback
        self._handling_selection = False
        self._restore_after_sort_rows: list[int] = []
        self._restore_after_sort_current_row = -1

        self.summary_label = QLabel('Load sessions to show frames.')
        self.summary_label.setProperty('role', 'muted')
        self.summary_label.setWordWrap(True)

        self.model = RecordPreviewModel()
        self.model.layoutAboutToBeChanged.connect(self._capture_selection_before_sort)
        self.model.layoutChanged.connect(self._restore_selection_after_sort)
        self.table = CyclingPreviewTable(self)
        self.table.setObjectName('recordPreviewTable')
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(True)
        self.table.setMinimumHeight(170)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalScrollBar().setTracking(True)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.selectionModel().selectionChanged.connect(lambda *_: self._handle_selection_change())
        self.table.selectionModel().currentChanged.connect(lambda *_: self._handle_selection_change())

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
        self._with_blocked_selection(lambda: self._reset_model(rows, columns))
        self._apply_column_widths()
        self._refresh_summary()
        if rows:
            self._select_view_row(0, emit=False, ensure_row_visible=False)
            self._handle_selection_change()
        elif self.selection_callback is not None:
            self.selection_callback(None)
        self._emit_playback_state()

    def _reset_model(self, rows: list[dict[str, Any]], columns: list[str]) -> None:
        self.model.set_preview_rows(rows, columns)
        self.table.clearSelection()
        if rows and columns:
            default_column = columns.index('frame_id') if 'frame_id' in columns else 0
            self.table.sortByColumn(default_column, Qt.AscendingOrder)
            first = self.model.index(0, 0)
            self._set_current_index(first)

    def _apply_column_widths(self) -> None:
        if self.model.columnCount() <= 0:
            return
        widths = {
            'frame_id': 125,
            'session': 190,
            'steering': 82,
            'throttle': 82,
            'pred_steering': 96,
            'pred_throttle': 88,
            'steering_diff': 88,
            'speed_diff': 88,
            'mode': 92,
            'ts': 170,
        }
        for column, column_name in enumerate(self.model.columns):
            self.table.setColumnWidth(column, widths.get(column_name, 110))
        self._schedule_first_column_visible()

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
        source_rows = [self.model.source_row(int(index.row())) for index in selection.selectedRows(0) if index.isValid()]
        return sorted(dict.fromkeys(row for row in source_rows if 0 <= row < len(self.df)))

    def current_row(self) -> int:
        index = self.table.currentIndex()
        if index.isValid():
            source_row = self.model.source_row(int(index.row()))
            if source_row >= 0:
                return source_row
        rows = self.selected_source_rows()
        return rows[0] if rows else -1

    def _current_view_row(self) -> int:
        index = self.table.currentIndex()
        return int(index.row()) if index.isValid() else self._view_row_for_source_row(self.current_row())

    def _view_row_for_source_row(self, source_row: int) -> int:
        return self.model.view_row_for_source_row(source_row)

    @staticmethod
    def _selection_flag(name: str):
        direct = getattr(QItemSelectionModel, name, None)
        if direct is not None:
            return direct
        enum = getattr(QItemSelectionModel, 'SelectionFlag', None)
        if enum is not None:
            return getattr(enum, name, None)
        return None

    def _selection_flags(self, *names: str):
        result = None
        for name in names:
            flag = self._selection_flag(name)
            if flag is None:
                continue
            result = flag if result is None else result | flag
        return result

    def _with_blocked_selection(self, func) -> None:
        selection_model = self.table.selectionModel()
        table_blocker = QSignalBlocker(self.table)
        selection_blocker = QSignalBlocker(selection_model) if selection_model is not None else None
        try:
            func()
        finally:
            del table_blocker
            if selection_blocker is not None:
                del selection_blocker

    def _set_current_index(self, index: QModelIndex, *, no_update: bool = True) -> None:
        if not index.isValid():
            return
        selection_model = self.table.selectionModel()
        if selection_model is not None and no_update:
            flags = self._selection_flags('NoUpdate')
            if flags is not None:
                try:
                    selection_model.setCurrentIndex(index, flags)
                    return
                except TypeError:
                    pass
        self.table.setCurrentIndex(index)

    def _capture_selection_before_sort(self) -> None:
        self._restore_after_sort_rows = self.selected_source_rows()
        self._restore_after_sort_current_row = self.current_row()

    def _restore_selection_after_sort(self) -> None:
        if not self._restore_after_sort_rows:
            self._schedule_first_column_visible()
            return
        selection_model = self.table.selectionModel()
        if selection_model is None:
            return

        def restore() -> None:
            self.table.clearSelection()
            select_flags = self._selection_flags('Select', 'Rows')
            for source_row in self._restore_after_sort_rows:
                view_row = self._view_row_for_source_row(source_row)
                if view_row < 0:
                    continue
                index = self.model.index(view_row, 0)
                if select_flags is not None:
                    selection_model.select(index, select_flags)
                else:
                    self.table.selectRow(view_row)
            current_view_row = self._view_row_for_source_row(self._restore_after_sort_current_row)
            if current_view_row < 0 and self._restore_after_sort_rows:
                current_view_row = self._view_row_for_source_row(self._restore_after_sort_rows[0])
            if current_view_row >= 0:
                self._set_current_index(self.model.index(current_view_row, 0), no_update=True)

        self._with_blocked_selection(restore)
        self._schedule_first_column_visible()
        self._handle_selection_change()

    def _anchor_current_to_first_column(self) -> None:
        if self.model.columnCount() <= 0:
            return
        current = self.table.currentIndex()
        if current.isValid():
            row = current.row()
        else:
            selected_rows = self.selected_source_rows()
            row = self._view_row_for_source_row(selected_rows[0]) if selected_rows else -1
        if row < 0 or row >= self.model.rowCount():
            return
        first_column_index = self.model.index(row, 0)
        if not current.isValid() or current.column() != 0:
            self._set_current_index(first_column_index, no_update=True)

    def _select_view_row(self, view_row: int, *, emit: bool = True, ensure_row_visible: bool = True) -> bool:
        if view_row < 0 or view_row >= self.model.rowCount():
            return False
        selection_model = self.table.selectionModel()
        if selection_model is None:
            return False
        index = self.model.index(view_row, 0)
        flags = self._selection_flags('ClearAndSelect', 'Rows')
        self._with_blocked_selection(lambda: self._select_index(selection_model, index, flags))
        self._keep_first_column_visible(ensure_row_visible=ensure_row_visible)
        if emit:
            self._handle_selection_change()
        return True

    def _select_index(self, selection_model, index: QModelIndex, flags) -> None:
        if flags is not None:
            selection_model.select(index, flags)
        else:
            self.table.clearSelection()
            self.table.selectRow(index.row())
        self._set_current_index(index, no_update=True)

    def select_record_identity(self, identity: tuple[str, str, str, str]) -> bool:
        if not identity:
            return False
        for source_row in range(len(self.df)):
            record = self.df.iloc[source_row].to_dict()
            if self.record_identity(record) == identity:
                view_row = self._view_row_for_source_row(source_row)
                return self._select_view_row(view_row)
        return False

    def update_record_values(
        self,
        identity: tuple[str, str, str, str],
        values: dict[str, float],
        *,
        preserve_selection: bool = False,
    ) -> bool:
        """Update visible row values without rebuilding the table."""
        if not identity or self.df.empty:
            return False
        matched_source_rows: list[int] = []
        for source_row in range(len(self.df)):
            record = self.df.iloc[source_row].to_dict()
            if self.record_identity(record) == identity:
                matched_source_rows.append(source_row)
        if not matched_source_rows:
            return False

        for source_row in matched_source_rows:
            for field_name, value in values.items():
                if field_name in self.df.columns:
                    self.df.at[source_row, field_name] = float(value)
                self.model.set_value(source_row, field_name, float(value))

        if not preserve_selection:
            view_row = self._view_row_for_source_row(matched_source_rows[0])
            if view_row >= 0:
                self._select_view_row(view_row, emit=False, ensure_row_visible=False)
        self._refresh_summary()
        self._schedule_first_column_visible()
        self._emit_playback_state()
        return True

    def sort_by_column_desc(self, column_name: str) -> bool:
        if column_name not in self.model.columns:
            return False
        column = self.model.columns.index(column_name)
        self.table.sortByColumn(column, Qt.DescendingOrder)
        self._schedule_first_column_visible()
        self.focus_table_for_keyboard()
        return True

    def focus_table_for_keyboard(self) -> None:
        """Return keyboard focus to the Records table after external actions.

        Buttons in the Deploy/Review panels keep focus after they are clicked, so
        plain Up/Down key presses can be consumed by those controls instead of
        cycling frames.  Refocusing the table keeps frame navigation available
        without forcing the user to click the table again.
        """
        self._anchor_current_to_first_column()
        self.table.setFocus(Qt.OtherFocusReason)

    def select_all_records(self) -> bool:
        total = self.model.rowCount()
        if total <= 0:
            return False
        def select_all() -> None:
            self.table.selectAll()
            self._set_current_index(self.model.index(0, 0), no_update=True)
        self._with_blocked_selection(select_all)
        self._keep_first_column_visible(ensure_row_visible=False)
        self._handle_selection_change()
        return True

    def select_adjacent_record(self, step: int) -> bool:
        total = self.model.rowCount()
        if total <= 0:
            return False
        view_row = self._current_view_row()
        if view_row < 0:
            target_row = 0 if step >= 0 else total - 1
        else:
            target_row = (view_row + int(step)) % total
        return self._select_view_row(target_row, ensure_row_visible=True)

    def set_playback_fps(self, fps: float) -> None:
        safe_fps = min(250.0, max(0.5, float(fps)))
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
        if self.model.rowCount() <= 0:
            self.stop_autoplay()
            return False
        if not self._select_view_row(0):
            return False
        return self.start_autoplay()

    def autoplay_active(self) -> bool:
        return bool(self.autoplay_timer.isActive())

    def total_rows(self) -> int:
        return int(self.model.rowCount())

    def _advance_autoplay(self) -> None:
        total = self.model.rowCount()
        if total <= 1:
            self.stop_autoplay()
            return
        view_row = self._current_view_row()
        next_view_row = 0 if view_row < 0 else (view_row + 1) % total
        self._select_view_row(next_view_row, ensure_row_visible=True)

    def _keep_first_column_visible(self, *, ensure_row_visible: bool = False) -> None:
        if self.model.columnCount() <= 0:
            return
        self._anchor_current_to_first_column()
        scrollbar = self.table.horizontalScrollBar()
        scrollbar.setValue(scrollbar.minimum())
        if ensure_row_visible:
            view_row = self._current_view_row()
            if 0 <= view_row < self.model.rowCount():
                self.table.scrollTo(self.model.index(view_row, 0), QAbstractItemView.EnsureVisible)
                scrollbar.setValue(scrollbar.minimum())

    def _schedule_first_column_visible(self) -> None:
        # Qt may auto-scroll horizontally after selection, resize, or current-index changes.
        # Re-anchor the first column without vertically re-centring the selected row.
        for delay_ms in (0, 30, 90, 180):
            QTimer.singleShot(delay_ms, self._keep_first_column_visible)

    def _handle_selection_change(self) -> None:
        if self._handling_selection:
            return
        self._handling_selection = True
        try:
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
        finally:
            self._handling_selection = False

    def _refresh_summary(self) -> None:
        total = len(self.df)
        row = self.current_row()
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
        display_row = row + 1
        self.summary_label.setText(
            f"Displaying {total} frame(s). Current: row {display_row}, session '{session}', frame '{frame_id}', mode '{mode}', Steering {steering:.3f}, Speed {throttle:.3f}.{selected_note}"
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
