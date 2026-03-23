from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .debug_tools import clamp_float, clamp_int, coerce_bool

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RUN_SETTINGS_PATH = PACKAGE_ROOT / 'config' / 'run_settings.json'

DEFAULT_RUN_SETTINGS: dict[str, Any] = {
    'runtime_mode': 'sim',
    'max_cycles': 2,
    'headless_tick_s': 0.20,
    'gui_tick_s': 0.20,
    'auto_start_gui': False,
}


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out



def normalize_run_settings(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_RUN_SETTINGS, data or {})
    runtime_mode = str(merged.get('runtime_mode', 'sim')).strip().lower()
    if runtime_mode not in {'sim', 'live'}:
        runtime_mode = 'sim'
    merged['runtime_mode'] = runtime_mode
    merged['max_cycles'] = clamp_int(merged.get('max_cycles', 2), 2, 1, 999)
    merged['headless_tick_s'] = round(clamp_float(merged.get('headless_tick_s', 0.20), 0.20, 0.02, 10.0), 3)
    merged['gui_tick_s'] = round(clamp_float(merged.get('gui_tick_s', 0.20), 0.20, 0.02, 10.0), 3)
    merged['auto_start_gui'] = coerce_bool(merged.get('auto_start_gui', False), False)
    return merged



def load_run_settings(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or RUN_SETTINGS_PATH
    if not cfg_path.exists():
        return copy.deepcopy(DEFAULT_RUN_SETTINGS)
    try:
        raw = json.loads(cfg_path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    return normalize_run_settings(raw)



def save_run_settings(data: dict[str, Any] | None, path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or RUN_SETTINGS_PATH
    normalized = normalize_run_settings(data)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(normalized, indent=2, ensure_ascii=False) + '\n'
    tmp_path = cfg_path.with_suffix(cfg_path.suffix + '.tmp')
    tmp_path.write_text(payload, encoding='utf-8')
    os.replace(tmp_path, cfg_path)
    return normalized
