from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from pisd.core.errors import ErrorReporter, PiSDErrorCodes, ok_payload, report_payload
from pisd.core.presentation_registry import PRESENTATION_DEFAULTS

DEFAULT_RUNTIME_SETTINGS: dict[str, Any] = {
    "camera": {},
    "motor": {},
    "manual_drive": {
        "speed": 0.18,
        "max_speed_limit": 0.65,
        "steer_strength": 0.35,
        "drag_send_interval_ms": 90,
        "preview_mode": "live",
        "recording_fps": 6.0,
    },
    "panel_presentation": copy.deepcopy(PRESENTATION_DEFAULTS),
    "safety": {
        "motor_output_locked_by_default": True,
        "require_wheels_lifted_ack": True,
    },
    "ui": {
        "compact_headers": True,
        "show_page_subtitles": False,
    },
}

SETTINGS_SCHEMA: dict[str, Any] = {
    "groups": {
        "camera": "Camera runtime settings passed to CameraService.apply_settings.",
        "motor": "Motor runtime settings passed to MotorService.apply_settings.",
        "manual_drive": "Manual drive page defaults and drag-pad behaviour.",
        "panel_presentation": "Shared visual style, adaptive panel sizing, and role-based horizontal/vertical panel weights used by all browser pages.",
        "safety": "Safety defaults used by GUI pages.",
        "ui": "Global UI density/header behaviour.",
    },
    "allowed_top_level_keys": list(DEFAULT_RUNTIME_SETTINGS.keys()),
}


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class SettingsManager:
    """Small JSON-backed runtime settings store.

    The manager intentionally keeps user runtime settings in config/runtime_settings.json
    instead of rewriting config/defaults.json. Unknown nested service keys are preserved so
    future camera/motor settings can be added without breaking older files.
    """

    def __init__(self, path: Path, defaults: dict[str, Any] | None = None):
        self.path = Path(path)
        defaults = defaults or {}
        self.defaults = deep_merge(DEFAULT_RUNTIME_SETTINGS, {
            "camera": defaults.get("camera", {}),
            "motor": defaults.get("motor", {}),
        })
        self.errors = ErrorReporter("settings")
        self._lock = RLock()
        self._settings = copy.deepcopy(self.defaults)
        self.load()

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                if not self.path.exists():
                    self._settings = copy.deepcopy(self.defaults)
                    return self.get()
                with self.path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict):
                    self.errors.report(PiSDErrorCodes.SETTINGS_LOAD_FAILED, "runtime_settings.json did not contain an object; defaults loaded.", context={"path": str(self.path)})
                    self._settings = copy.deepcopy(self.defaults)
                    return self.get()
                self._settings = self._normalise(data)
                return self.get()
            except Exception as exc:
                self.errors.report(PiSDErrorCodes.SETTINGS_LOAD_FAILED, f"Failed to load runtime settings: {exc}", context={"path": str(self.path)}, exc=exc)
                self._settings = copy.deepcopy(self.defaults)
                return self.get()

    def get(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._settings)

    def schema(self) -> dict[str, Any]:
        return copy.deepcopy(SETTINGS_SCHEMA)

    def save(self, partial: dict[str, Any]) -> tuple[bool, dict[str, Any], Any | None]:
        if not isinstance(partial, dict):
            report = self.errors.report(PiSDErrorCodes.SETTINGS_INVALID_PAYLOAD, "Settings payload must be a JSON object.")
            return False, self.get(), report
        unknown = sorted(set(partial) - set(DEFAULT_RUNTIME_SETTINGS))
        if unknown:
            report = self.errors.report(PiSDErrorCodes.SETTINGS_INVALID_PAYLOAD, f"Unknown settings group(s): {', '.join(unknown)}", context={"unknown": unknown})
            return False, self.get(), report
        with self._lock:
            self._settings = self._normalise(deep_merge(self._settings, partial))
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                with tmp.open("w", encoding="utf-8") as handle:
                    json.dump(self._settings, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                tmp.replace(self.path)
                return True, self.get(), None
            except Exception as exc:
                report = self.errors.report(PiSDErrorCodes.SETTINGS_SAVE_FAILED, f"Failed to save runtime settings: {exc}", context={"path": str(self.path)}, exc=exc)
                return False, self.get(), report

    def reset(self) -> tuple[bool, dict[str, Any], Any | None]:
        with self._lock:
            self._settings = copy.deepcopy(self.defaults)
        return self.save({})

    def _normalise(self, data: dict[str, Any]) -> dict[str, Any]:
        merged = deep_merge(self.defaults, data)
        panel = merged.setdefault("panel_presentation", {})
        for key in ("fontScale", "borderStrength", "shadowStrength", "panelPadding", "buttonScale"):
            if key in panel:
                try:
                    panel[key] = float(panel[key])
                except Exception:
                    panel[key] = self.defaults["panel_presentation"].get(key)
        for key in ("panelGap", "panelRadius", "minPanelWidth", "consoleHeight"):
            if key in panel:
                try:
                    panel[key] = int(float(panel[key]))
                except Exception:
                    panel[key] = self.defaults["panel_presentation"].get(key)
        for key in (
            "statusPanelHWeight", "statusPanelVWeight", "previewPanelHWeight", "previewPanelVWeight",
            "controlPanelHWeight", "controlPanelVWeight", "settingsPanelHWeight", "settingsPanelVWeight",
            "logPanelHWeight", "logPanelVWeight",
        ):
            if key in panel:
                try:
                    panel[key] = max(1, min(4, int(round(float(panel[key])))))
                except Exception:
                    panel[key] = self.defaults["panel_presentation"].get(key)
        if "adaptivePanels" in panel:
            panel["adaptivePanels"] = str(panel["adaptivePanels"]).lower() not in {"false", "0", "no", "off"}
        if "semanticLayoutLock" in panel:
            panel["semanticLayoutLock"] = str(panel["semanticLayoutLock"]).lower() not in {"false", "0", "no", "off"}
        if panel.get("layoutSystem") not in {"strict-responsive"}:
            panel["layoutSystem"] = "strict-responsive"
        if panel.get("previewPriority") not in {"fit-view", "balanced", "compact"}:
            panel["previewPriority"] = "fit-view"
        if panel.get("topbarMode") not in {"compact", "standard"}:
            panel["topbarMode"] = "compact"

        # Clamp persisted motor limits as settings are loaded, not only when the
        # MotorService receives them. Older runtime_settings.json files could
        # still contain 1.0, which made the Settings page show an unsafe value
        # even though the motor service later clamped it.
        motor = merged.setdefault("motor", {})
        for key in ("left_max_speed", "right_max_speed"):
            try:
                motor[key] = max(0.0, min(0.65, float(motor.get(key, self.defaults.get("motor", {}).get(key, 0.65)))))
            except Exception:
                motor[key] = self.defaults.get("motor", {}).get(key, 0.65)
        for key in ("left_bias", "right_bias"):
            try:
                motor[key] = max(-0.35, min(0.35, float(motor.get(key, self.defaults.get("motor", {}).get(key, 0.0)))))
            except Exception:
                motor[key] = self.defaults.get("motor", {}).get(key, 0.0)
        try:
            motor["steer_mix"] = max(0.0, min(1.0, float(motor.get("steer_mix", self.defaults.get("motor", {}).get("steer_mix", 1.0)))))
        except Exception:
            motor["steer_mix"] = self.defaults.get("motor", {}).get("steer_mix", 1.0)

        manual = merged.setdefault("manual_drive", {})
        for key in ("speed", "steer_strength"):
            try:
                upper = 0.65 if key == "speed" else 1.0
                manual[key] = max(0.0, min(upper, float(manual.get(key, self.defaults["manual_drive"][key]))))
            except Exception:
                manual[key] = self.defaults["manual_drive"][key]
        try:
            manual["max_speed_limit"] = max(0.1, min(0.65, float(manual.get("max_speed_limit", 0.65))))
        except Exception:
            manual["max_speed_limit"] = 0.65
        try:
            manual["drag_send_interval_ms"] = max(40, min(500, int(float(manual.get("drag_send_interval_ms", 90)))))
        except Exception:
            manual["drag_send_interval_ms"] = 90
        try:
            manual["recording_fps"] = max(0.2, min(30.0, float(manual.get("recording_fps", self.defaults["manual_drive"].get("recording_fps", 6.0)))))
        except Exception:
            manual["recording_fps"] = self.defaults["manual_drive"].get("recording_fps", 6.0)
        return merged
