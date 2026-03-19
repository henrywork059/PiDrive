from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "CustomDrive" / "config" / "runtime_settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "camera": {
        "width": 426,
        "height": 240,
        "fps": 30,
        "preview_fps": 12,
        "preview_quality": 60,
        "stream_quality": "balanced",
    },
    "motor": {
        "left_direction": 1,
        "right_direction": 1,
        "steering_direction": 1,
        "left_max_speed": 1.0,
        "right_max_speed": 1.0,
        "left_bias": 0.0,
        "right_bias": 0.0,
    },
    "runtime": {
        "steer_mix": 0.75,
        "tick_s_live": 0.1,
        "tick_s_sim": 0.2,
        "allow_virtual_grab_without_arm": False,
    },
    "perception": {
        "enabled": True,
        "blur_kernel": 5,
        "open_iterations": 1,
        "close_iterations": 1,
        "min_box_area_ratio": 0.0025,
        "max_detections_per_label": 3,
        "labels": {
            "he3": {
                "ranges": [
                    {"lower": [5, 100, 90], "upper": [35, 255, 255]}
                ],
                "min_box_area_ratio": 0.0025,
            },
            "he3_zone": {
                "ranges": [
                    {"lower": [90, 80, 70], "upper": [135, 255, 255]}
                ],
                "min_box_area_ratio": 0.0040,
            },
        },
    },
}


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or SETTINGS_PATH
    if not cfg_path.exists():
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    return _deep_merge(json.loads(json.dumps(DEFAULT_SETTINGS)), raw)


def save_settings(data: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or SETTINGS_PATH
    merged = _deep_merge(json.loads(json.dumps(DEFAULT_SETTINGS)), data or {})
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return merged
