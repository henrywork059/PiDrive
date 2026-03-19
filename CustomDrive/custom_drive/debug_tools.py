from __future__ import annotations

import time
from typing import Any


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {'1', 'true', 'yes', 'y', 'on'}:
            return True
        if text in {'0', 'false', 'no', 'n', 'off', ''}:
            return False
    return bool(default)


def clamp_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(value)
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(value)
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


def sanitize_label_name(value: Any, default: str) -> str:
    text = str(value or default).strip()
    return text or default


def append_event(
    buffer: list[dict[str, Any]],
    message: str,
    *,
    level: str = 'info',
    event_type: str = 'runtime',
    limit: int = 200,
    timestamp: float | None = None,
    **fields: Any,
) -> None:
    event: dict[str, Any] = {
        'timestamp': float(time.monotonic() if timestamp is None else timestamp),
        'level': str(level).lower(),
        'type': str(event_type),
        'message': str(message),
    }
    for key, value in fields.items():
        event[str(key)] = value
    buffer.append(event)
    trim_events(buffer, limit)


def trim_events(buffer: list[dict[str, Any]], limit: int = 200) -> list[dict[str, Any]]:
    if limit < 1:
        limit = 1
    if len(buffer) > limit:
        del buffer[:-limit]
    return buffer
