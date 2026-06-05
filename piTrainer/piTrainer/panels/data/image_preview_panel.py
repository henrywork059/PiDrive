from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QPoint, QTimer, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from ...services.data.augmentation_service import truthy_value
from ...services.data.overlay_service import apply_overlays, clip_speed, clip_steering, drive_values_from_point
from ...utils.image_utils import load_scaled_pixmap
from ...ui.layout_widgets import CollapsibleSection
from ...ui.sliders import CenteredFillSlider


class InteractiveImageLabel(QLabel):
    def __init__(self, parent_panel) -> None:
        super().__init__('No preview')
        self.parent_panel = parent_panel
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(220)
        self.setWordWrap(True)
        self.setFocusPolicy(Qt.ClickFocus)
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
            self.setFocus(Qt.MouseFocusReason)
            self._handle_event_position(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton:
            self._handle_event_position(event.position().toPoint())
        super().mouseMoveEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        if hasattr(self.parent_panel, '_schedule_render_preview'):
            self.parent_panel._schedule_render_preview()


class ImagePreviewPanel(QGroupBox):
    def __init__(self, record_edited_callback=None, navigate_record_callback=None) -> None:
        super().__init__('Image Preview')
        self.record_edited_callback = record_edited_callback
        self.navigate_record_callback = navigate_record_callback
        self.current_record: dict[str, Any] | None = None
        self.overlay_options: dict[str, bool] = {
            'path_preview': True,
            'legacy_path_preview': False,
            'speed_vertical': False,
            'steering_horizontal': False,
            'steering_arc': False,
            'drive_arrow': False,
        }
        self._syncing_controls = False
        self._pending_edit_records: dict[tuple[str, str, str, str], dict[str, Any]] = {}

        self.image_label = InteractiveImageLabel(self)

        hint_label = QLabel(
            'Select a row on the left, then review the image and PiSD V7 overlay here. Click or drag only when you want to correct steering/speed. '
            'PiSD V7 overlay metadata is used for road-guide redraw when available. Use the sliders below for precise adjustment.'
        )
        hint_label.setProperty('role', 'muted')
        hint_label.setWordWrap(True)

        self.steering_value_label = QLabel('0.000')
        self.speed_value_label = QLabel('0.000')
        self.overlay_meta_label = QLabel('Overlay metadata: none')
        self.overlay_meta_label.setProperty('role', 'muted')
        self.overlay_meta_label.setWordWrap(True)

        self.steering_slider = CenteredFillSlider(Qt.Horizontal, center_value=0)
        self.steering_slider.setRange(-1000, 1000)
        self.steering_slider.valueChanged.connect(self._on_slider_changed)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 1000)
        self.speed_slider.valueChanged.connect(self._on_slider_changed)

        for widget in (self.image_label, self.steering_slider, self.speed_slider):
            widget.installEventFilter(self)

        steering_row = QHBoxLayout()
        steering_row.addWidget(QLabel('Steering'))
        steering_row.addWidget(self.steering_slider, 1)
        steering_row.addWidget(self.steering_value_label)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel('Speed'))
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_value_label)

        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(hint_label)
        editor_layout.addLayout(steering_row)
        editor_layout.addLayout(speed_row)
        editor_layout.addWidget(self.overlay_meta_label)

        self.commit_timer = QTimer(self)
        self.commit_timer.setSingleShot(True)
        # Debounce edits so click/drag adjustments do not rewrite JSONL files repeatedly,
        # but keep selection changes responsive by committing queued edits after the UI moves on.
        self.commit_timer.setInterval(450)
        self.commit_timer.timeout.connect(self._emit_pending_record_edits)

        self.resize_render_timer = QTimer(self)
        self.resize_render_timer.setSingleShot(True)
        self.resize_render_timer.setInterval(120)
        self.resize_render_timer.timeout.connect(self._render_preview)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label, 1)
        layout.addWidget(CollapsibleSection('Edit Steering / Speed + Overlay Metadata', editor_widget, expanded=False))

        self._set_slider_enabled(False)
        self._update_value_labels(0.0, 0.0)
        self._update_overlay_meta_label({})

    @staticmethod
    def _key_press_event_type():
        direct = getattr(QEvent, 'KeyPress', None)
        if direct is not None:
            return direct
        event_type = getattr(QEvent, 'Type', None)
        return getattr(event_type, 'KeyPress', None) if event_type is not None else None

    def set_record_navigation_callback(self, callback) -> None:
        self.navigate_record_callback = callback

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API name
        key_press_type = self._key_press_event_type()
        if key_press_type is not None and event.type() == key_press_type and isinstance(event, QKeyEvent):
            if self._handle_navigation_key(event):
                return True
        return super().eventFilter(watched, event)

    def _handle_navigation_key(self, event: QKeyEvent) -> bool:
        key = event.key()
        if key not in (Qt.Key_Down, Qt.Key_Up):
            return False
        if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier):
            return False
        if self.navigate_record_callback is None:
            return False
        step = 1 if key == Qt.Key_Down else -1
        if not self.navigate_record_callback(step):
            return False
        event.accept()
        return True

    def set_record(self, record: dict[str, Any] | None) -> None:
        # Do not synchronously write pending edits when the user clicks another row.
        # The debounce timer commits queued edits shortly after selection changes,
        # which keeps frame-to-frame review responsive on large JSONL sessions.
        self.current_record = dict(record) if record else None
        self._sync_controls_from_record()
        self._render_preview()

    def set_overlay_options(self, options: dict[str, bool]) -> None:
        self.overlay_options = {
            'path_preview': bool(options.get('path_preview', True)),
            'legacy_path_preview': bool(options.get('legacy_path_preview', False)),
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
        self.current_record = None
        self.image_label.set_display_pixmap(None)
        self.image_label.setText('No preview')
        self._set_slider_enabled(False)
        self._syncing_controls = True
        self.steering_slider.setValue(0)
        self.speed_slider.setValue(0)
        self._syncing_controls = False
        self._update_value_labels(0.0, 0.0)
        self._update_overlay_meta_label({})

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
        self._update_overlay_meta_label(record)

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
        self._queue_pending_edit(self.current_record)

    def _update_value_labels(self, steering: float, speed: float) -> None:
        self.steering_value_label.setText(f'{steering:.3f}')
        self.speed_value_label.setText(f'{speed:.3f}')

    def _update_overlay_meta_label(self, record: dict[str, Any]) -> None:
        settings = record.get('overlay_settings') if isinstance(record, dict) else {}
        has_settings = bool(settings) if isinstance(settings, dict) else False
        schema = str(record.get('overlay_schema_version', '') if isinstance(record, dict) else '').strip()
        source = str(record.get('overlay_settings_source', '') if isinstance(record, dict) else '').strip()
        if has_settings:
            count = len(settings)
            suffix = f' | {source}' if source else ''
            self.overlay_meta_label.setText(f'Overlay metadata: PiSD road settings loaded ({count} value(s)) | {schema or "no schema"}{suffix}')
        else:
            self.overlay_meta_label.setText('Overlay metadata: using PiSD V7 defaults')

    def _schedule_render_preview(self) -> None:
        if self.current_record is not None:
            self.resize_render_timer.start()

    def _preview_size(self) -> tuple[int, int]:
        width = max(260, self.image_label.width() - 14)
        height = max(180, self.image_label.height() - 14)
        return width, height

    def _render_preview(self) -> None:
        record = self.current_record or {}
        image_path = str(record.get('abs_image', ''))
        target_width, target_height = self._preview_size()
        flip_lr = truthy_value(record.get('aug_flip_lr', False), default=False)
        pixmap = load_scaled_pixmap(image_path, width=target_width, height=target_height, flip_lr=flip_lr)
        if pixmap is None:
            self.image_label.set_display_pixmap(None)
            self.image_label.setText('Image not available')
            return

        rendered = apply_overlays(pixmap, record, self.overlay_options)
        self.image_label.setText('')
        self.image_label.set_display_pixmap(rendered)

    @staticmethod
    def _record_edit_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            str(record.get('session', '') or ''),
            str(record.get('frame_id', '') or ''),
            str(record.get('abs_image', '') or record.get('image_path', '') or record.get('frame', '') or ''),
            str(record.get('ts', '') or ''),
        )

    def _queue_pending_edit(self, record: dict[str, Any]) -> None:
        key = self._record_edit_key(record)
        if not any(key):
            return
        self._pending_edit_records[key] = dict(record)
        self.commit_timer.start()

    def _emit_pending_record_edits(self) -> None:
        if self.record_edited_callback is None or not self._pending_edit_records:
            return
        pending = [dict(record) for record in self._pending_edit_records.values()]
        self._pending_edit_records.clear()
        if len(pending) == 1:
            self.record_edited_callback(pending[0])
        else:
            self.record_edited_callback(pending)

    def _flush_pending_commit(self) -> None:
        if self.commit_timer.isActive():
            self.commit_timer.stop()
        self._emit_pending_record_edits()
