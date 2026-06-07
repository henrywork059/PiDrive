from __future__ import annotations

import json
import math
from typing import Any

from PySide6.QtCore import QPointF


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
