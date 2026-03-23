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
        'port': 5060,
        'refresh_ms': 200,
    },
    'ui': {
        'manual_speed': 0.55,
        'show_camera': True,
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
        'port': clamp_int(server.get('port', 5060), 5060, 1, 65535),
        'refresh_ms': clamp_int(server.get('refresh_ms', 200), 200, 50, 5000),
    }

    ui = merged.get('ui') or {}
    merged['ui'] = {
        'manual_speed': round(clamp_float(ui.get('manual_speed', 0.55), 0.55, 0.05, 1.0), 3),
        'show_camera': bool(ui.get('show_camera', True)),
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
