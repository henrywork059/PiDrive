from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout

from ...services.data.overlay_service import apply_overlays, clip_speed, clip_steering, drive_values_from_point
from ...utils.image_utils import load_scaled_pixmap


class InteractiveImageLabel(QLabel):
    def __init__(self, parent_panel) -> None:
        super().__init__('No preview')
        self.parent_panel = parent_panel
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(320)
        self.setWordWrap(True)
        self._pixmap: QPixmap | None = None

    def set_display_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        if pixmap is None:
            self.setPixmap(QPixmap())
            return
        self.setPixmap(pixmap)

    def _pixmap_rect(self):
        pixmap = self._pixmap
        if pixmap is None or pixmap.isNull():
            return None
        x = max(0, int((self.width() - pixmap.width()) / 2))
        y = max(0, int((self.height() - pixmap.height()) / 2))
        return x, y, pixmap.width(), pixmap.height()

    def _handle_event_position(self, pos: QPoint) -> None:
        rect = self._pixmap_rect()
        if rect is None:
            return
        left, top, width, height = rect
        x = pos.x() - left
        y = pos.y() - top
        if x < 0 or y < 0 or x > width or y > height:
            return
        steering, speed = drive_values_from_point(float(x), float(y), float(width), float(height))
        self.parent_panel.set_controls_from_preview(steering, speed)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._handle_event_position(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton:
            self._handle_event_position(event.position().toPoint())
        super().mouseMoveEvent(event)


class ImagePreviewPanel(QGroupBox):
    def __init__(self, record_edited_callback=None) -> None:
        super().__init__('Image Preview')
        self.record_edited_callback = record_edited_callback
        self.current_record: dict[str, Any] | None = None
        self.overlay_options: dict[str, bool] = {
            'speed_vertical': False,
            'steering_horizontal': False,
            'steering_arc': False,
            'drive_arrow': False,
        }
        self._syncing_controls = False

        self.image_label = InteractiveImageLabel(self)

        hint_label = QLabel(
            'Click or drag on the preview to edit steering/speed using the same logic as the drive arrow. '
            'Use the sliders below for precise adjustment.'
        )
        hint_label.setProperty('role', 'muted')
        hint_label.setWordWrap(True)

        self.steering_value_label = QLabel('0.000')
        self.speed_value_label = QLabel('0.000')

        self.steering_slider = QSlider(Qt.Horizontal)
        self.steering_slider.setRange(-1000, 1000)
        self.steering_slider.valueChanged.connect(self._on_slider_changed)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 1000)
        self.speed_slider.valueChanged.connect(self._on_slider_changed)

        steering_row = QHBoxLayout()
        steering_row.addWidget(QLabel('Steering'))
        steering_row.addWidget(self.steering_slider, 1)
        steering_row.addWidget(self.steering_value_label)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel('Speed'))
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_value_label)

        self.commit_timer = QTimer(self)
        self.commit_timer.setSingleShot(True)
        self.commit_timer.setInterval(250)
        self.commit_timer.timeout.connect(self._emit_record_edited)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(hint_label)
        layout.addLayout(steering_row)
        layout.addLayout(speed_row)

        self._set_slider_enabled(False)
        self._update_value_labels(0.0, 0.0)

    def set_record(self, record: dict[str, Any] | None) -> None:
        self._flush_pending_commit()
        self.current_record = dict(record) if record else None
        self._sync_controls_from_record()
        self._render_preview()

    def set_overlay_options(self, options: dict[str, bool]) -> None:
        self.overlay_options = {
            'speed_vertical': bool(options.get('speed_vertical', False)),
            'steering_horizontal': bool(options.get('steering_horizontal', False)),
            'steering_arc': bool(options.get('steering_arc', False)),
            'drive_arrow': bool(options.get('drive_arrow', False)),
        }
        self._render_preview()

    def set_controls_from_preview(self, steering: float, speed: float) -> None:
        if self.current_record is None:
            return
        self._syncing_controls = True
        self.steering_slider.setValue(int(round(clip_steering(steering) * 1000.0)))
        self.speed_slider.setValue(int(round(clip_speed(speed) * 1000.0)))
        self._syncing_controls = False
        self._apply_current_control_values()

    def clear_preview(self) -> None:
        self._flush_pending_commit()
        self.current_record = None
        self.image_label.set_display_pixmap(None)
        self.image_label.setText('No preview')
        self._set_slider_enabled(False)
        self._syncing_controls = True
        self.steering_slider.setValue(0)
        self.speed_slider.setValue(0)
        self._syncing_controls = False
        self._update_value_labels(0.0, 0.0)

    def _set_slider_enabled(self, enabled: bool) -> None:
        self.steering_slider.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)

    def _sync_controls_from_record(self) -> None:
        record = self.current_record or {}
        steering = clip_steering(float(record.get('steering', 0.0) or 0.0))
        speed = clip_speed(float(record.get('throttle', 0.0) or 0.0))
        self._syncing_controls = True
        self.steering_slider.setValue(int(round(steering * 1000.0)))
        self.speed_slider.setValue(int(round(speed * 1000.0)))
        self._syncing_controls = False
        self._set_slider_enabled(self.current_record is not None)
        self._update_value_labels(steering, speed)

    def _on_slider_changed(self) -> None:
        if self._syncing_controls:
            return
        self._apply_current_control_values()

    def _apply_current_control_values(self) -> None:
        if self.current_record is None:
            return
        steering = clip_steering(self.steering_slider.value() / 1000.0)
        speed = clip_speed(self.speed_slider.value() / 1000.0)
        self.current_record['steering'] = steering
        self.current_record['throttle'] = speed
        self._update_value_labels(steering, speed)
        self._render_preview()
        self.commit_timer.start()

    def _update_value_labels(self, steering: float, speed: float) -> None:
        self.steering_value_label.setText(f'{steering:.3f}')
        self.speed_value_label.setText(f'{speed:.3f}')

    def _render_preview(self) -> None:
        record = self.current_record or {}
        image_path = str(record.get('abs_image', ''))
        pixmap = load_scaled_pixmap(image_path, width=560, height=420)
        if pixmap is None:
            self.image_label.set_display_pixmap(None)
            self.image_label.setText('Image not available')
            return

        rendered = apply_overlays(pixmap, record, self.overlay_options)
        self.image_label.setText('')
        self.image_label.set_display_pixmap(rendered)

    def _emit_record_edited(self) -> None:
        if self.current_record is not None and self.record_edited_callback is not None:
            self.record_edited_callback(dict(self.current_record))

    def _flush_pending_commit(self) -> None:
        if self.commit_timer.isActive():
            self.commit_timer.stop()
            self._emit_record_edited()
