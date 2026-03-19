from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .debug_tools import clamp_float, clamp_int, coerce_bool, sanitize_label_name

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PACKAGE_ROOT / 'config' / 'runtime_settings.json'

DEFAULT_SETTINGS: dict[str, Any] = {
    'camera': {
        'width': 426,
        'height': 240,
        'fps': 30,
        'preview_fps': 12,
        'preview_quality': 60,
        'stream_quality': 'balanced',
        'format': 'BGR888',
        'auto_exposure': True,
        'exposure_us': 12000,
        'analogue_gain': 1.0,
        'exposure_compensation': 0.0,
        'auto_white_balance': True,
        'brightness': 0.0,
        'contrast': 1.0,
        'saturation': 1.0,
        'sharpness': 1.0,
    },
    'motor': {
        'left_direction': 1,
        'right_direction': 1,
        'steering_direction': 1,
        'left_max_speed': 1.0,
        'right_max_speed': 1.0,
        'left_bias': 0.0,
        'right_bias': 0.0,
    },
    'runtime': {
        'steer_mix': 0.75,
        'tick_s_live': 0.1,
        'tick_s_sim': 0.2,
        'allow_virtual_grab_without_arm': False,
        'event_history_limit': 200,
    },
    'perception': {
        'enabled': True,
        'blur_kernel': 5,
        'open_iterations': 1,
        'close_iterations': 1,
        'min_box_area_ratio': 0.0025,
        'max_detections_per_label': 3,
        'labels': {
            'he3': {
                'ranges': [
                    {'lower': [5, 100, 90], 'upper': [35, 255, 255]}
                ],
                'min_box_area_ratio': 0.0025,
            },
            'he3_zone': {
                'ranges': [
                    {'lower': [90, 80, 70], 'upper': [135, 255, 255]}
                ],
                'min_box_area_ratio': 0.0040,
            },
        },
    },
}

_STREAM_QUALITY_CHOICES = {'low_latency', 'balanced', 'high', 'manual'}
_CAMERA_FORMAT_CHOICES = {'BGR888', 'RGB888', 'XBGR8888'}


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _normalize_hsv_triplet(values: Any, default: list[int]) -> list[int]:
    if not isinstance(values, (list, tuple)):
        values = list(default)
    result: list[int] = []
    for index, fallback in enumerate(default):
        try:
            item = int(values[index])
        except Exception:
            item = int(fallback)
        result.append(max(0, min(255, item)))
    if len(result) < 3:
        result.extend(int(x) for x in default[len(result):3])
    return result[:3]


def _normalize_label_spec(spec: Any, fallback: dict[str, Any], default_min_ratio: float, default_max_det: int) -> dict[str, Any]:
    source = spec if isinstance(spec, dict) else {}
    out = copy.deepcopy(fallback)
    out['min_box_area_ratio'] = round(
        clamp_float(source.get('min_box_area_ratio', out.get('min_box_area_ratio', default_min_ratio)), out.get('min_box_area_ratio', default_min_ratio), 0.00001, 1.0),
        6,
    )
    out['max_detections_per_label'] = clamp_int(
        source.get('max_detections_per_label', source.get('max_dets', out.get('max_detections_per_label', default_max_det))),
        out.get('max_detections_per_label', default_max_det),
        1,
        20,
    )

    ranges = source.get('ranges', out.get('ranges', []))
    normalized_ranges: list[dict[str, list[int]]] = []
    if isinstance(ranges, list):
        for item in ranges[:8]:
            if not isinstance(item, dict):
                continue
            lower = _normalize_hsv_triplet(item.get('lower'), [0, 0, 0])
            upper = _normalize_hsv_triplet(item.get('upper'), [255, 255, 255])
            normalized_ranges.append({'lower': lower, 'upper': upper})
    if not normalized_ranges:
        normalized_ranges = copy.deepcopy(out.get('ranges', []))
    out['ranges'] = normalized_ranges
    return out



