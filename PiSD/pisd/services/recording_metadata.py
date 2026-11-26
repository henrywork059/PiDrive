"""Pure recording metadata normalization; no file, thread, camera or motor access."""
from __future__ import annotations

import math
from typing import Any
from pisd.core.value_utils import clamp_float

OVERLAY_SCHEMA_VERSION = "PiSD_0_8_8_overlay_settings_v2"
OVERLAY_REDUCED_KEYS = {
    "enabled",
    "turn_rate_visual_scale",
    "path_length_scale",
    "path_width_scale",
    "base_y",
    "horizon_y",
    "perspective_scale",
    "opacity",
}
OVERLAY_SETTINGS_FILENAME = "overlay_settings.json"
OVERLAY_SETTINGS_HISTORY_FILENAME = "overlay_settings_history.jsonl"

def _safe_label(value: Any, default: str = "manual") -> str:
    text = str(value or default).strip().lower()
    allowed = []
    for char in text:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    cleaned = "".join(allowed).strip("_")
    return cleaned[:48] or default


def _normalise_command_source(value: Any, label: Any = "") -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if raw in {"ai", "ai_output", "ai_safe", "ai_safe_command", "model", "model_output"}:
        return "ai_safe_command"
    if raw in {"manual", "manual_command", "motor", "motor_command"}:
        return "manual_command"
    label_text = str(label or "").strip().lower()
    if label_text.startswith("ai_mode") or label_text.startswith("ai_"):
        return "ai_safe_command"
    return "manual_command"


def _command_dict(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {"steering": 0.0, "throttle": 0.0}
    return {
        "steering": float(clamp_float(value.get("steering", 0.0), -1.0, 1.0, 0.0)),
        "throttle": float(clamp_float(value.get("throttle", 0.0), -1.0, 1.0, 0.0)),
    }


def json_safe_overlay_settings(value: Any) -> dict[str, Any]:
    """Return the reduced Manual Drive overlay metadata snapshot.

    Overlay settings are visual/training metadata, not motor-safety inputs.
    PiSD 0.8.8 records only the seven user-facing visual controls plus the
    enabled flag. Older advanced/internal keys are pruned so recordings and
    trainer labels do not keep carrying the old oversized overlay schema.
    """
    if not isinstance(value, dict):
        return {}
    source = dict(value)
    if "turn_rate_visual_scale" not in source and "curve_strength" in source:
        try:
            source["turn_rate_visual_scale"] = float(source.get("curve_strength", 3.35)) / 3.35 * 2.2
        except Exception:
            source["turn_rate_visual_scale"] = 2.2
    cleaned: dict[str, Any] = {}
    for key in (
        "enabled",
        "turn_rate_visual_scale",
        "path_length_scale",
        "path_width_scale",
        "base_y",
        "horizon_y",
        "perspective_scale",
        "opacity",
    ):
        if key not in source:
            continue
        item = source[key]
        if key == "enabled":
            cleaned[key] = str(item).lower() not in {"false", "0", "no", "off"}
        elif isinstance(item, (int, float)) and math.isfinite(float(item)):
            cleaned[key] = item
        else:
            try:
                numeric = float(item)
                if math.isfinite(numeric):
                    cleaned[key] = numeric
            except Exception:
                continue
    return cleaned

