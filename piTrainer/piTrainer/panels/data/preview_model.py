from __future__ import annotations

from functools import lru_cache
from typing import Any
import re

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor

from ...ui.theme import theme_color


class RecordPreviewModel(QAbstractTableModel):
    """Small read-only model for the Records table.

    Keeping the table model simple avoids item-based current-cell side effects
    that previously scrolled the view to later columns during multi-row
    selection. The model keeps an explicit source-row mapping so header sorting
    does not break selection, preview, bulk edit, or hide/delete operations.
    """

    HEADER_LABELS = {
        'frame_id': 'Frame',
        'frame_number': 'Frame No.',
        'session': 'Session',
        'steering': 'Steering',
        'throttle': 'Speed',
        'pred_steering': 'AI Steering',
        'pred_throttle': 'AI Speed',
        'steering_diff': 'Steering Diff',
        'speed_diff': 'Speed Diff',
        'mode': 'Mode',
        'ts': 'Time',
        'abs_image': 'Image path',
        'image_path': 'Image',
        'source_frame_id': 'Source',
        'synthetic_variant': 'Variant',
        'aug_flip_lr': 'Flip',
        'hidden_from_training': 'Hidden',
        'row_number': 'Row',
        'target_steering': 'True Steering',
        'target_speed': 'True Speed',
        'pred_speed': 'AI Speed',
        'combined_error': 'Error',
    }

    NUMERIC_COLUMNS = {
        'steering', 'throttle', 'pred_steering', 'pred_throttle', 'steering_diff', 'speed_diff',
        'target_steering', 'target_speed', 'pred_speed', 'combined_error',
    }

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []
        self.columns: list[str] = []
        self._source_rows: list[int] = []
        self._view_rows: list[int] = []
        self._sort_column = -1
        self._sort_order = Qt.AscendingOrder

    def set_preview_rows(self, rows: list[dict[str, Any]], columns: list[str]) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.columns = list(columns)
        self._source_rows = list(range(len(self.rows)))
        self._sort_column = -1
        self._sort_order = Qt.AscendingOrder
        self._sort_rows_by_default_order()
        self._rebuild_source_lookup()
        self.endResetModel()

    def source_row(self, view_row: int) -> int:
        if 0 <= view_row < len(self._source_rows):
            return int(self._source_rows[view_row])
        return -1

    def _rebuild_source_lookup(self) -> None:
        # Source rows are dense indices into the current dataframe. Rebuild
        # once per reset/sort; selection and bulk edits no longer scan O(n)
        # rows for each source identity.
        self._view_rows = [-1] * len(self._source_rows)
        for view, source in enumerate(self._source_rows):
            self._view_rows[source] = view

    def view_row_for_source_row(self, source_row: int) -> int:
        try:
            source = int(source_row)
        except ValueError:
            return -1
        if 0 <= source < len(self._view_rows):
            return self._view_rows[source]
        return -1

    def sort(self, column: int, order=Qt.AscendingOrder) -> None:  # noqa: N802 - Qt API name
        if column < 0 or column >= len(self.columns):
            return
        self.layoutAboutToBeChanged.emit()
        # Qt's selection model creates persistent indexes while handling the
        # about-to-change signal. Preserve their source-row identities across
        # the reorder, before notifying Qt that the new layout is available.
        old_indexes = self.persistentIndexList()
        identities = [(self.source_row(index.row()), index.column())
                      for index in old_indexes]
        self._sort_column = int(column)
        self._sort_order = order
        self._sort_rows_in_place()
        self._rebuild_source_lookup()
        new_indexes = [self.index(view, column) if view >= 0 else QModelIndex()
                       for source, column in identities
                       for view in [self.view_row_for_source_row(source)]]
        self.changePersistentIndexList(old_indexes, new_indexes)
        self.layoutChanged.emit()

    def _sort_rows_in_place(self) -> None:
        if self._sort_column < 0 or self._sort_column >= len(self.columns):
            return
        column_name = self.columns[self._sort_column]
        rows, sources = self.rows, self._source_rows
        order = list(range(len(rows)))
        reverse = self._is_descending(self._sort_order)
        order.sort(key=lambda index: self._sort_key_for_row(rows[index], column_name), reverse=reverse)
        self.rows = [rows[index] for index in order]
        self._source_rows = [sources[index] for index in order]

    def _sort_rows_by_default_order(self) -> None:
        """Default review order: chronological session, then frame id.

        PiSD frame ids can restart in separate sessions/days. Sorting by frame id
        alone can interleave two recordings. The default table order therefore
        keeps each session together by the date/time embedded in the session name
        or timestamp, then uses natural frame-id order inside that session.
        """
        if not self.rows:
            return
        rows, sources = self.rows, self._source_rows
        # The sort-local cache is bounded and cannot outlive the source rows.
        session_key = lru_cache(maxsize=256)(self._session_datetime_key)

        def key(index):
            row = rows[index]
            session, timestamp = row.get('session', ''), row.get('ts', '')
            if type(session) is str and type(timestamp) is str:
                return (session_key(session, timestamp),
                        self._sort_key(row.get('frame_id', ''), 'frame_id'),
                        int(sources[index]))
            return self._default_sort_key(row, sources[index])

        order = list(range(len(rows)))
        order.sort(key=key)
        self.rows = [rows[index] for index in order]
        self._source_rows = [sources[index] for index in order]

    def _default_sort_key(self, row: dict[str, Any], source_row: int):
        return (
            self._session_datetime_key(row.get('session', ''), row.get('ts', '')),
            self._sort_key(row.get('frame_id', ''), 'frame_id'),
            int(source_row),
        )

    def _sort_key_for_row(self, row: dict[str, Any], column_name: str):
        if column_name == 'session':
            return self._session_datetime_key(row.get('session', ''), row.get('ts', ''))
        return self._sort_key(row.get(column_name), column_name)

    @staticmethod
    def _is_descending(order) -> bool:
        descending = getattr(Qt, 'DescendingOrder', None)
        if descending is None:
            sort_order = getattr(Qt, 'SortOrder', None)
            descending = getattr(sort_order, 'DescendingOrder', None) if sort_order is not None else None
        return bool(descending is not None and order == descending)

    @staticmethod
    def _natural_key(value: Any):
        text = '' if value is None else str(value)
        parts = re.split(r'(\d+)', text.lower())
        return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts if part != '')

    @classmethod
    def _session_datetime_key(cls, session_value: Any, ts_value: Any = ''):
        session_text = '' if session_value is None else str(session_value)
        ts_text = '' if ts_value is None else str(ts_value)
        for text in (f'{session_text} {ts_text}', session_text, ts_text):
            key = cls._extract_datetime_key(text)
            if key is not None:
                return (0, key, session_text.lower())
        return (1, cls._natural_key(session_text))

    @staticmethod
    def _valid_datetime_tuple(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0):
        if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            return None
        return (year, month, day, hour, minute, second)

    @classmethod
    def _extract_datetime_key(cls, text: str):
        text = str(text or '')
        if not text:
            return None

        # Common PiSD forms:
        #   YYYY-MM-DD/YYYYMMDD_HHMMSS_...
        #   PiSD_recording_YYYY-MM-DD_YYYYMMDD_HHMMSS_...
        #   session_YYYYMMDD-HHMMSS
        compact_matches = list(re.finditer(r'(20\d{2})(\d{2})(\d{2})[_-]?(\d{2})(\d{2})(\d{2})', text))
        if compact_matches:
            match = compact_matches[-1]
            values = tuple(int(part) for part in match.groups())
            return cls._valid_datetime_tuple(*values)

        separated = re.search(
            r'(20\d{2})[-_/](\d{2})[-_/](\d{2})[^0-9]+(\d{2})[:_-](\d{2})[:_-](\d{2})',
            text,
        )
        if separated:
            values = tuple(int(part) for part in separated.groups())
            return cls._valid_datetime_tuple(*values)

        # If only a date is available, still keep sessions in day order.
        date_match = re.search(r'(20\d{2})[-_/]?(\d{2})[-_/]?(\d{2})', text)
        if date_match:
            year, month, day = (int(part) for part in date_match.groups())
            return cls._valid_datetime_tuple(year, month, day)
        return None

    def _sort_key(self, value: Any, column_name: str):
        if value is None or value == '':
            return (1, ())
        if column_name in self.NUMERIC_COLUMNS:
            try:
                return (0, 0, float(value))
            except (TypeError, ValueError):
                return (0, 1, str(value).lower())
        if column_name == 'frame_id':
            return (0, self._natural_key(value))
        return (0, str(value).lower())

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API name
        if parent is not None and parent.isValid():
            return 0
        return len(self.rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API name
        if parent is not None and parent.isValid():
            return 0
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802 - Qt API name
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        if row < 0 or row >= len(self.rows) or column < 0 or column >= len(self.columns):
            return None
        column_name = self.columns[column]
        value = self.rows[row].get(column_name, "")
        if role == Qt.UserRole:
            return self.source_row(row)
        edit_status = str(self.rows[row].get('_validation_edit_status', '') or '').strip()
        if role == Qt.BackgroundRole and edit_status:
            color_name = 'warning_surface' if edit_status == 'edited' else 'info_surface'
            return QBrush(QColor(theme_color(color_name)))
        if role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        if column_name in self.NUMERIC_COLUMNS:
            try:
                display = f"{float(value):.3f}"
            except (TypeError, ValueError):
                display = ""
        else:
            display = "" if value is None else str(value)
        if role == Qt.ToolTipRole:
            tooltip = str(self.rows[row].get('_validation_edit_tooltip', '') or '').strip()
            return f"{display}\n{tooltip}" if tooltip else display
        return display

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802 - Qt API name
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self.columns):
                column = self.columns[section]
                return self.HEADER_LABELS.get(column, column)
            return None
        return section + 1

    def set_value(self, source_row: int, field_name: str, value: float) -> None:
        view_row = self.view_row_for_source_row(source_row)
        if view_row < 0 or view_row >= len(self.rows):
            return
        self.rows[view_row][field_name] = value
        if field_name not in self.columns:
            return
        column = self.columns.index(field_name)
        model_index = self.index(view_row, column)
        self.dataChanged.emit(model_index, model_index, [Qt.DisplayRole, Qt.ToolTipRole])
