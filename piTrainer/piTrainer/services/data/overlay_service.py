from __future__ import annotations

import json
import math
from math import cos, pi, radians, sin, sqrt
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPainterPath, QPen, QPixmap


# Shared overlay helpers kept here to avoid duplicated path/arrow math across Data, Train and Validation.
# PiTrainer keeps the older debug overlays, but the main path overlay now mirrors PiSD V7's recorded
# road-guide geometry so frames can be redrawn from labels.jsonl/manifest overlay metadata.

PISD_OVERLAY_DEFAULTS: dict[str, float] = {
    'path_length_scale': 1.0,
    'curve_strength': 3.35,
    'opacity': 0.94,
    'path_width_scale': 0.34,
    'sample_count': 56,
    'wheelbase': 0.32,
    'max_steer_rad': 0.62,
    'curve_response': 1.05,
    'curvature_scale': 0.52,
    'curvature_limit': 2.25,
    'entry_blend_start': 0.76,
    'road_half_width': 0.41,
    'base_y': 96,
    'horizon_y': 31,
    'camera_forward_offset': 0.26,
    'near_clip': 0.19,
    'perspective_scale': 64,
    'perspective_depth': 0.92,
    'turn_compression': 0.075,
    'turn_width_taper': 0.08,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp(value: Any, lower: float, upper: float, fallback: float = 0.0) -> float:
    number = _to_float(value, fallback)
    return max(lower, min(upper, number))


def _overlay_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return dict(decoded) if isinstance(decoded, dict) else {}
    return {}


def _overlay_number(settings: dict[str, Any], key: str) -> float:
    if key in settings:
        number = _to_float(settings.get(key), math.nan)
        if math.isfinite(number):
            return number
    return float(PISD_OVERLAY_DEFAULTS[key])


def _bounded_opacity(settings: dict[str, Any]) -> float:
    return _clamp(_overlay_number(settings, 'opacity'), 0.0, 1.0, PISD_OVERLAY_DEFAULTS['opacity'])


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


def _pisd_road_geometry(
    width: float,
    height: float,
    steering_value: float,
    throttle_value: float,
    overlay_settings: dict[str, Any] | None,
) -> dict[str, Any]:
    settings = _overlay_dict(overlay_settings)
    safe_throttle = _clamp(throttle_value, -1.0, 1.0, 0.0)
    safe_steering = _clamp(steering_value, -1.0, 1.0, 0.0)
    speed = max(0.0, safe_throttle)
    moving_reverse = safe_throttle < -0.02

    curve_strength = _overlay_number(settings, 'curve_strength')
    length_scale = _overlay_number(settings, 'path_length_scale')
    width_calibration = _overlay_number(settings, 'path_width_scale')
    visual_width_scale = max(0.03, 0.82 + width_calibration * 0.32)
    base_y = _clamp(_overlay_number(settings, 'base_y'), -40, 160, PISD_OVERLAY_DEFAULTS['base_y'])
    base_horizon_y = _to_float(_overlay_number(settings, 'horizon_y'), PISD_OVERLAY_DEFAULTS['horizon_y'])
    lookahead = _clamp(1.65 + speed * 0.85 + (length_scale - 1.0) * 0.75, 0.25, 8.5, 1.65)
    horizon_y = _clamp(base_horizon_y - speed * 8.5 - (length_scale - 1.0) * 14, -60, 120, PISD_OVERLAY_DEFAULTS['horizon_y'])
    samples = int(round(_clamp(_overlay_number(settings, 'sample_count'), 8, 220, PISD_OVERLAY_DEFAULTS['sample_count'])))
    wheelbase = max(0.01, abs(_overlay_number(settings, 'wheelbase')) or PISD_OVERLAY_DEFAULTS['wheelbase'])
    max_steer_rad = max(0.01, abs(_overlay_number(settings, 'max_steer_rad')) or PISD_OVERLAY_DEFAULTS['max_steer_rad'])
    curve_response = _clamp(_overlay_number(settings, 'curve_response'), 0.2, 4.0, PISD_OVERLAY_DEFAULTS['curve_response'])
    curvature_scale = _to_float(_overlay_number(settings, 'curvature_scale'), PISD_OVERLAY_DEFAULTS['curvature_scale'])
    curvature_limit = max(0.05, abs(_overlay_number(settings, 'curvature_limit')) or PISD_OVERLAY_DEFAULTS['curvature_limit'])
    entry_blend_start = _clamp(_overlay_number(settings, 'entry_blend_start'), -1.5, 2.0, PISD_OVERLAY_DEFAULTS['entry_blend_start'])
    road_half_width_base = max(0.01, abs(_overlay_number(settings, 'road_half_width')) or PISD_OVERLAY_DEFAULTS['road_half_width'])
    camera_forward_offset = max(0.01, abs(_overlay_number(settings, 'camera_forward_offset')) or PISD_OVERLAY_DEFAULTS['camera_forward_offset'])
    near_clip = max(0.01, abs(_overlay_number(settings, 'near_clip')) or PISD_OVERLAY_DEFAULTS['near_clip'])
    perspective_base = max(1.0, abs(_overlay_number(settings, 'perspective_scale')) or PISD_OVERLAY_DEFAULTS['perspective_scale'])
    perspective_depth = max(0.05, abs(_overlay_number(settings, 'perspective_depth')) or PISD_OVERLAY_DEFAULTS['perspective_depth'])
    turn_compression_setting = _to_float(_overlay_number(settings, 'turn_compression'), PISD_OVERLAY_DEFAULTS['turn_compression'])
    turn_width_taper_setting = _to_float(_overlay_number(settings, 'turn_width_taper'), PISD_OVERLAY_DEFAULTS['turn_width_taper'])

    visual_steering = safe_steering
    shaped_steering = math.copysign(abs(visual_steering) ** curve_response, visual_steering) if abs(visual_steering) > 0 else 0.0
    steer_rad = shaped_steering * max_steer_rad
    curvature_gain = curve_strength / PISD_OVERLAY_DEFAULTS['curve_strength'] if PISD_OVERLAY_DEFAULTS['curve_strength'] else 1.0
    curvature = _clamp((math.tan(steer_rad) / wheelbase) * curvature_scale * curvature_gain, -curvature_limit, curvature_limit, 0.0)
    road_half_width = road_half_width_base * visual_width_scale

    center_world: list[dict[str, float]] = []
    x = 0.0
    z = 0.0
    heading = 0.0
    ds = lookahead / max(1, samples - 1)
    for index in range(samples):
        center_world.append({'x': x, 'z': z, 'heading': heading})
        if index < samples - 1:
            progress = index / max(1.0, samples - 1.0)
            entry_blend = entry_blend_start + (1.0 - entry_blend_start) * math.sin(progress * math.pi * 0.5)
            local_curvature = curvature * entry_blend
            mid_heading = heading + local_curvature * ds * 0.5
            x += math.sin(mid_heading) * ds
            z += math.cos(mid_heading) * ds
            heading += local_curvature * ds

    def project_ground_point(point: dict[str, float]) -> QPointF:
        projected_z = max(near_clip, point['z'] + camera_forward_offset)
        max_projected_z = lookahead + camera_forward_offset
        perspective_scale = perspective_base / (projected_z + perspective_depth)
        near_perspective_z = max(near_clip, camera_forward_offset)
        scale_at_near = perspective_base / (near_perspective_z + perspective_depth)
        scale_at_far = perspective_base / (max_projected_z + perspective_depth)
        depth_ratio = _clamp((perspective_scale - scale_at_far) / max(0.01, scale_at_near - scale_at_far), 0, 1, 0)
        y_percent = horizon_y + (base_y - horizon_y) * depth_ratio
        t = _clamp((projected_z - near_clip) / max(0.1, max_projected_z - near_clip), 0, 1, 0)
        turn_compression = max(0.05, 1.0 - turn_compression_setting * t) if abs(curvature) > 0.45 else 1.0
        edge_guard = 2.6 + t * 2.8
        x_percent = _clamp(50.0 + point['x'] * perspective_scale * turn_compression, edge_guard, 100.0 - edge_guard, 50.0)
        y_percent = _clamp(y_percent, 7.0, 99.0, y_percent)
        return QPointF((x_percent / 100.0) * width, (y_percent / 100.0) * height)

    left_points: list[QPointF] = []
    right_points: list[QPointF] = []
    center_points: list[QPointF] = []
    for index, point in enumerate(center_world):
        previous = center_world[max(0, index - 2)]
        next_point = center_world[min(len(center_world) - 1, index + 2)]
        dx = next_point['x'] - previous['x']
        dz = next_point['z'] - previous['z']
        tangent_length = math.hypot(dx, dz) or 1.0
        normal_x = -dz / tangent_length
        normal_z = dx / tangent_length
        progress = index / max(1.0, len(center_world) - 1.0)
        turn_width_taper = max(0.05, 1.0 - abs(curvature) * turn_width_taper_setting * progress)
        local_half_width = road_half_width * turn_width_taper
        left_points.append(project_ground_point({'x': point['x'] + normal_x * local_half_width, 'z': point['z'] + normal_z * local_half_width}))
        right_points.append(project_ground_point({'x': point['x'] - normal_x * local_half_width, 'z': point['z'] - normal_z * local_half_width}))
        center_points.append(project_ground_point(point))

    return {
        'left_points': left_points,
        'right_points': right_points,
        'center_points': center_points,
        'start': center_points[0] if center_points else QPointF(width / 2.0, height * 0.96),
        'end': center_points[-1] if center_points else QPointF(width / 2.0, height * 0.31),
        'curve': curvature * curve_strength,
        'moving_reverse': moving_reverse,
        'speed': speed,
        'settings': settings,
    }


def _draw_pisd_road_guide(
    painter: QPainter,
    pixmap: QPixmap,
    steering_value: float,
    throttle_value: float,
    overlay_settings: dict[str, Any] | None,
    *,
    color: QColor,
    label: str | None = None,
    comparison: bool = False,
) -> None:
    geometry = _pisd_road_geometry(float(pixmap.width()), float(pixmap.height()), steering_value, throttle_value, overlay_settings)
    if geometry.get('moving_reverse'):
        return

    settings = geometry.get('settings') if isinstance(geometry.get('settings'), dict) else {}
    speed = float(geometry.get('speed', 0.0) or 0.0)
    steering_abs = abs(clip_steering(steering_value))
    moving_forward = throttle_value >= 0.02
    calibrated_opacity = _bounded_opacity(settings)
    width_scale = max(0.05, abs(_overlay_number(settings, 'path_width_scale')))
    visible_opacity = calibrated_opacity if (moving_forward or steering_abs >= 0.02) else max(0.12, calibrated_opacity * 0.26)
    if comparison:
        visible_opacity = max(0.30, visible_opacity * 0.95)

    left_points = geometry['left_points']
    right_points = geometry['right_points']
    center_points = geometry['center_points']
    surface_path = _polygon_path(left_points, right_points)
    left_path = _smooth_polyline_path(left_points)
    right_path = _smooth_polyline_path(right_points)
    center_path = _smooth_polyline_path(center_points)

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)

    surface_alpha = int(255 * (max(0.16, calibrated_opacity * 0.36) if moving_forward else max(0.04, calibrated_opacity * 0.10)))
    if comparison:
        surface_alpha = min(surface_alpha, 70)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), max(8, min(105, surface_alpha)))))
    painter.drawPath(surface_path)

    boundary_alpha = max(25, min(255, int(255 * visible_opacity)))
    boundary_pen = QPen(QColor(color.red(), color.green(), color.blue(), boundary_alpha), max(1.0, 2.25 * width_scale), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(boundary_pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(left_path)
    painter.drawPath(right_path)

    center_alpha = int(255 * (max(0.18, calibrated_opacity * 0.34) if moving_forward else max(0.08, calibrated_opacity * 0.16)))
    center_pen = QPen(QColor(color.red(), color.green(), color.blue(), max(20, min(255, center_alpha))), max(1.0, (1.15 + speed * 0.38) * width_scale), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    if not moving_forward:
        center_pen.setStyle(Qt.DashLine)
    painter.setPen(center_pen)
    painter.drawPath(center_path)

    if not comparison:
        painter.setPen(QPen(QColor(255, 255, 255, 185), 1))
        painter.setBrush(QColor(255, 255, 255, 190))
        start = geometry['start']
        end = geometry['end']
        painter.drawEllipse(start, 3.5, 3.5)
        painter.setBrush(color)
        painter.drawEllipse(end, 4.5, 4.5)
    painter.restore()

    if label:
        start = geometry['start']
        curve = abs(float(geometry.get('curve', 0.0) or 0.0))
        curve_text = 'trapezium' if curve < 0.08 else f'road curve {curve:.2f}'
        _draw_label(painter, QRectF(start.x() - 136, max(6.0, start.y() - 62.0), 272, 24), f"{label} · {curve_text}", color)


def _draw_path_preview(painter: QPainter, pixmap: QPixmap, record: dict[str, Any] | None, steering_value: float, speed_value: float) -> None:
    settings = _overlay_dict((record or {}).get('overlay_settings'))
    _draw_pisd_road_guide(
        painter,
        pixmap,
        steering_value,
        speed_value,
        settings,
        color=QColor(36, 212, 255, 235),
        label=f"PiSD V7 SPD {speed_value:.2f} | STR {steering_value:.2f}",
    )


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
    painter.setPen(QColor('#f7fbff'))
    painter.drawText(QRectF(legend_rect.left() + 40, legend_rect.top() + 4, legend_rect.width() - 45, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Target PiSD road guide')
    painter.setPen(QPen(QColor(255, 164, 76, 235), 3))
    painter.drawLine(QPointF(legend_rect.left() + 12, legend_rect.top() + 32), QPointF(legend_rect.left() + 34, legend_rect.top() + 32))
    painter.setPen(QColor('#f7fbff'))
    painter.drawText(QRectF(legend_rect.left() + 40, legend_rect.top() + 21, legend_rect.width() - 45, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Predicted PiSD road guide')
    painter.restore()

    painter.end()
    return rendered
