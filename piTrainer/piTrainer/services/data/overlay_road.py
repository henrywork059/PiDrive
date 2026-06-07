from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPixmap

from .overlay_primitives import _draw_label, _polygon_path, _smooth_polyline_path
from .overlay_values import (
    PISD_OVERLAY_DEFAULTS,
    _bounded_opacity,
    _clamp,
    _overlay_dict,
    _overlay_number,
    _to_float,
    clip_steering,
)


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
