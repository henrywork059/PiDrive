from __future__ import annotations

from math import cos, pi, radians, sin, sqrt

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPainterPath, QPen, QPixmap

from ...ui.theme import theme_color
from .overlay_values import clip_speed, clip_steering, drive_arrow_points


def _draw_label(painter: QPainter, rect: QRectF, text: str, color: QColor | None = None) -> None:
    painter.save()
    painter.setPen(color or QColor(theme_color('text_primary')))
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


def _sample_quarter_ellipse_points(start: QPointF, end: QPointF, steps: int = 40) -> list[QPointF]:
    lateral = end.x() - start.x()
    vertical = start.y() - end.y()
    if abs(lateral) < 1e-3 or vertical <= 1e-3:
        return [
            QPointF(
                start.x() + (end.x() - start.x()) * (index / float(steps)),
                start.y() + (end.y() - start.y()) * (index / float(steps)),
            )
            for index in range(steps + 1)
        ]

    radius_y = vertical
    points: list[QPointF] = []
    for index in range(steps + 1):
        theta = (index / float(steps)) * (pi / 2.0)
        x = end.x() + (start.x() - end.x()) * cos(theta)
        y = start.y() - radius_y * sin(theta)
        points.append(QPointF(x, y))
    return points


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


def _smooth_polyline_path(points: list[QPointF]) -> QPainterPath:
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(points[0])
    if len(points) < 3:
        for point in points[1:]:
            path.lineTo(point)
        return path
    for index in range(1, len(points) - 2):
        current = points[index]
        next_point = points[index + 1]
        midpoint = QPointF((current.x() + next_point.x()) / 2.0, (current.y() + next_point.y()) / 2.0)
        path.quadTo(current, midpoint)
    path.quadTo(points[-2], points[-1])
    return path


def _polyline_path(points: list[QPointF]) -> QPainterPath:
    if not points:
        return QPainterPath()
    path = QPainterPath(points[0])
    for point in points[1:]:
        path.lineTo(point)
    return path


def _polygon_path(left_points: list[QPointF], right_points: list[QPointF]) -> QPainterPath:
    if not left_points or not right_points:
        return QPainterPath()
    path = _smooth_polyline_path(left_points)
    path.lineTo(right_points[-1])
    reversed_right = list(reversed(right_points))
    if len(reversed_right) < 3:
        for point in reversed_right[1:]:
            path.lineTo(point)
    else:
        for index in range(1, len(reversed_right) - 2):
            current = reversed_right[index]
            next_point = reversed_right[index + 1]
            midpoint = QPointF((current.x() + next_point.x()) / 2.0, (current.y() + next_point.y()) / 2.0)
            path.quadTo(current, midpoint)
        path.quadTo(reversed_right[-2], reversed_right[-1])
    path.closeSubpath()
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
    start, end = drive_arrow_points(width, height, steering_value, speed_value)
    center_points = _sample_quarter_ellipse_points(start, end)
    lane_half_width = max(7.0, min(width, height) * (0.014 + 0.005 * abs(clip_steering(steering_value))))
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
    painter.restore()

    if label:
        _draw_label(painter, QRectF(start.x() - 112, max(6.0, start.y() - 60.0), 224, 24), label, main_color)

def _draw_legacy_path_preview(painter: QPainter, pixmap: QPixmap, steering_value: float, speed_value: float) -> None:
    _draw_single_path(painter, pixmap, steering_value, speed_value, QColor(180, 210, 255, 185), f"LEGACY SPD {speed_value:.2f} | STR {steering_value:.2f}")


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
