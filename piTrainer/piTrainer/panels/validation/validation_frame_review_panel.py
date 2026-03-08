from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...services.data.overlay_service import apply_prediction_comparison_overlay
from ...services.validation.validation_service import validation_preview_rows
from ...utils.image_utils import load_scaled_pixmap


class ValidationFrameReviewPanel(QGroupBox):
    def __init__(self, edit_in_data_callback=None) -> None:
        super().__init__('Validation Frame Review')
        self.edit_in_data_callback = edit_in_data_callback
        self.result: dict | None = None
        self.all_rows: list[dict] = []
        self.rows: list[dict] = []

        self.help_label = QLabel(
            'Browse validated frames, filter bad predictions, and open a selected frame back in the Data tab for raw-label editing.'
        )
        self.help_label.setWordWrap(True)
        self.help_label.setProperty('role', 'muted')

        self.bad_only_checkbox = QCheckBox('Show only bad predictions')
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

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._refresh_preview)

        self.image_label = QLabel('No validation frame selected.')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(320)
        self.image_label.setWordWrap(True)

        self.meta_label = QLabel('')
        self.meta_label.setWordWrap(True)
        self.meta_label.setProperty('role', 'muted')

        self.best_button = QPushButton('Best')
        self.best_button.clicked.connect(self._select_best)
        self.worst_button = QPushButton('Worst')
        self.worst_button.clicked.connect(self._select_worst)
        self.edit_button = QPushButton('Edit in Data')
        self.edit_button.clicked.connect(self._edit_current_frame)

        top_controls = QGridLayout()
        top_controls.addWidget(self.bad_only_checkbox, 0, 0)
        top_controls.addWidget(QLabel('Bad threshold'), 0, 1)
        top_controls.addWidget(self.error_threshold_spin, 0, 2)
        top_controls.addWidget(QLabel('Order'), 0, 3)
        top_controls.addWidget(self.sort_combo, 0, 4)
        top_controls.addWidget(self.count_label, 0, 5)
        top_controls.setColumnStretch(5, 1)

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
        layout.addWidget(self.help_label)
        layout.addLayout(top_controls)
        layout.addWidget(splitter, 1)

    def set_result(self, result: dict | None) -> None:
        self.result = result
        self.all_rows = validation_preview_rows(result)
        self._apply_filters()

    def selected_row(self) -> dict | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row_idx = selected[0].row()
        if row_idx < 0 or row_idx >= len(self.rows):
            return None
        return self.rows[row_idx]

    def _apply_filters(self) -> None:
        rows = list(self.all_rows)
        if self.bad_only_checkbox.isChecked():
            threshold = float(self.error_threshold_spin.value())
            rows = [row for row in rows if float(row.get('combined_error', 0.0) or 0.0) >= threshold]
        order = self.sort_combo.currentText()
        if order == 'Worst first':
            rows.sort(key=lambda row: float(row.get('combined_error', 0.0) or 0.0), reverse=True)
        elif order == 'Best first':
            rows.sort(key=lambda row: float(row.get('combined_error', 0.0) or 0.0))
        self.rows = rows
        self._populate_table()
        self.count_label.setText(f'{len(self.rows)} frame(s)')
        self._refresh_preview()

    def _populate_table(self) -> None:
        columns = [
            'row_number', 'session', 'frame_id', 'frame_number', 'mode',
            'target_steering', 'pred_steering', 'target_speed', 'pred_speed', 'combined_error',
        ]
        headers = ['Row', 'Session', 'Frame ID', 'Frame No.', 'Mode', 'Target Str', 'Pred Str', 'Target Spd', 'Pred Spd', 'Error']
        self.table.clear()
        self.table.setRowCount(len(self.rows))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(headers)
        for row_idx, row in enumerate(self.rows):
            for col_idx, col in enumerate(columns):
                value = row.get(col, '')
                if isinstance(value, float):
                    text = f'{value:.3f}'
                else:
                    text = str(value)
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(text))
        if self.rows:
            self.table.selectRow(0)
        else:
            self.image_label.clear()
            self.image_label.setText('No validation frame selected.')
            self.meta_label.setText('Run validation to populate frame overlays or loosen the bad-frame filter.')

    def _select_best(self) -> None:
        if not self.rows:
            return
        best_index = min(range(len(self.rows)), key=lambda index: float(self.rows[index].get('combined_error', 0.0) or 0.0))
        self.table.selectRow(best_index)
        self._refresh_preview()

    def _select_worst(self) -> None:
        if not self.rows:
            return
        worst_index = max(range(len(self.rows)), key=lambda index: float(self.rows[index].get('combined_error', 0.0) or 0.0))
        self.table.selectRow(worst_index)
        self._refresh_preview()

    def _edit_current_frame(self) -> None:
        row = self.selected_row()
        if row and self.edit_in_data_callback is not None:
            self.edit_in_data_callback(dict(row))

    def _refresh_preview(self) -> None:
        row = self.selected_row()
        if row is None:
            self.image_label.clear()
            self.image_label.setText('Select a validation row to preview it.')
            self.meta_label.setText('')
            return
        pixmap = load_scaled_pixmap(str(row.get('abs_image', '')), 620, 420)
        if pixmap is None:
            self.image_label.clear()
            self.image_label.setText('Image not available')
        else:
            rendered = apply_prediction_comparison_overlay(
                pixmap,
                steering_true=float(row.get('target_steering', 0.0) or 0.0),
                speed_true=float(row.get('target_speed', 0.0) or 0.0),
                steering_pred=float(row.get('pred_steering', 0.0) or 0.0),
                speed_pred=float(row.get('pred_speed', 0.0) or 0.0),
            )
            self.image_label.setText('')
            self.image_label.setPixmap(rendered)
        self.meta_label.setText(
            (
                'Row {row_number} | Session: {session} | Mode: {mode} | Frame ID: {frame_id} | Frame No.: {frame_number}\n'
                'Target Steer/Speed: {target_steering:.3f} / {target_speed:.3f} | '
                'Pred Steer/Speed: {pred_steering:.3f} / {pred_speed:.3f} | '
                'Combined error: {combined_error:.4f}'
            ).format(
                row_number=int(row.get('row_number', 0) or 0),
                session=str(row.get('session', '')),
                mode=str(row.get('mode', '')),
                frame_id=str(row.get('frame_id', '')),
                frame_number=str(row.get('frame_number', '')),
                target_steering=float(row.get('target_steering', 0.0) or 0.0),
                target_speed=float(row.get('target_speed', 0.0) or 0.0),
                pred_steering=float(row.get('pred_steering', 0.0) or 0.0),
                pred_speed=float(row.get('pred_speed', 0.0) or 0.0),
                combined_error=float(row.get('combined_error', 0.0) or 0.0),
            )
        )
