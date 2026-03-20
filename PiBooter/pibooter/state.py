from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any


class RuntimeState:
    def __init__(self, log_limit: int = 200):
        self._lock = threading.RLock()
        self._log_limit = max(20, int(log_limit))
        self._status: dict[str, Any] = {
            "phase": "starting",
            "message": "PiBooter is starting.",
            "last_error": "",
            "connection_attempt": None,
            "network": {},
            "scan_results": [],
            "known_connections": [],
            "hotspot": {},
            "primary_ip": "",
            "active_connection": "",
            "hotspot_clients": [],
            "last_status": {},
            "session_active": False,
            "session_source": "",
            "session_started_at": 0.0,
            "startup_wait_s": 0,
            "startup_remaining_s": 0,
            "shutdown_reason": "",
            "should_exit": False,
            "updated_at": time.time(),
        }
        self._logs: list[dict[str, Any]] = []

    def set_log_limit(self, limit: int) -> None:
        with self._lock:
            self._log_limit = max(20, int(limit))
            self._logs = self._logs[-self._log_limit :]

    def log(self, message: str, level: str = "info") -> None:
        entry = {
            "ts": time.time(),
            "level": str(level or "info"),
            "message": str(message or ""),
        }
        with self._lock:
            self._logs.append(entry)
            self._logs = self._logs[-self._log_limit :]
            self._status["updated_at"] = time.time()

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                self._status[key] = deepcopy(value)
            self._status["updated_at"] = time.time()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = deepcopy(self._status)
            data["logs"] = deepcopy(self._logs)
            return data
