from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from ...services.data.overlay_service import apply_prediction_comparison_overlay
from ...utils.image_utils import load_scaled_pixmap


class _FrameReviewCard(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)
        self.image = QLabel('No frame yet')
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMinimumHeight(180)
        self.image.setWordWrap(True)
        self.meta = QLabel('')
        self.meta.setWordWrap(True)
        self.meta.setProperty('role', 'muted')
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.image)
        layout.addWidget(self.meta)

    def set_payload(self, payload: dict | None) -> None:
        if not payload:
            self.image.clear()
            self.image.setText('No frame yet')
            self.meta.setText('')
            return

        pixmap = load_scaled_pixmap(str(payload.get('abs_image', '')), 300, 200)
        if pixmap is not None:
            rendered = apply_prediction_comparison_overlay(
                pixmap,
                steering_true=float(payload.get('steering_true', 0.0) or 0.0),
                speed_true=float(payload.get('throttle_true', 0.0) or 0.0),
                steering_pred=float(payload.get('steering_pred', 0.0) or 0.0),
                speed_pred=float(payload.get('throttle_pred', 0.0) or 0.0),
            )
            self.image.setText('')
            self.image.setPixmap(rendered)
        else:
            self.image.clear()
            self.image.setText('Image not available')

        frame_id = str(payload.get('frame_id', '')).strip() or '(none)'
        frame_number = str(payload.get('frame_number', '')).strip() or '(none)'
        review_frame = int(payload.get('review_frame_number', 0) or 0)
        review_total = int(payload.get('review_total', 0) or 0)
        self.meta.setText(
            (
                'Session: {session}\n'
                'Frame ID: {frame_id}\n'
                'Frame No.: {frame_number}\n'
                'Review frame: {review_frame}/{review_total}\n'
                'Combined error: {combined_error:.4f}\n'
                'Target Steer/Speed: {steering_true:.3f} / {throttle_true:.3f}\n'
                'Pred Steer/Speed: {steering_pred:.3f} / {throttle_pred:.3f}'
            ).format(
                session=str(payload.get('session', '')),
                frame_id=frame_id,
                frame_number=frame_number,
                review_frame=review_frame,
                review_total=review_total,
                combined_error=float(payload.get('combined_error', 0.0) or 0.0),
                steering_true=float(payload.get('steering_true', 0.0) or 0.0),
                steering_pred=float(payload.get('steering_pred', 0.0) or 0.0),
                throttle_true=float(payload.get('throttle_true', 0.0) or 0.0),
                throttle_pred=float(payload.get('throttle_pred', 0.0) or 0.0),
            )
        )


class TrainEpochReviewPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Epoch Frame Review')
        self.epoch_label = QLabel('Best and worst-fit frames will appear during training.')
        self.epoch_label.setWordWrap(True)
        self.best_card = _FrameReviewCard('Best-fit frame')
        self.worst_card = _FrameReviewCard('Worst-fit frame')
        grid = QGridLayout()
        grid.addWidget(self.best_card, 0, 0)
        grid.addWidget(self.worst_card, 0, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.epoch_label)
        layout.addLayout(grid)

    def clear_review(self) -> None:
        self.epoch_label.setText('Best and worst-fit frames will appear during training.')
        self.best_card.set_payload(None)
        self.worst_card.set_payload(None)

    def set_review(self, payload: dict | None) -> None:
        if not payload:
            self.clear_review()
            return
        self.epoch_label.setText(
            'Epoch {epoch}: current best-fit and worst-fit frames with target vs predicted paths.'.format(
                epoch=int(payload.get('epoch', 0) or 0)
            )
        )
        self.best_card.set_payload(payload.get('best'))
        self.worst_card.set_payload(payload.get('worst'))
