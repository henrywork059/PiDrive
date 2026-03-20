from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "active_algorithm": "manual",
    "max_throttle": 0.55,
    "steer_mix": 0.5,
    "current_page": "manual",
    "camera": {
        "width": 426,
        "height": 240,
        "fps": 30,
        "format": "BGR888",
        "preview_fps": 12,
        "preview_quality": 60,
        "stream_quality": "balanced",
        "auto_exposure": True,
        "exposure_us": 12000,
        "analogue_gain": 1.0,
        "exposure_compensation": 0.0,
        "auto_white_balance": True,
        "brightness": 0.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "sharpness": 1.0,
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
}


class ConfigStore:
    def __init__(self, path: str | Path, defaults: dict[str, Any] | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.defaults = deepcopy(defaults) if isinstance(defaults, dict) else deepcopy(DEFAULT_CONFIG)

    def _deep_merge(self, base: Any, override: Any) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            merged = {key: deepcopy(value) for key, value in base.items()}
            for key, value in override.items():
                merged[key] = self._deep_merge(merged.get(key), value)
            return merged
        return deepcopy(override)

    def normalize(self, data: dict | None) -> dict:
        payload = data if isinstance(data, dict) else {}
        return self._deep_merge(self.defaults, payload)

    def load_raw(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def load(self) -> dict:
        return self.normalize(self.load_raw())

    def save(self, data: dict) -> dict:
        payload = self.normalize(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.path)
        return payload

    def merge_save(self, data: dict | None) -> dict:
        merged = self._deep_merge(self.load_raw(), data if isinstance(data, dict) else {})
        return self.save(merged)
