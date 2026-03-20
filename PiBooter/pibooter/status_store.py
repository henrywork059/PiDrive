from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LAST_STATUS: dict[str, Any] = {
    "last_ssid": "",
    "last_known_ip": "",
    "last_gateway_ip": "",
    "hostname": "",
    "updated_at": "",
    "note": "",
}


class LastStatusStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data = self.load()

    def load(self) -> dict[str, Any]:
        data = deepcopy(DEFAULT_LAST_STATUS)
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = None
            if isinstance(loaded, dict):
                for key in data:
                    value = loaded.get(key, data[key])
                    data[key] = "" if value is None else str(value)
        self._data = data
        self._write(data)
        return deepcopy(self._data)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = deepcopy(DEFAULT_LAST_STATUS)
        for key in data:
            value = payload.get(key, data[key]) if isinstance(payload, dict) else data[key]
            data[key] = "" if value is None else str(value)
        if not data.get("updated_at"):
            data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._data = data
        self._write(data)
        return deepcopy(self._data)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._data)

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
