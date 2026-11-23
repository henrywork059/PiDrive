"""R49 bounded on-device operator events; no user payloads or cloud output.

Only predefined operation identifiers are accepted. Entries contain a UTC
timestamp, allowlisted category/action, and outcome. Never store passwords,
SSIDs, model filenames, filesystem paths, request URLs or exception details.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

OPERATIONS: dict[str, tuple[str, str]] = {
    "startup": ("runtime", "Service initialized"),
    "camera_preview": ("camera", "Camera preview selection"),
    "camera_apply": ("camera", "Camera settings Apply"),
    "motor_apply": ("motor", "Motor settings Apply"),
    "config_save": ("settings", "Settings Save"),
    "config_reload": ("settings", "Settings Reload"),
    "record_toggle": ("recording", "Recording toggled"),
    "record_capture": ("recording", "Snapshot captured"),
    "record_delete": ("recording", "Recording deleted"),
    "model_upload": ("model", "Model upload"),
    "model_load": ("model", "Model load"),
    "model_delete": ("model", "Model deletion"),
    "model_deploy": ("model", "Model Deploy"),
    "model_undeploy": ("model", "Model stopped"),
    "model_select": ("model", "Model selection"),
    "safety_stop": ("safety", "Emergency STOP requested"),
    "safety_rearm": ("safety", "Safety rearm requested"),
    "mission_start": ("mission", "Mission Start requested"),
    "mission_stop": ("safety", "Mission STOP requested"),
    "mission_transition": ("mission", "Mission stage transition"),
    "arm_action": ("arm", "Arm action requested"),
    "arm_transition": ("arm", "Arm state transition"),
    "runtime_save": ("settings", "Runtime settings Save"),
    "other": ("runtime", "Operator action"),
}
_ALLOWED_OUTCOMES = frozenset({"succeeded", "failed", "partial", "observed"})
_MAX_LIMIT = 128


class RecentEventRing:
    """A thread-safe fixed-size ring. Does not persist data or spawn workers."""
    def __init__(self, capacity: int = _MAX_LIMIT):
        self.capacity = max(1, min(_MAX_LIMIT, int(capacity)))
        self._items: deque[dict[str, str]] = deque(maxlen=self.capacity)
        self._lock = threading.Lock()

    def record(self, operation: str, outcome: str = "observed") -> None:
        # Never let unsanitized messages become entries.
        key = operation if operation in OPERATIONS else "other"
        kind, title = OPERATIONS[key]
        if outcome not in _ALLOWED_OUTCOMES:
            outcome = "observed"
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "operation": key,
            "category": kind,
            "title": title,
            "outcome": outcome,
        }
        with self._lock:
            self._items.append(event)

    def snapshot(self, limit: int = 80) -> list[dict[str, str]]:
        cap = max(1, min(self.capacity, 80, int(limit)))
        with self._lock:
            return [dict(item) for item in list(self._items)[-cap:]]


def record_api_response(events: RecentEventRing, response: Any, request: Any,
                        routes: dict[str, str]) -> Any:
    """After-request hook: classification only, never read or log request body."""
    if request.method != "POST":
        return response
    # request.endpoint is controlled by server routes, not query/filename.
    operation = routes.get(request.endpoint)
    if operation is None:
        return response
    if operation == "safety_stop":
        # Only a strict literal bool selects the rearm classification.
        # The action remains independently governed by the original route.
        data = request.get_json(silent=True)
        if isinstance(data, dict) and data.get("enabled") is False:
            operation = "safety_rearm"
    payload = response.get_json(silent=True) if response.is_json else None
    failed = response.status_code >= 400 or (
        isinstance(payload, dict) and payload.get("ok") is False
    )
    partial = isinstance(payload, dict) and payload.get("saved") is False
    outcome = "failed" if failed else "partial" if partial else "succeeded"
    events.record(operation, outcome)
    return response
