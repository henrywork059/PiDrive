from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QLabel,
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
    def __init__(self) -> None:
        super().__init__('Validation Frame Review')
        self.result: dict | None = None
        self.rows: list[dict] = []

        self.help_label = QLabel(
            'Browse validated frames and compare the target/trained path against the predicted path directly on the image.'
        )
        self.help_label.setWordWrap(True)
        self.help_label.setProperty('role', 'muted')

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

        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.addWidget(self.image_label, 1)
        preview_layout.addWidget(self.meta_label)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(self.help_label)
        layout.addWidget(splitter, 1)

    def set_result(self, result: dict | None) -> None:
        self.result = result
        self.rows = validation_preview_rows(result)
        columns = [
            'row_number',
            'session',
            'frame_id',
            'frame_number',
            'target_steering',
            'pred_steering',
            'target_speed',
            'pred_speed',
            'combined_error',
        ]
        headers = ['Row', 'Session', 'Frame ID', 'Frame No.', 'Target Str', 'Pred Str', 'Target Spd', 'Pred Spd', 'Error']
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
            self.meta_label.setText('Run validation to populate frame overlays.')

    def _refresh_preview(self) -> None:
        if not self.result or not self.rows:
            self.image_label.clear()
            self.image_label.setText('No validation frame selected.')
            self.meta_label.setText('Run validation to populate frame overlays.')
            return
        selected = self.table.selectedItems()
        if not selected:
            self.image_label.clear()
            self.image_label.setText('Select a validation row to preview it.')
            self.meta_label.setText('')
            return
        row_idx = selected[0].row()
        if row_idx < 0 or row_idx >= len(self.rows):
            return
        row = self.rows[row_idx]
        abs_images = list(self.result.get('abs_images', []))
        image_path = abs_images[row_idx] if row_idx < len(abs_images) else ''
        pixmap = load_scaled_pixmap(str(image_path), 620, 420)
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
                'Row {row_number} | Session: {session} | Frame ID: {frame_id} | Frame No.: {frame_number}\n'
                'Target Steer/Speed: {target_steering:.3f} / {target_speed:.3f} | '
                'Pred Steer/Speed: {pred_steering:.3f} / {pred_speed:.3f} | '
                'Combined error: {combined_error:.4f}'
            ).format(
                row_number=int(row.get('row_number', 0) or 0),
                session=str(row.get('session', '')),
                frame_id=str(row.get('frame_id', '')),
                frame_number=str(row.get('frame_number', '')),
                target_steering=float(row.get('target_steering', 0.0) or 0.0),
                target_speed=float(row.get('target_speed', 0.0) or 0.0),
                pred_steering=float(row.get('pred_steering', 0.0) or 0.0),
                pred_speed=float(row.get('pred_speed', 0.0) or 0.0),
                combined_error=float(row.get('combined_error', 0.0) or 0.0),
            )
        )
