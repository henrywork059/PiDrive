from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

from piserver.core.config_recovery import ConfigRecovery


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
        "auto_white_balance": False,
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
        self._lock = RLock()
        self._recovery = ConfigRecovery(self.path)
        self._last_raw = {}
        self._load_failed = False

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

    def recovery_status(self) -> dict:
        with self._lock:
            return {**self._recovery.status(), "load_failed": self._load_failed}

    def _read_checked(self):
        raw = self._recovery.read()
        if raw is None:
            self._load_failed = False
            return None, {}
        try:
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Configuration must be an object.")
            for key in ("camera", "motor"):
                if key in data and not isinstance(data[key], dict):
                    raise ValueError("Invalid configuration group.")
        except (ValueError, TypeError):
            self._load_failed = True
            self._recovery.preserve(raw)
            return raw, None
        self._load_failed = False
        self._recovery.write_blocked = False
        return raw, data

    def load_raw(self) -> dict:
        with self._lock:
            try:
                _, data = self._read_checked()
                if data is not None:
                    self._last_raw = deepcopy(data)
            except OSError:
                self._load_failed = True
            return deepcopy(self._last_raw)

    def load(self) -> dict:
        return self.normalize(self.load_raw())

    def save(self, data: dict) -> dict:
        with self._lock:
            raw, existing = self._read_checked()
            # Preserve valid unknown keys omitted from the runtime snapshot.
            previous = self._last_raw if existing is None else existing
            payload = self.normalize(self._deep_merge(previous, data if isinstance(data, dict) else {}))
            self._recovery.write(
                (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), raw)
            self._last_raw = deepcopy(payload)
            self._load_failed = False
            return payload

    def merge_save(self, data: dict | None) -> dict:
        return self.save(data if isinstance(data, dict) else {})
