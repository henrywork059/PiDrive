from __future__ import annotations

from typing import Any

from pisd.core.value_utils import clamp_float


def apply_ai_safety(raw_steering: Any, raw_throttle: Any, settings: dict[str, Any] | None, previous_safe: dict[str, Any] | None = None) -> dict[str, float]:
    """Clamp/smooth AI commands before they are shown or sent to motors."""
    cfg = dict(settings or {})
    previous = dict(previous_safe or {})
    steering = clamp_float(raw_steering, -1.0, 1.0, 0.0)
    throttle = clamp_float(raw_throttle, -1.0, 1.0, 0.0)
    max_steering = clamp_float(cfg.get("max_steering", 0.70), 0.0, 1.0, 0.70)
    max_throttle = clamp_float(cfg.get("max_throttle", 0.22), 0.0, 1.0, 0.22)
    fixed_throttle = clamp_float(cfg.get("fixed_throttle", 0.16), 0.0, 1.0, 0.16)
    if cfg.get("output_mode") == "steering_only":
        throttle = fixed_throttle
    steering = max(-max_steering, min(max_steering, steering))
    throttle = max(-max_throttle, min(max_throttle, throttle))
    steer_alpha = clamp_float(cfg.get("steering_smoothing", 0.35), 0.0, 1.0, 0.35)
    throttle_alpha = clamp_float(cfg.get("throttle_smoothing", 0.25), 0.0, 1.0, 0.25)
    previous_steering = clamp_float(previous.get("steering", 0.0), -1.0, 1.0, 0.0)
    previous_throttle = clamp_float(previous.get("throttle", 0.0), -1.0, 1.0, 0.0)
    steering = previous_steering + (steering - previous_steering) * (1.0 - steer_alpha)
    throttle = previous_throttle + (throttle - previous_throttle) * (1.0 - throttle_alpha)
    return {
        "steering": float(max(-max_steering, min(max_steering, steering))),
        "throttle": float(max(-max_throttle, min(max_throttle, throttle))),
    }
