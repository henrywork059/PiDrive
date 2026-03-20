from __future__ import annotations

import math
from typing import Any


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def parse_finite_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return parsed if math.isfinite(parsed) else float(default)


def parse_clamped_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    return clamp_float(parse_finite_float(value, default), minimum, maximum)


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def parse_clamped_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, parse_int(value, default)))


def parse_bool_like(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off", ""}:
            return False
    return bool(default)


def normalize_direction(value: Any, default: int = 1) -> int:
    parsed = parse_int(value, default)
    return -1 if parsed < 0 else 1
