from __future__ import annotations

from math import cos, radians, sin, sqrt
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPainterPath, QPen, QPixmap


# Shared overlay helpers kept here to avoid duplicated path/arrow math across Data, Train and Validation.

def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clip_steering(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def clip_speed(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _layout_margins(width: float, height: float) -> tuple[float, float, float]:
    margin_x = max(18.0, width * 0.06)
    margin_top = max(18.0, height * 0.08)
    margin_bottom = max(22.0, height * 0.08)
    return margin_x, margin_top, margin_bottom


def drive_arrow_points(width: float, height: float, steering_value: float, speed_value: float) -> tuple[QPointF, QPointF]:
    margin_x, margin_top, margin_bottom = _layout_margins(width, height)
    start = QPointF(width / 2.0, height - margin_bottom)
    steering = clip_steering(steering_value)
    speed = clip_speed(speed_value)
    half_span_x = max(20.0, (width / 2.0) - margin_x)
    span_y = max(20.0, height - margin_top - margin_bottom)

    end_x = start.x() + steering * half_span_x
    end_y = start.y() - speed * span_y
    return start, QPointF(end_x, end_y)


def drive_values_from_point(x: float, y: float, width: float, height: float) -> tuple[float, float]:
    margin_x, margin_top, margin_bottom = _layout_margins(width, height)
    start_x = width / 2.0
    start_y = height - margin_bottom
    half_span_x = max(20.0, (width / 2.0) - margin_x)
    span_y = max(20.0, height - margin_top - margin_bottom)

    steering = clip_steering((float(x) - start_x) / half_span_x)
    speed = clip_speed((start_y - float(y)) / span_y)
    return steering, speed


def _draw_label(painter: QPainter, rect: QRectF, text: str, color: QColor | None = None) -> None:
    painter.save()
    painter.setPen(color or QColor('#f7fbff'))
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


def _path_geometry(width: float, height: float, steering_value: float, speed_value: float) -> tuple[QPointF, QPointF, QPointF, QPointF]:
    start, end = drive_arrow_points(width, height, steering_value, speed_value)
    steering = clip_steering(steering_value)
    vertical_travel = max(18.0, start.y() - end.y())
    lateral_travel = end.x() - start.x()
    bend = lateral_travel * 0.82 + steering * max(width * 0.10, vertical_travel * 0.18)
    control_1 = QPointF(start.x() + bend * 0.22, start.y() - vertical_travel * 0.18)
    control_2 = QPointF(start.x() + bend * 1.02, start.y() - vertical_travel * 0.78)
    return start, control_1, control_2, end


def _cubic_point(start: QPointF, control_1: QPointF, control_2: QPointF, end: QPointF, t: float) -> QPointF:
    u = 1.0 - t
    x = (u ** 3) * start.x() + 3 * (u ** 2) * t * control_1.x() + 3 * u * (t ** 2) * control_2.x() + (t ** 3) * end.x()
    y = (u ** 3) * start.y() + 3 * (u ** 2) * t * control_1.y() + 3 * u * (t ** 2) * control_2.y() + (t ** 3) * end.y()
    return QPointF(x, y)


def _sample_cubic_points(start: QPointF, control_1: QPointF, control_2: QPointF, end: QPointF, steps: int = 24) -> list[QPointF]:
    return [_cubic_point(start, control_1, control_2, end, index / float(steps)) for index in range(steps + 1)]


def _offset_polyline(points: list[QPointF], offset: float) -> list[QPointF]:
    if len(points) <= 1:
        return list(points)
    offset_points: list[QPointF] = []
    for index, point in enumerate(points):
        prev_point = points[max(0, index - 1)]
        next_point = points[min(len(points) - 1, index + 1)]
        dx = next_point.x() - prev_point.x()
        dy = next_point.y() - prev_point.y()
        length = max(1e-6, sqrt(dx * dx + dy * dy))
        nx = -dy / length
        ny = dx / length
        offset_points.append(QPointF(point.x() + nx * offset, point.y() + ny * offset))
    return offset_points


def _polyline_path(points: list[QPointF]) -> QPainterPath:
    if not points:
        return QPainterPath()
    path = QPainterPath(points[0])
    for point in points[1:]:
        path.lineTo(point)
    return path


def _draw_single_path(
    painter: QPainter,
    pixmap: QPixmap,
    steering_value: float,
    speed_value: float,
    main_color: QColor,
    label: str | None = None,
) -> None:
    width = float(pixmap.width())
    height = float(pixmap.height())
    start, control_1, control_2, end = _path_geometry(width, height, steering_value, speed_value)
    center_points = _sample_cubic_points(start, control_1, control_2, end)
    lane_half_width = max(7.0, min(width, height) * 0.014)
    left_points = _offset_polyline(center_points, -lane_half_width)
    right_points = _offset_polyline(center_points, lane_half_width)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)

    anchor_y = height - max(12.0, height * 0.04)
    guide_pen = QPen(QColor(255, 255, 255, 70), 2, Qt.DashLine)
    guide_pen.setCapStyle(Qt.RoundCap)
    painter.setPen(guide_pen)
    painter.drawLine(QPointF(start.x(), anchor_y), start)

    rail_pen = QPen(QColor(main_color.red(), main_color.green(), main_color.blue(), 110), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(rail_pen)
    painter.drawPath(_polyline_path(left_points))
    painter.drawPath(_polyline_path(right_points))

    glow_pen = QPen(QColor(main_color.red(), main_color.green(), main_color.blue(), 85), 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(glow_pen)
    painter.drawPath(_polyline_path(center_points))

    center_pen = QPen(main_color, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(center_pen)
    painter.drawPath(_polyline_path(center_points))

    painter.setPen(QPen(QColor(255, 255, 255, 210), 2))
    painter.setBrush(QColor(255, 255, 255, 230))
    painter.drawEllipse(start, 4.0, 4.0)
    painter.setBrush(main_color)
    painter.drawEllipse(end, 6.0, 6.0)
    painter.setPen(QPen(main_color, 2, Qt.DashLine))
    painter.drawLine(QPointF(width / 2.0, end.y()), end)
    painter.restore()

    if label:
        _draw_label(painter, QRectF(start.x() - 112, max(6.0, start.y() - 60.0), 224, 24), label, main_color)


def _draw_path_preview(painter: QPainter, pixmap: QPixmap, steering_value: float, speed_value: float) -> None:
    _draw_single_path(painter, pixmap, steering_value, speed_value, QColor(36, 212, 255, 235), f"PATH SPD {speed_value:.2f} | STR {steering_value:.2f}")


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
    left = QPointF(end.x() - unit_x * head - unit_y * head * 0.6, end.y() - unit_y * head + unit_x * head * 0.6)
    right = QPointF(end.x() - unit_x * head + unit_y * head * 0.6, end.y() - unit_y * head - unit_x * head * 0.6)
    painter.drawLine(end, left)
    painter.drawLine(end, right)
    painter.restore()

    _draw_label(painter, QRectF(start.x() - 82, max(6.0, start.y() - 42.0), 164, 22), f"DRV X {steering_value:.2f} | Y {speed_value:.2f}")


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
        _draw_path_preview(painter, rendered, steering_value, throttle_value)
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
) -> QPixmap:
    if pixmap.isNull():
        return pixmap

    rendered = QPixmap(pixmap)
    painter = QPainter(rendered)
    painter.setRenderHint(QPainter.Antialiasing, True)

    _draw_single_path(painter, rendered, steering_true, speed_true, QColor(74, 208, 120, 235), None)
    _draw_single_path(painter, rendered, steering_pred, speed_pred, QColor(255, 164, 76, 235), None)

    legend_rect = QRectF(16, 10, min(250.0, rendered.width() * 0.44), 42)
    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
    painter.setBrush(QBrush(QColor(18, 22, 31, 165)))
    painter.drawRoundedRect(legend_rect, 8, 8)
    painter.setPen(QPen(QColor(74, 208, 120, 235), 3))
    painter.drawLine(QPointF(legend_rect.left() + 12, legend_rect.top() + 14), QPointF(legend_rect.left() + 34, legend_rect.top() + 14))
    painter.setPen(QColor('#f7fbff'))
    painter.drawText(QRectF(legend_rect.left() + 40, legend_rect.top() + 3, legend_rect.width() - 45, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Target / trained path')
    painter.setPen(QPen(QColor(255, 164, 76, 235), 3))
    painter.drawLine(QPointF(legend_rect.left() + 12, legend_rect.top() + 29), QPointF(legend_rect.left() + 34, legend_rect.top() + 29))
    painter.setPen(QColor('#f7fbff'))
    painter.drawText(QRectF(legend_rect.left() + 40, legend_rect.top() + 18, legend_rect.width() - 45, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Predicted path')
    painter.restore()

    painter.end()
    return rendered
