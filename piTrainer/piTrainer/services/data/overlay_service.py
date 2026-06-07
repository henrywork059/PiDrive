from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPixmap

from ...ui.theme import theme_color
from .overlay_primitives import (
    _draw_drive_arrow,
    _draw_legacy_path_preview,
    _draw_speed_bar,
    _draw_steering_arc,
    _draw_steering_bar,
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

    if options.get('speed_vertical'):
        _draw_speed_bar(painter, rendered, throttle_value)
    if options.get('steering_horizontal'):
        _draw_steering_bar(painter, rendered, steering_value)
    if options.get('steering_arc'):
        _draw_steering_arc(painter, rendered, steering_value)
    if options.get('path_preview'):
        _draw_path_preview(painter, rendered, record, steering_value, throttle_value)
    if options.get('legacy_path_preview'):
        _draw_legacy_path_preview(painter, rendered, steering_value, throttle_value)
    if options.get('drive_arrow'):
        _draw_drive_arrow(painter, rendered, steering_value, throttle_value)

    painter.end()
    return rendered


def apply_prediction_comparison_overlay(
    pixmap: QPixmap,
    steering_true: float,
    speed_true: float,
    steering_pred: float,
    speed_pred: float,
    overlay_settings: dict[str, Any] | None = None,
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

    legend_rect = QRectF(16, 10, min(280.0, rendered.width() * 0.50), 48)
    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
    painter.setBrush(QBrush(QColor(18, 22, 31, 165)))
    painter.drawRoundedRect(legend_rect, 8, 8)
    painter.setPen(QPen(QColor(74, 208, 120, 235), 3))
    painter.drawLine(QPointF(legend_rect.left() + 12, legend_rect.top() + 15), QPointF(legend_rect.left() + 34, legend_rect.top() + 15))
    painter.setPen(QColor(theme_color('text_primary')))
    painter.drawText(QRectF(legend_rect.left() + 40, legend_rect.top() + 4, legend_rect.width() - 45, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Target PiSD road guide')
    painter.setPen(QPen(QColor(255, 164, 76, 235), 3))
    painter.drawLine(QPointF(legend_rect.left() + 12, legend_rect.top() + 32), QPointF(legend_rect.left() + 34, legend_rect.top() + 32))
    painter.setPen(QColor(theme_color('text_primary')))
    painter.drawText(QRectF(legend_rect.left() + 40, legend_rect.top() + 21, legend_rect.width() - 45, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Predicted PiSD road guide')
    painter.restore()

    painter.end()
    return rendered
