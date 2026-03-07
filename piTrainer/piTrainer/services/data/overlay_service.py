from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPixmap


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip_unit(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _draw_label(painter: QPainter, rect: QRectF, text: str) -> None:
    painter.save()
    painter.setPen(QColor('#f7fbff'))
    painter.drawText(rect, Qt.AlignCenter, text)
    painter.restore()


def _draw_track(painter: QPainter, rect: QRectF) -> None:
    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 120), 2))
    painter.setBrush(QBrush(QColor(18, 22, 31, 150)))
    painter.drawRoundedRect(rect, 8, 8)
    painter.restore()


def _draw_speed_bar(painter: QPainter, pixmap: QPixmap, throttle_value: float) -> None:
    width = pixmap.width()
    height = pixmap.height()
    track = QRectF(width - 48, height * 0.12, 24, height * 0.68)
    label_rect = QRectF(width - 92, height * 0.82, 70, 24)

    _draw_track(painter, track)

    value = max(0.0, min(1.0, throttle_value))
    fill_h = (track.height() - 8.0) * value
    fill_rect = QRectF(track.left() + 4, track.bottom() - 4 - fill_h, track.width() - 8, fill_h)

    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(74, 208, 120, 220))
    painter.drawRoundedRect(fill_rect, 6, 6)
    painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
    painter.drawLine(track.left() - 4, track.bottom(), track.right() + 4, track.bottom())
    painter.restore()

    _draw_label(painter, label_rect, f"SPD {throttle_value:.2f}")


def _draw_steering_bar(painter: QPainter, pixmap: QPixmap, steering_value: float) -> None:
    width = pixmap.width()
    height = pixmap.height()
    track = QRectF(width * 0.20, height - 44, width * 0.44, 20)
    center_x = track.center().x()
    half_width = (track.width() - 8.0) / 2.0
    value = _clip_unit(steering_value)
    fill_width = half_width * abs(value)

    _draw_track(painter, track)

    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
    painter.drawLine(QPointF(center_x, track.top() - 4), QPointF(center_x, track.bottom() + 4))
    if fill_width > 0:
        left = center_x if value >= 0 else center_x - fill_width
        fill_rect = QRectF(left, track.top() + 4, fill_width, track.height() - 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(86, 167, 255, 220))
        painter.drawRoundedRect(fill_rect, 6, 6)
    painter.restore()

    _draw_label(painter, QRectF(track.right() + 8, track.top() - 2, 92, 24), f"STR {steering_value:.2f}")


def _draw_steering_arc(painter: QPainter, pixmap: QPixmap, steering_value: float) -> None:
    width = pixmap.width()
    height = pixmap.height()
    size = min(width, height) * 0.25
    rect = QRectF(22, height - size - 28, size, size)
    value = _clip_unit(steering_value)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor(255, 255, 255, 120), 6))
    painter.drawArc(rect, 0, 180 * 16)

    span_angle = int(180 * value * 16)
    painter.setPen(QPen(QColor(255, 188, 88, 230), 8))
    if span_angle >= 0:
        painter.drawArc(rect, 90 * 16, -span_angle)
    else:
        painter.drawArc(rect, 90 * 16, -span_angle)

    center = rect.center()
    radius = rect.width() / 2.0
    painter.setPen(QPen(QColor(255, 255, 255, 160), 2))
    painter.drawLine(QPointF(center.x(), center.y()), QPointF(center.x(), rect.top()))
    end_angle_deg = 90.0 - 90.0 * value
    from math import cos, radians, sin
    end_x = center.x() + radius * cos(radians(end_angle_deg))
    end_y = center.y() - radius * sin(radians(end_angle_deg))
    painter.setPen(QPen(QColor(255, 188, 88, 230), 3))
    painter.drawLine(QPointF(center.x(), center.y()), QPointF(end_x, end_y))
    painter.restore()

    _draw_label(painter, QRectF(rect.left() - 8, rect.bottom() - 4, rect.width() + 16, 24), f"STR ARC {steering_value:.2f}")


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

    painter.end()
    return rendered
