from __future__ import annotations

from typing import Any
import re

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


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
    }

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []
        self.columns: list[str] = []
        self._source_rows: list[int] = []
        self._sort_column = -1
        self._sort_order = Qt.AscendingOrder

    def set_preview_rows(self, rows: list[dict[str, Any]], columns: list[str]) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.columns = list(columns)
        self._source_rows = list(range(len(self.rows)))
        self._sort_column = self.columns.index('frame_id') if 'frame_id' in self.columns else (0 if self.columns else -1)
        self._sort_order = Qt.AscendingOrder
        self._sort_rows_in_place()
        self.endResetModel()

    def source_row(self, view_row: int) -> int:
        if 0 <= view_row < len(self._source_rows):
            return int(self._source_rows[view_row])
        return -1

    def view_row_for_source_row(self, source_row: int) -> int:
        try:
            return self._source_rows.index(int(source_row))
        except ValueError:
            return -1

    def sort(self, column: int, order=Qt.AscendingOrder) -> None:  # noqa: N802 - Qt API name
        if column < 0 or column >= len(self.columns):
            return
        self.layoutAboutToBeChanged.emit()
        self._sort_column = int(column)
        self._sort_order = order
        self._sort_rows_in_place()
        self.layoutChanged.emit()

    def _sort_rows_in_place(self) -> None:
        if self._sort_column < 0 or self._sort_column >= len(self.columns):
            return
        column_name = self.columns[self._sort_column]
        pairs = list(zip(self.rows, self._source_rows))
        reverse = self._is_descending(self._sort_order)
        pairs.sort(key=lambda pair: self._sort_key(pair[0].get(column_name), column_name), reverse=reverse)
        self.rows = [row for row, _source in pairs]
        self._source_rows = [source for _row, source in pairs]

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

    def _sort_key(self, value: Any, column_name: str):
        if value is None or value == '':
            return (1, ())
        if column_name in {'steering', 'throttle', 'pred_steering', 'pred_throttle', 'steering_diff', 'speed_diff'}:
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
        if role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        if column_name in {"steering", "throttle", "pred_steering", "pred_throttle", "steering_diff", "speed_diff"}:
            try:
                return f"{float(value):.3f}"
            except (TypeError, ValueError):
                return ""
        return "" if value is None else str(value)

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