def normalize_settings(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_SETTINGS, data or {})

    camera = merged.get('camera') or {}
    merged['camera'] = {
        'width': clamp_int(camera.get('width', 426), 426, 64, 3840),
        'height': clamp_int(camera.get('height', 240), 240, 48, 2160),
        'fps': clamp_int(camera.get('fps', 30), 30, 1, 120),
        'preview_fps': clamp_int(camera.get('preview_fps', 12), 12, 1, 30),
        'preview_quality': clamp_int(camera.get('preview_quality', 60), 60, 20, 95),
        'stream_quality': str(camera.get('stream_quality', 'balanced') or 'balanced').strip().lower(),
        'format': str(camera.get('format', 'BGR888') or 'BGR888').strip().upper(),
        'auto_exposure': coerce_bool(camera.get('auto_exposure', True), True),
        'exposure_us': clamp_int(camera.get('exposure_us', 12000), 12000, 100, 200000),
        'analogue_gain': round(clamp_float(camera.get('analogue_gain', 1.0), 1.0, 0.0, 64.0), 3),
        'exposure_compensation': round(clamp_float(camera.get('exposure_compensation', 0.0), 0.0, -8.0, 8.0), 3),
        'auto_white_balance': coerce_bool(camera.get('auto_white_balance', True), True),
        'brightness': round(clamp_float(camera.get('brightness', 0.0), 0.0, -1.0, 1.0), 3),
        'contrast': round(clamp_float(camera.get('contrast', 1.0), 1.0, 0.0, 32.0), 3),
        'saturation': round(clamp_float(camera.get('saturation', 1.0), 1.0, 0.0, 32.0), 3),
        'sharpness': round(clamp_float(camera.get('sharpness', 1.0), 1.0, 0.0, 16.0), 3),
    }
    if merged['camera']['stream_quality'] not in _STREAM_QUALITY_CHOICES:
        merged['camera']['stream_quality'] = 'balanced'
    if merged['camera']['format'] not in _CAMERA_FORMAT_CHOICES:
        merged['camera']['format'] = 'BGR888'

    motor = merged.get('motor') or {}
    merged['motor'] = {
        'left_direction': -1 if int(motor.get('left_direction', 1)) < 0 else 1,
        'right_direction': -1 if int(motor.get('right_direction', 1)) < 0 else 1,
        'steering_direction': -1 if int(motor.get('steering_direction', 1)) < 0 else 1,
        'left_max_speed': round(clamp_float(motor.get('left_max_speed', 1.0), 1.0, 0.0, 1.0), 3),
        'right_max_speed': round(clamp_float(motor.get('right_max_speed', 1.0), 1.0, 0.0, 1.0), 3),
        'left_bias': round(clamp_float(motor.get('left_bias', 0.0), 0.0, -0.35, 0.35), 3),
        'right_bias': round(clamp_float(motor.get('right_bias', 0.0), 0.0, -0.35, 0.35), 3),
    }

    runtime = merged.get('runtime') or {}
    merged['runtime'] = {
        'steer_mix': round(clamp_float(runtime.get('steer_mix', 0.75), 0.75, 0.0, 1.0), 3),
        'tick_s_live': round(clamp_float(runtime.get('tick_s_live', 0.1), 0.1, 0.02, 10.0), 3),
        'tick_s_sim': round(clamp_float(runtime.get('tick_s_sim', 0.2), 0.2, 0.02, 10.0), 3),
        'allow_virtual_grab_without_arm': coerce_bool(runtime.get('allow_virtual_grab_without_arm', False), False),
        'event_history_limit': clamp_int(runtime.get('event_history_limit', 200), 200, 20, 1000),
    }

    perception = merged.get('perception') or {}
    default_perception = DEFAULT_SETTINGS['perception']
    normalized_perception: dict[str, Any] = {
        'enabled': coerce_bool(perception.get('enabled', True), True),
        'blur_kernel': clamp_int(perception.get('blur_kernel', 5), 5, 1, 31),
        'open_iterations': clamp_int(perception.get('open_iterations', 1), 1, 0, 10),
        'close_iterations': clamp_int(perception.get('close_iterations', 1), 1, 0, 10),
        'min_box_area_ratio': round(clamp_float(perception.get('min_box_area_ratio', 0.0025), 0.0025, 0.00001, 1.0), 6),
        'max_detections_per_label': clamp_int(perception.get('max_detections_per_label', 3), 3, 1, 20),
        'labels': {},
    }
    if normalized_perception['blur_kernel'] % 2 == 0:
        normalized_perception['blur_kernel'] += 1

    labels_in = perception.get('labels') or {}
    default_labels = default_perception.get('labels') or {}
    label_names = set(default_labels.keys()) | set(labels_in.keys())
    for raw_name in sorted(label_names):
        name = sanitize_label_name(raw_name, 'label')
        fallback = default_labels.get(name, {
            'ranges': [{'lower': [0, 0, 0], 'upper': [255, 255, 255]}],
            'min_box_area_ratio': normalized_perception['min_box_area_ratio'],
            'max_detections_per_label': normalized_perception['max_detections_per_label'],
        })
        normalized_perception['labels'][name] = _normalize_label_spec(
            labels_in.get(raw_name, fallback),
            fallback,
            normalized_perception['min_box_area_ratio'],
            normalized_perception['max_detections_per_label'],
        )
    merged['perception'] = normalized_perception
    return merged



def load_settings(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or SETTINGS_PATH
    if not cfg_path.exists():
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        raw = json.loads(cfg_path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    return normalize_settings(raw)



def save_settings(data: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or SETTINGS_PATH
    merged = normalize_settings(data or {})
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return merged
