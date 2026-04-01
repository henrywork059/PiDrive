from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .debug_tools import clamp_float, clamp_int, sanitize_label_name
from .project_paths import CONFIG_DIR

MANUAL_CONTROL_CONFIG_PATH = CONFIG_DIR / 'manual_control.json'

DEFAULT_MANUAL_CONTROL_CONFIG: dict[str, Any] = {
    'server': {
        'host': '0.0.0.0',
        'port': 5050,
        'refresh_ms': 200,
    },
    'ui': {
        'manual_speed': 0.55,
        'show_camera': True,
    },
    'arm': {
        'enabled': True,
        'backend': 'pca9685',
        'channels': 16,
        'i2c_address': 64,
        'frequency_hz': 50,
        'lift_channel': 0,
        'lift_channel_secondary': 1,
        'lift_secondary_enabled': True,
        'lift_secondary_multiplier': 1.0,
        'grip_channel': 2,
        'lift_up_angle': 40,
        'lift_down_angle': 115,
        'lift_step_angle': 1,
        'lift_step_interval_s': 0.1,
        'lift_up_direction': -1,
        'grip_hold_angle': 70,
        'grip_release_angle': 130,
        'grip_open_direction': -1,
        'grip_step_angle': 1,
        'grip_rate_deg_per_s': 10.0,
    },
    'ai': {
        'perception_backend': 'color',
        'deployed_model': 'none',
        'labels_file': '',
        'overlay_enabled': True,
        'input_size': 0,
        'confidence_threshold': 0.25,
        'iou_threshold': 0.45,
        'max_overlay_fps': 6.0,
        'overlay_frame_skip': 5,
        'target_label': 'he3',
        'drop_zone_label': 'he3_zone',
    },
    'competition': {
        'current_session': 'session_1',
        'sessions': {
            'session_1': {
                'label': 'Competition Session 1',
                'team_name': '',
                'driver_name': '',
                'notes': '',
            },
            'session_2': {
                'label': 'Competition Session 2',
                'team_name': '',
                'driver_name': '',
                'notes': '',
            },
        },
    },
}


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.stem + '_', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


