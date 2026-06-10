from __future__ import annotations

import time
from typing import Any

from pisd.core.value_utils import clamp_float


def manual_correction_status(
    settings: dict[str, Any] | None,
    manual: dict[str, Any] | None,
    updated_monotonic: Any = 0.0,
    *,
    now_monotonic: float | None = None,
) -> dict[str, Any]:
    """Return whether a manual correction vector is still active."""
    cfg = dict(settings or {})
    source = dict(manual or {})
    timeout_s = clamp_float(cfg.get("manual_correction_timeout_s", 0.75), 0.1, 3.0, 0.75)
    now = time.monotonic() if now_monotonic is None else float(now_monotonic)
    try:
        updated = float(updated_monotonic or 0.0)
    except Exception:
        updated = 0.0
    age_s = max(0.0, now - updated) if updated else None
    enabled = str(cfg.get("manual_correction_enabled", False)).lower() in {"true", "1", "yes", "on"}
    active = bool(enabled and age_s is not None and age_s <= timeout_s)
    result = {
        "enabled": enabled,
        "active": active,
        "mix_percent": clamp_float(cfg.get("manual_mix_percent", 50.0), 0.0, 100.0, 50.0),
        "age_s": age_s,
        "timeout_s": timeout_s,
        "source": str(source.get("source", ""))[:80],
        "updated_at_utc": str(source.get("updated_at_utc", "")),
        "steering": 0.0,
        "throttle": 0.0,
    }
    if active:
        result["steering"] = clamp_float(source.get("steering", 0.0), -1.0, 1.0, 0.0)
        result["throttle"] = clamp_float(source.get("throttle", 0.0), -1.0, 1.0, 0.0)
    return result


def apply_additive_manual_correction(
    model_steering: Any,
    model_throttle: Any,
    settings: dict[str, Any] | None,
    manual_status: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply PiSD's additive correction equation: AI + manual * correction %."""
    cfg = dict(settings or {})
    manual = dict(manual_status or {})
    model_s = clamp_float(model_steering, -1.0, 1.0, 0.0)
    model_t = clamp_float(model_throttle, -1.0, 1.0, 0.0)
    correction_gain = clamp_float(cfg.get("manual_mix_percent", manual.get("mix_percent", 50.0)), 0.0, 100.0, 50.0) / 100.0 if manual.get("active") else 0.0
    manual_s = clamp_float(manual.get("steering", 0.0), -1.0, 1.0, 0.0)
    manual_t = clamp_float(manual.get("throttle", 0.0), -1.0, 1.0, 0.0)
    corrected_s = clamp_float(model_s + manual_s * correction_gain, -1.0, 1.0, 0.0)
    corrected_t = clamp_float(model_t + manual_t * correction_gain, -1.0, 1.0, 0.0)
    return {
        "steering": float(corrected_s),
        "throttle": float(corrected_t),
        "manual_weight": float(correction_gain),
        "correction_gain": float(correction_gain),
        "manual_active": bool(manual.get("active")),
        "equation": "ai + manual * correction_gain",
    }
