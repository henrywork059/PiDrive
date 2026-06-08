from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QFontMetricsF, QPainter, QPen, QPixmap

from ...ui.theme import theme_color
from .overlay_primitives import (
    _draw_drive_arrow,
    _draw_legacy_path_preview,
    _draw_speed_bar,
    _draw_steering_arc,
    _draw_steering_bar,
    _overlay_text_color,
    _overlay_text_size_factor,
    _scaled_overlay_font,
)
from .overlay_road import _draw_path_preview, _draw_pisd_road_guide
from .overlay_values import (
    _overlay_dict,
    _to_float,
    clip_speed,
    clip_steering,
    drive_arrow_points,
    drive_values_from_point,
)


__all__ = [
    'apply_overlays',
    'apply_prediction_comparison_overlay',
    'clip_speed',
    'clip_steering',
    'drive_arrow_points',
    'drive_values_from_point',
]


def apply_overlays(pixmap: QPixmap, record: dict[str, Any] | None, options: dict[str, bool]) -> QPixmap:
    if pixmap.isNull() or not record:
        return pixmap

    rendered = QPixmap(pixmap)
    painter = QPainter(rendered)
    painter.setRenderHint(QPainter.Antialiasing, True)

    throttle_value = _to_float(record.get('throttle', 0.0), 0.0)
    steering_value = _to_float(record.get('steering', 0.0), 0.0)

    show_middle_label = not (options.get('speed_vertical') or options.get('steering_arc'))
    if options.get('path_preview'):
        _draw_path_preview(painter, rendered, record, steering_value, throttle_value, show_label=show_middle_label)
    if options.get('legacy_path_preview'):
        _draw_legacy_path_preview(painter, rendered, steering_value, throttle_value)
    if options.get('drive_arrow'):
        _draw_drive_arrow(painter, rendered, steering_value, throttle_value)
    if options.get('speed_vertical'):
        _draw_speed_bar(painter, rendered, throttle_value)
    if options.get('steering_horizontal'):
        _draw_steering_bar(painter, rendered, steering_value)
    if options.get('steering_arc'):
        _draw_steering_arc(painter, rendered, steering_value)

    painter.end()
    return rendered


def apply_prediction_comparison_overlay(
    pixmap: QPixmap,
    steering_true: float,
    speed_true: float,
    steering_pred: float,
    speed_pred: float,
    overlay_settings: dict[str, Any] | None = None,
    *,
    legend_text_color: QColor | None = None,
    legend_font_scale: float = 1.0,
) -> QPixmap:
    if pixmap.isNull():
        return pixmap

    rendered = QPixmap(pixmap)
    painter = QPainter(rendered)
    painter.setRenderHint(QPainter.Antialiasing, True)
    settings = _overlay_dict(overlay_settings)

    _draw_pisd_road_guide(
        painter,
        rendered,
        steering_true,
        speed_true,
        settings,
        color=QColor(74, 208, 120, 235),
        comparison=True,
    )
    _draw_pisd_road_guide(
        painter,
        rendered,
        steering_pred,
        speed_pred,
        settings,
        color=QColor(255, 164, 76, 235),
        comparison=True,
    )

    text_color = _overlay_text_color(legend_text_color or QColor(theme_color('text_primary')))
    text_scale = legend_font_scale if legend_font_scale > 0 else 1.0
    reference_size = float(min(rendered.width(), rendered.height()))
    size_factor = _overlay_text_size_factor(reference_size)

    painter.save()
    painter.setFont(_scaled_overlay_font(painter, text_scale, reference_size=reference_size))
    metrics = QFontMetricsF(painter.font())
    row_height = max(20.0 * size_factor, metrics.height() + 4.0 * size_factor)
    swatch_left = 12.0 * size_factor
    swatch_width = 22.0 * size_factor
    text_left = 40.0 * size_factor
    legend_width = min(max(220.0 * size_factor, text_left + metrics.horizontalAdvance('Target path') + 18.0 * size_factor), rendered.width() * 0.58)
    legend_height = row_height * 2.0 + 14.0 * size_factor
    legend_rect = QRectF(16.0 * size_factor, 10.0 * size_factor, legend_width, legend_height)

    painter.setPen(QPen(QColor(255, 255, 255, 70), max(1.0, size_factor)))
    painter.setBrush(QBrush(QColor(18, 22, 31, 165)))
    painter.drawRoundedRect(legend_rect, 8.0 * size_factor, 8.0 * size_factor)

    first_center_y = legend_rect.top() + 7.0 * size_factor + row_height / 2.0
    second_center_y = first_center_y + row_height
    painter.setPen(QPen(QColor(74, 208, 120, 235), max(2.0, 3.0 * size_factor)))
    painter.drawLine(QPointF(legend_rect.left() + swatch_left, first_center_y), QPointF(legend_rect.left() + swatch_left + swatch_width, first_center_y))
    painter.setPen(text_color)
    painter.drawText(QRectF(legend_rect.left() + text_left, legend_rect.top() + 5.0 * size_factor, legend_rect.width() - text_left - 6.0 * size_factor, row_height), Qt.AlignLeft | Qt.AlignVCenter, 'Target path')

    painter.setPen(QPen(QColor(255, 164, 76, 235), max(2.0, 3.0 * size_factor)))
    painter.drawLine(QPointF(legend_rect.left() + swatch_left, second_center_y), QPointF(legend_rect.left() + swatch_left + swatch_width, second_center_y))
    painter.setPen(text_color)
    painter.drawText(QRectF(legend_rect.left() + text_left, legend_rect.top() + 5.0 * size_factor + row_height, legend_rect.width() - text_left - 6.0 * size_factor, row_height), Qt.AlignLeft | Qt.AlignVCenter, 'AI path')
    painter.restore()

    painter.end()
    return rendered