def normalize_manual_control_config(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_MANUAL_CONTROL_CONFIG, data or {})

    server = merged.get('server') or {}
    merged['server'] = {
        'host': str(server.get('host', '0.0.0.0') or '0.0.0.0').strip() or '0.0.0.0',
        'port': clamp_int(server.get('port', 5050), 5050, 1, 65535),
        'refresh_ms': clamp_int(server.get('refresh_ms', 200), 200, 50, 5000),
    }

    ui = merged.get('ui') or {}
    merged['ui'] = {
        'manual_speed': round(clamp_float(ui.get('manual_speed', 0.55), 0.55, 0.05, 1.0), 3),
        'show_camera': bool(ui.get('show_camera', True)),
    }

    arm = merged.get('arm') or {}
    backend = str(arm.get('backend', 'pca9685') or 'pca9685').strip().lower() or 'pca9685'
    merged['arm'] = {
        'enabled': bool(arm.get('enabled', True)),
        'backend': backend,
        'channels': clamp_int(arm.get('channels', 16), 16, 1, 16),
        'i2c_address': clamp_int(arm.get('i2c_address', 64), 64, 3, 119),
        'frequency_hz': clamp_int(arm.get('frequency_hz', 50), 50, 40, 1000),
        'lift_channel': clamp_int(arm.get('lift_channel', 0), 0, 0, 15),
        'lift_channel_secondary': clamp_int(arm.get('lift_channel_secondary', 1), 1, 0, 15),
        'lift_secondary_enabled': bool(arm.get('lift_secondary_enabled', True)),
        'lift_secondary_multiplier': round(clamp_float(arm.get('lift_secondary_multiplier', 1.0), 1.0, 0.0, 4.0), 3),
        'grip_channel': 2,
        'lift_up_angle': clamp_int(arm.get('lift_up_angle', 40), 40, 0, 180),
        'lift_down_angle': clamp_int(arm.get('lift_down_angle', 115), 115, 0, 180),
        'lift_step_angle': clamp_int(arm.get('lift_step_angle', 1), 1, 1, 45),
        'lift_step_interval_s': round(clamp_float(arm.get('lift_step_interval_s', 0.1), 0.1, 0.02, 1.0), 3),
        'lift_up_direction': -1 if str(arm.get('lift_up_direction', -1) or '-1').strip().startswith('-') else 1,
        'speed_multiplier': round(clamp_float(arm.get('speed_multiplier', 2.0), 2.0, 0.25, 8.0), 3),
        'hold_refresh_enabled': bool(arm.get('hold_refresh_enabled', True)),
        'hold_refresh_interval_s': round(clamp_float(arm.get('hold_refresh_interval_s', 0.75), 0.75, 0.1, 10.0), 3),
        'grip_hold_angle': clamp_int(arm.get('grip_hold_angle', 70), 70, 0, 180),
        'grip_release_angle': clamp_int(arm.get('grip_release_angle', 130), 130, 0, 180),
        'grip_open_direction': -1 if str(arm.get('grip_open_direction', -1) or '-1').strip().startswith('-') else 1,
        'grip_step_angle': clamp_int(arm.get('grip_step_angle', 1), 1, 1, 45),
        'grip_rate_deg_per_s': round(clamp_float(arm.get('grip_rate_deg_per_s', 10.0), 10.0, 0.5, 90.0), 3),
    }
    if merged['arm']['grip_channel'] in {merged['arm']['lift_channel'], merged['arm']['lift_channel_secondary']}:
        merged['arm']['grip_channel'] = 2

    ai = merged.get('ai') or {}
    deployed_model = str(ai.get('deployed_model', 'none') or 'none').strip() or 'none'
    if deployed_model != 'none' and not deployed_model.lower().endswith('.tflite'):
        deployed_model = 'none'
    labels_file = str(ai.get('labels_file', '') or '').strip()
    if labels_file and not labels_file.lower().endswith('.txt'):
        labels_file = ''
    perception_backend = str(ai.get('perception_backend', 'color') or 'color').strip().lower() or 'color'
    if perception_backend not in {'color', 'tflite'}:
        perception_backend = 'color'
    merged['ai'] = {
        'perception_backend': perception_backend,
        'deployed_model': deployed_model,
        'labels_file': labels_file,
        'overlay_enabled': bool(ai.get('overlay_enabled', True)),
        'input_size': clamp_int(ai.get('input_size', 0), 0, 0, 4096),
        'confidence_threshold': round(clamp_float(ai.get('confidence_threshold', 0.25), 0.25, 0.01, 0.99), 3),
        'iou_threshold': round(clamp_float(ai.get('iou_threshold', 0.45), 0.45, 0.01, 0.99), 3),
        'max_overlay_fps': round(clamp_float(ai.get('max_overlay_fps', 6.0), 6.0, 0.5, 30.0), 2),
        'overlay_frame_skip': clamp_int(ai.get('overlay_frame_skip', 5), 5, 1, 30),
        'target_label': str(ai.get('target_label', 'he3') or 'he3').strip() or 'he3',
        'drop_zone_label': str(ai.get('drop_zone_label', 'he3_zone') or 'he3_zone').strip() or 'he3_zone',
    }

    competition = merged.get('competition') or {}
    sessions_in = competition.get('sessions') or {}
    current_session = str(competition.get('current_session', 'session_1') or 'session_1').strip().lower()
    if current_session not in {'session_1', 'session_2'}:
        current_session = 'session_1'

    sessions_out: dict[str, Any] = {}
    for session_key in ('session_1', 'session_2'):
        source = sessions_in.get(session_key) or {}
        label = sanitize_label_name(source.get('label'), DEFAULT_MANUAL_CONTROL_CONFIG['competition']['sessions'][session_key]['label'])
        sessions_out[session_key] = {
            'label': label,
            'team_name': str(source.get('team_name', '') or '').strip(),
            'driver_name': str(source.get('driver_name', '') or '').strip(),
            'notes': str(source.get('notes', '') or '').strip(),
        }

    merged['competition'] = {
        'current_session': current_session,
        'sessions': sessions_out,
    }
    return merged


def load_manual_control_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or MANUAL_CONTROL_CONFIG_PATH
    if not cfg_path.exists():
        return copy.deepcopy(DEFAULT_MANUAL_CONTROL_CONFIG)
    try:
        raw = json.loads(cfg_path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    return normalize_manual_control_config(raw)


def save_manual_control_config(data: dict[str, Any] | None, path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or MANUAL_CONTROL_CONFIG_PATH
    normalized = normalize_manual_control_config(data)
    _atomic_write_text(cfg_path, json.dumps(normalized, indent=2, ensure_ascii=False) + '\n')
    return normalized
