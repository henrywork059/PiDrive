from __future__ import annotations

import math
from typing import Any


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def parse_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return parsed


def clamp_float(value: Any, minimum: float, maximum: float, default: float = 0.0) -> float:
    parsed = parse_float(value, default)
    return max(minimum, min(maximum, parsed))


def clamp_int(value: Any, minimum: int, maximum: int, default: int = 0) -> int:
    parsed = parse_int(value, default)
    return max(minimum, min(maximum, parsed))


def normalize_direction(value: Any, default: int = 1) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return -1 if parsed < 0 else 1
