from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QItemSelectionModel

from ...ui.layout_widgets import CollapsibleSection

from ...panels.data.preview_model import RecordPreviewModel
from ...panels.data.preview_table import CyclingPreviewTable
from ...services.data.augmentation_service import truthy_value
from ...services.data.overlay_service import apply_prediction_comparison_overlay
from ...services.validation.validation_service import validation_preview_rows
from ...utils.image_utils import load_scaled_pixmap


ReviewIdentity = tuple[str, str, str, str, str, str, str]
ReviewGroupKey = tuple[str, str, str]


class ValidationFrameReviewPanel(QGroupBox):
    def __init__(self, edit_in_data_callback=None) -> None:
        super().__init__('Frame Review')
        self.edit_in_data_callback = edit_in_data_callback
        self.result: dict | None = None
        self.all_rows: list[dict[str, Any]] = []
        self.rows: list[dict[str, Any]] = []
        self._handling_selection = False
        self._restore_after_sort_rows: list[int] = []
        self._restore_after_sort_current_row = -1
        self._pending_restore_identity: ReviewIdentity | None = None
        self._last_selected_identity: ReviewIdentity | None = None
        self._edited_group_keys: set[ReviewGroupKey] = set()

        self.help_label = QLabel(
            'Review validated frames, filter high errors, and open the source frame in Data for label edits. '
            'Rows edited after this validation run are highlighted; mirrored/generated copies are highlighted too.'
        )
        self.help_label.setWordWrap(True)
        self.help_label.setProperty('role', 'muted')

        self.bad_only_checkbox = QCheckBox('Only bad predictions')
        self.bad_only_checkbox.toggled.connect(self._apply_filters)
        self.error_threshold_spin = QDoubleSpinBox()
        self.error_threshold_spin.setRange(0.0, 10.0)
        self.error_threshold_spin.setDecimals(3)
        self.error_threshold_spin.setSingleStep(0.05)
        self.error_threshold_spin.setValue(0.250)
        self.error_threshold_spin.valueChanged.connect(self._apply_filters)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['Worst first', 'Original order', 'Best first'])
        self.sort_combo.currentTextChanged.connect(self._apply_filters)
        self.count_label = QLabel('0 frame(s)')
        self.count_label.setProperty('role', 'muted')

        self.model = RecordPreviewModel()
        self.model.layoutAboutToBeChanged.connect(self._capture_selection_before_sort)
        self.model.layoutChanged.connect(self._restore_selection_after_sort)
        self.table = CyclingPreviewTable(self)
        self.table.setObjectName('validationFrameReviewTable')
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

        self.image_label = QLabel('No frame selected.')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(180)
        self.image_label.setWordWrap(True)

        self.resize_preview_timer = QTimer(self)
        self.resize_preview_timer.setSingleShot(True)
        self.resize_preview_timer.setInterval(140)
        self.resize_preview_timer.timeout.connect(self._refresh_preview)

        self.meta_label = QLabel('')
        self.meta_label.setWordWrap(True)
        self.meta_label.setProperty('role', 'muted')

        self.best_button = QPushButton('Best')
        self.best_button.setProperty('role', 'secondary')
        self.best_button.clicked.connect(self._select_best)
        self.worst_button = QPushButton('Worst')
        self.worst_button.setProperty('role', 'secondary')
        self.worst_button.clicked.connect(self._select_worst)
        self.edit_button = QPushButton('Edit in Data')
        self.edit_button.setProperty('role', 'primary')
        self.edit_button.clicked.connect(self._edit_current_frame)
        self.edit_button.setToolTip('Open the selected row in Data. Synthetic rows open their source frame.')

        controls_widget = QWidget()
        top_controls = QGridLayout(controls_widget)
        top_controls.setContentsMargins(0, 0, 0, 0)
        top_controls.addWidget(self.bad_only_checkbox, 0, 0)
        top_controls.addWidget(QLabel('Bad threshold'), 0, 1)
        top_controls.addWidget(self.error_threshold_spin, 0, 2)
        top_controls.addWidget(QLabel('Order'), 1, 0)
        top_controls.addWidget(self.sort_combo, 1, 1, 1, 2)
        top_controls.addWidget(self.count_label, 1, 3)
        top_controls.setColumnStretch(4, 1)

        action_row = QHBoxLayout()
        action_row.addWidget(self.best_button)
        action_row.addWidget(self.worst_button)
        action_row.addStretch(1)
        action_row.addWidget(self.edit_button)

        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.addWidget(self.image_label, 1)
        preview_layout.addWidget(self.meta_label)
        preview_layout.addLayout(action_row)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(CollapsibleSection('Filter + Sort', controls_widget, expanded=False))
        layout.addWidget(self.help_label)
        layout.addWidget(splitter, 1)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        if self.selected_row() is not None:
            self.resize_preview_timer.start()

    @staticmethod
    def _row_identity(row: dict[str, Any] | None) -> ReviewIdentity | None:
        if not row:
            return None
        return (
            str(row.get('result_index', '')),
            str(row.get('session', '')),
            str(row.get('frame_id', '')),
            str(row.get('ts', '')),
            str(row.get('abs_image', '')),
            str(row.get('source_frame_id', '')),
            str(row.get('synthetic_variant', '')),
        )

    @staticmethod
    def _normalized_session(row: dict[str, Any]) -> str:
        return str(row.get('session', '') or '').strip()

    @staticmethod
    def _normalized_frame_id(row: dict[str, Any], key: str = 'frame_id') -> str:
        return str(row.get(key, '') or '').strip()

    @staticmethod
    def _image_name(row: dict[str, Any]) -> str:
        return Path(str(row.get('abs_image', '') or row.get('image_path', '') or row.get('frame', '') or '')).name.strip()

    @classmethod
    def _record_group_keys(cls, row: dict[str, Any] | None) -> set[ReviewGroupKey]:
        if not row:
            return set()
        session = cls._normalized_session(row)
        keys: set[ReviewGroupKey] = set()
        frame_id = cls._normalized_frame_id(row)
        source_frame_id = cls._normalized_frame_id(row, 'source_frame_id')
        image_name = cls._image_name(row)
        if session and frame_id:
            keys.add(('frame', session, frame_id))
        if session and source_frame_id:
            keys.add(('frame', session, source_frame_id))
        if session and image_name:
            keys.add(('image', session, image_name))
        return keys

    @classmethod
    def _record_direct_keys(cls, row: dict[str, Any] | None) -> set[ReviewGroupKey]:
        if not row:
            return set()
        session = cls._normalized_session(row)
        frame_id = cls._normalized_frame_id(row)
        return {('frame', session, frame_id)} if session and frame_id else set()

    @staticmethod
    def _is_generated_or_mirrored(row: dict[str, Any]) -> bool:
        frame_id = str(row.get('frame_id', '') or '').strip()
        source_frame_id = str(row.get('source_frame_id', '') or '').strip()
        variant = str(row.get('synthetic_variant', '') or '').strip()
        return bool(
            truthy_value(row.get('aug_flip_lr', False), default=False)
            or variant
            or (source_frame_id and source_frame_id != frame_id)
        )

    def _apply_edit_marker_to_row(self, row: dict[str, Any]) -> dict[str, Any]:
        marked = dict(row)
        direct_match = bool(self._record_direct_keys(row) & self._edited_group_keys)
        group_match = bool(self._record_group_keys(row) & self._edited_group_keys)
        if not group_match:
            marked.pop('_validation_edit_status', None)
            marked.pop('_validation_edit_tooltip', None)
            return marked

        if direct_match and not self._is_generated_or_mirrored(row):
            marked['_validation_edit_status'] = 'edited'
            marked['_validation_edit_tooltip'] = 'Edited in Data after this validation run. Re-run validation to refresh true/error values.'
        else:
            marked['_validation_edit_status'] = 'mirrored'
            marked['_validation_edit_tooltip'] = 'Mirrored/generated copy of a row edited in Data after this validation run.'
        return marked

    def set_result(self, result: dict | None) -> None:
        self.result = result
        self.all_rows = [self._apply_edit_marker_to_row(row) for row in validation_preview_rows(result)]
        self._apply_filters()

    def mark_edited_records(self, records: list[dict] | dict | None) -> None:
        if not records:
            return
        if isinstance(records, dict):
            records = [records]
        new_keys: set[ReviewGroupKey] = set()
        for record in records:
            new_keys.update(self._record_group_keys(dict(record)))
        if not new_keys:
            return
        self._edited_group_keys.update(new_keys)
        preferred = self._pending_restore_identity or self._last_selected_identity or self._row_identity(self.selected_row())
        self.all_rows = [self._apply_edit_marker_to_row(row) for row in self.all_rows]
        self._apply_filters(preferred_identity=preferred)

    def restore_pending_selection(self) -> None:
        preferred = self._pending_restore_identity or self._last_selected_identity
        if preferred:
            self._select_row_identity(preferred)
        self.focus_table_for_keyboard()

    def selected_row(self) -> dict | None:
        row_idx = self.current_row()
        if row_idx < 0 or row_idx >= len(self.rows):
            return None
        return self.rows[row_idx]

    def selected_source_rows(self) -> list[int]:
        selection = self.table.selectionModel()
        if selection is None:
            return []
        source_rows = [self.model.source_row(int(index.row())) for index in selection.selectedRows(0) if index.isValid()]
        return sorted(dict.fromkeys(row for row in source_rows if 0 <= row < len(self.rows)))

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

    def _select_row_identity(self, identity: ReviewIdentity | None) -> bool:
        if not identity:
            return False
        for source_row, row in enumerate(self.rows):
            if self._row_identity(row) == identity:
                return self._select_view_row(self._view_row_for_source_row(source_row))
        return False

    def _apply_filters(self, *_, preferred_identity: ReviewIdentity | None = None) -> None:
        preferred_identity = preferred_identity or self._pending_restore_identity or self._last_selected_identity or self._row_identity(self.selected_row())
        rows = list(self.all_rows)
        if self.bad_only_checkbox.isChecked():
            threshold = float(self.error_threshold_spin.value())
            rows = [row for row in rows if float(row.get('combined_error', 0.0) or 0.0) >= threshold]
        order = self.sort_combo.currentText()
        if order == 'Worst first':
            rows.sort(key=lambda row: float(row.get('combined_error', 0.0) or 0.0), reverse=True)
        elif order == 'Best first':
            rows.sort(key=lambda row: float(row.get('combined_error', 0.0) or 0.0))
        else:
            rows.sort(key=lambda row: int(row.get('row_number', 0) or 0))
        self.rows = rows
        self._populate_table(preferred_identity=preferred_identity)
        self.count_label.setText(f'{len(self.rows)} frame(s)')
        self._refresh_preview()

    def _populate_table(self, *, preferred_identity: ReviewIdentity | None = None) -> None:
        columns = [
            'frame_id', 'session', 'target_steering', 'pred_steering', 'target_speed', 'pred_speed',
            'combined_error', 'mode', 'row_number', 'frame_number', 'ts', 'source_frame_id', 'synthetic_variant',
        ]
        present_columns = [column for column in columns if any(str(row.get(column, '')).strip() for row in self.rows)]
        if not present_columns and self.rows:
            present_columns = columns[:10]
        self._with_blocked_selection(lambda: self.model.set_preview_rows(self.rows, present_columns))
        self._sort_to_current_order()
        self._apply_column_widths()
        restored = self._select_row_identity(preferred_identity) if preferred_identity else False
        if not restored and self.rows:
            self._select_view_row(0, emit=False, ensure_row_visible=False)
            self._handle_selection_change()
        elif not self.rows:
            self.image_label.clear()
            self.image_label.setText('No frame selected.')
            self.meta_label.setText('Run validation or loosen the bad-frame filter.')
        self._schedule_first_column_visible()

    def _sort_to_current_order(self) -> None:
        if not self.rows or not self.model.columns:
            return
        order_text = self.sort_combo.currentText()
        if order_text in {'Worst first', 'Best first'} and 'combined_error' in self.model.columns:
            order = Qt.DescendingOrder if order_text == 'Worst first' else Qt.AscendingOrder
            self.table.sortByColumn(self.model.columns.index('combined_error'), order)
        elif 'row_number' in self.model.columns:
            self.table.sortByColumn(self.model.columns.index('row_number'), Qt.AscendingOrder)

    def _apply_column_widths(self) -> None:
        widths = {
            'frame_id': 125,
            'session': 190,
            'target_steering': 96,
            'pred_steering': 96,
            'target_speed': 86,
            'pred_speed': 86,
            'combined_error': 88,
            'mode': 92,
            'row_number': 70,
            'frame_number': 80,
            'ts': 170,
            'source_frame_id': 120,
            'synthetic_variant': 110,
        }
        for column, column_name in enumerate(self.model.columns):
            self.table.setColumnWidth(column, widths.get(column_name, 110))
        self._schedule_first_column_visible()

    def select_adjacent_record(self, step: int) -> bool:
        total = self.model.rowCount()
        if total <= 0:
            return False
        view_row = self._current_view_row()
        target_row = 0 if view_row < 0 and step >= 0 else total - 1 if view_row < 0 else (view_row + int(step)) % total
        return self._select_view_row(target_row, ensure_row_visible=True)

    def focus_table_for_keyboard(self) -> None:
        self._anchor_current_to_first_column()
        self.table.setFocus(Qt.OtherFocusReason)

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
        for delay_ms in (0, 30, 90, 180):
            QTimer.singleShot(delay_ms, self._keep_first_column_visible)

    def _handle_selection_change(self) -> None:
        if self._handling_selection:
            return
        self._handling_selection = True
        try:
            row = self.selected_row()
            if row is not None:
                self._last_selected_identity = self._row_identity(row)
            self._schedule_first_column_visible()
            self._refresh_preview()
        finally:
            self._handling_selection = False

    def _select_best(self) -> None:
        if not self.rows:
            return
        best_source = min(range(len(self.rows)), key=lambda index: float(self.rows[index].get('combined_error', 0.0) or 0.0))
        self._select_view_row(self._view_row_for_source_row(best_source))
        self.focus_table_for_keyboard()

    def _select_worst(self) -> None:
        if not self.rows:
            return
        worst_source = max(range(len(self.rows)), key=lambda index: float(self.rows[index].get('combined_error', 0.0) or 0.0))
        self._select_view_row(self._view_row_for_source_row(worst_source))
        self.focus_table_for_keyboard()

    def _edit_current_frame(self) -> None:
        row = self.selected_row()
        if row and self.edit_in_data_callback is not None:
            self._pending_restore_identity = self._row_identity(row)
            self.edit_in_data_callback(dict(row))

    def _refresh_preview(self) -> None:
        row = self.selected_row()
        if row is None:
            self.image_label.clear()
            self.image_label.setText('Select a row to preview it.')
            self.meta_label.setText('')
            return
        target_width = max(260, self.image_label.width() - 14)
        target_height = max(180, self.image_label.height() - 14)
        flip_lr = truthy_value(row.get('aug_flip_lr', False), default=False)
        pixmap = load_scaled_pixmap(str(row.get('abs_image', '')), target_width, target_height, flip_lr=flip_lr)
        if pixmap is None:
            self.image_label.clear()
            self.image_label.setText('Image unavailable')
        else:
            rendered = apply_prediction_comparison_overlay(
                pixmap,
                steering_true=float(row.get('target_steering', 0.0) or 0.0),
                speed_true=float(row.get('target_speed', 0.0) or 0.0),
                steering_pred=float(row.get('pred_steering', 0.0) or 0.0),
                speed_pred=float(row.get('pred_speed', 0.0) or 0.0),
                overlay_settings=row.get('overlay_settings') if isinstance(row.get('overlay_settings'), dict) else {},
            )
            self.image_label.setText('')
            self.image_label.setPixmap(rendered)
        source_frame_id = str(row.get('source_frame_id', '')).strip()
        synthetic_variant = str(row.get('synthetic_variant', '')).strip()
        warning = str(row.get('flip_label_warning', '')).strip()
        edit_note = str(row.get('_validation_edit_tooltip', '')).strip()
        edit_suffix = f'\nEdit marker: {edit_note}' if edit_note else ''
        self.meta_label.setText(
            (
                'Row {row_number} | Session: {session} | Mode: {mode} | Frame ID: {frame_id} | Frame No.: {frame_number}\n'
                'Horizontal flip: {flip_note}{source_suffix}{variant_suffix}{warning_suffix}\n'
                'Target Steering/Speed: {target_steering:.3f} / {target_speed:.3f} | '
                'AI Steering/Speed: {pred_steering:.3f} / {pred_speed:.3f} | '
                'Combined error: {combined_error:.4f}{edit_suffix}'
            ).format(
                row_number=int(row.get('row_number', 0) or 0),
                session=str(row.get('session', '')),
                mode=str(row.get('mode', '')),
                frame_id=str(row.get('frame_id', '')),
                frame_number=str(row.get('frame_number', '')),
                flip_note='Yes' if flip_lr else 'No',
                source_suffix=f' | Source: {source_frame_id}' if source_frame_id else '',
                variant_suffix=f' | Variant: {synthetic_variant}' if synthetic_variant else '',
                warning_suffix=f' | WARNING: {warning}' if warning else '',
                target_steering=float(row.get('target_steering', 0.0) or 0.0),
                target_speed=float(row.get('target_speed', 0.0) or 0.0),
                pred_steering=float(row.get('pred_steering', 0.0) or 0.0),
                pred_speed=float(row.get('pred_speed', 0.0) or 0.0),
                combined_error=float(row.get('combined_error', 0.0) or 0.0),
                edit_suffix=edit_suffix,
            )
        )
