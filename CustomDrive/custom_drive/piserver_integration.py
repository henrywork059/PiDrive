from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PISERVER_ROOT = REPO_ROOT / 'PiServer'
PISERVER_RUNTIME_PATH = PISERVER_ROOT / 'config' / 'runtime.json'


def ensure_piserver_import_path() -> None:
    for path in (REPO_ROOT, PISERVER_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def load_piserver_symbols():
    ensure_piserver_import_path()
    from piserver.core.config_store import ConfigStore  # noqa: WPS433,E402
    from piserver.services.camera_service import CameraService  # noqa: WPS433,E402
    from piserver.services.motor_service import MotorService  # noqa: WPS433,E402
    return CameraService, MotorService, ConfigStore


def get_piserver_config_store():
    _, _, ConfigStore = load_piserver_symbols()
    return ConfigStore(PISERVER_RUNTIME_PATH)


def load_piserver_runtime_config() -> dict[str, Any]:
    try:
        store = get_piserver_config_store()
        data = store.load()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data


def save_piserver_runtime_config(data: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(data if isinstance(data, dict) else {})
    store = get_piserver_config_store()
    store.save(payload)
    return payload


def merge_live_settings_with_piserver(custom_settings: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    settings = copy.deepcopy(custom_settings if isinstance(custom_settings, dict) else {})
    runtime = load_piserver_runtime_config()

    camera_cfg = runtime.get('camera')
    if isinstance(camera_cfg, dict):
        merged = copy.deepcopy(settings.get('camera') or {})
        merged.update(copy.deepcopy(camera_cfg))
        settings['camera'] = merged

    motor_cfg = runtime.get('motor')
    if isinstance(motor_cfg, dict):
        merged = copy.deepcopy(settings.get('motor') or {})
        merged.update(copy.deepcopy(motor_cfg))
        settings['motor'] = merged

    runtime_cfg = copy.deepcopy(settings.get('runtime') or {})
    if 'steer_mix' in runtime:
        runtime_cfg['steer_mix'] = runtime.get('steer_mix')
    settings['runtime'] = runtime_cfg
    return settings, runtime


def sync_custom_settings_to_piserver(custom_settings: dict[str, Any]) -> dict[str, Any]:
    runtime = load_piserver_runtime_config()
    settings = custom_settings if isinstance(custom_settings, dict) else {}
    runtime_cfg = settings.get('runtime') if isinstance(settings.get('runtime'), dict) else {}

    if isinstance(settings.get('camera'), dict):
        runtime['camera'] = copy.deepcopy(settings['camera'])
    if isinstance(settings.get('motor'), dict):
        runtime['motor'] = copy.deepcopy(settings['motor'])
    if 'steer_mix' in runtime_cfg:
        runtime['steer_mix'] = runtime_cfg.get('steer_mix')

    return save_piserver_runtime_config(runtime)
