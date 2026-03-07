from __future__ import annotations

from math import cos, radians, sin
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPixmap


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clip_steering(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def clip_speed(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def drive_arrow_points(width: float, height: float, steering_value: float, speed_value: float) -> tuple[QPointF, QPointF]:
    margin_x = max(18.0, width * 0.06)
    margin_top = max(18.0, height * 0.08)
    margin_bottom = max(22.0, height * 0.08)

    start = QPointF(width / 2.0, height - margin_bottom)
    steering = clip_steering(steering_value)
    speed = clip_speed(speed_value)
    half_span_x = max(20.0, (width / 2.0) - margin_x)
    span_y = max(20.0, height - margin_top - margin_bottom)

    end_x = start.x() + steering * half_span_x
    end_y = start.y() - speed * span_y
    return start, QPointF(end_x, end_y)


def drive_values_from_point(x: float, y: float, width: float, height: float) -> tuple[float, float]:
    margin_x = max(18.0, width * 0.06)
    margin_top = max(18.0, height * 0.08)
    margin_bottom = max(22.0, height * 0.08)
    start_x = width / 2.0
    start_y = height - margin_bottom
    half_span_x = max(20.0, (width / 2.0) - margin_x)
    span_y = max(20.0, height - margin_top - margin_bottom)

    steering = clip_steering((float(x) - start_x) / half_span_x)
    speed = clip_speed((start_y - float(y)) / span_y)
    return steering, speed


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

    value = clip_speed(throttle_value)
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


def _steering_fill_color(value: float) -> QColor:
    if value < 0:
        return QColor(255, 184, 88, 225)
    return QColor(86, 167, 255, 225)


def _draw_steering_bar(painter: QPainter, pixmap: QPixmap, steering_value: float) -> None:
    width = pixmap.width()
    height = pixmap.height()
    track = QRectF(width * 0.20, height - 44, width * 0.44, 20)
    inner = QRectF(track.left() + 4, track.top() + 4, track.width() - 8, track.height() - 8)
    center_x = inner.center().x()
    half_width = inner.width() / 2.0
    value = clip_steering(steering_value)
    fill_width = half_width * abs(value)

    _draw_track(painter, track)

    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 155), 1))
    painter.drawLine(QPointF(center_x, track.top() - 4), QPointF(center_x, track.bottom() + 4))

    if fill_width > 0.0:
        if value >= 0:
            fill_rect = QRectF(center_x, inner.top(), fill_width, inner.height())
        else:
            fill_rect = QRectF(center_x - fill_width, inner.top(), fill_width, inner.height())
        painter.setPen(Qt.NoPen)
        painter.setBrush(_steering_fill_color(value))
        painter.drawRect(fill_rect)

    painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
    painter.drawLine(QPointF(inner.left(), inner.center().y()), QPointF(inner.right(), inner.center().y()))
    painter.restore()

    _draw_label(painter, QRectF(track.right() + 8, track.top() - 2, 92, 24), f"STR {steering_value:.2f}")


def _draw_steering_arc(painter: QPainter, pixmap: QPixmap, steering_value: float) -> None:
    width = pixmap.width()
    height = pixmap.height()
    size = min(width, height) * 0.25
    rect = QRectF(22, height - size - 28, size, size)
    value = clip_steering(steering_value)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)

    guide_pen = QPen(QColor(255, 255, 255, 120), 6)
    guide_pen.setCapStyle(Qt.FlatCap)
    painter.setPen(guide_pen)
    painter.drawArc(rect, 0, 180 * 16)

    span_angle = int(90 * value * 16)
    if span_angle != 0:
        value_pen = QPen(_steering_fill_color(value), 8)
        value_pen.setCapStyle(Qt.FlatCap)
        painter.setPen(value_pen)
        painter.drawArc(rect, 90 * 16, -span_angle)

    center = rect.center()
    radius = rect.width() / 2.0
    painter.setPen(QPen(QColor(255, 255, 255, 170), 2))
    painter.drawLine(QPointF(center.x(), center.y()), QPointF(center.x(), rect.top()))

    end_angle_deg = 90.0 - 90.0 * value
    end_x = center.x() + radius * cos(radians(end_angle_deg))
    end_y = center.y() - radius * sin(radians(end_angle_deg))
    painter.setPen(QPen(_steering_fill_color(value), 3))
    painter.drawLine(QPointF(center.x(), center.y()), QPointF(end_x, end_y))
    painter.restore()

    _draw_label(painter, QRectF(rect.left() - 8, rect.bottom() - 4, rect.width() + 16, 24), f"STR ARC {steering_value:.2f}")


def _draw_drive_arrow(painter: QPainter, pixmap: QPixmap, steering_value: float, speed_value: float) -> None:
    width = float(pixmap.width())
    height = float(pixmap.height())
    start, end = drive_arrow_points(width, height, steering_value, speed_value)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor(255, 90, 90, 180), 2, Qt.DashLine))
    painter.drawLine(QPointF(start.x(), height - max(12.0, height * 0.04)), start)

    painter.setPen(QPen(QColor(255, 90, 90, 230), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawLine(start, end)

    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    unit_x = dx / length
    unit_y = dy / length
    head = 12.0
    left = QPointF(
        end.x() - unit_x * head - unit_y * head * 0.6,
        end.y() - unit_y * head + unit_x * head * 0.6,
    )
    right = QPointF(
        end.x() - unit_x * head + unit_y * head * 0.6,
        end.y() - unit_y * head - unit_x * head * 0.6,
    )
    painter.drawLine(end, left)
    painter.drawLine(end, right)
    painter.restore()

    _draw_label(
        painter,
        QRectF(start.x() - 82, max(6.0, start.y() - 42.0), 164, 22),
        f"DRV X {steering_value:.2f} | Y {speed_value:.2f}",
    )


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
    if options.get('drive_arrow'):
        _draw_drive_arrow(painter, rendered, steering_value, throttle_value)

    painter.end()
    return rendered
