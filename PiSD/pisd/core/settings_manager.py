from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from pisd.core.errors import ErrorReporter, PiSDErrorCodes
# PiSD_0_4_1 cleanup: ok_payload/report_payload were imported here by an older settings API draft,
# but SettingsManager does not build HTTP payloads directly. Keep them unused/commented out rather
# than deleting the history of that planned path.
# from pisd.core.errors import ok_payload, report_payload
from pisd.core.presentation_registry import PRESENTATION_DEFAULTS

DEFAULT_RUNTIME_SETTINGS: dict[str, Any] = {
    "camera": {},
    "motor": {},
    "manual_drive": {
        "speed": 0.18,
        "max_speed_limit": 1.0,
        "drag_send_interval_ms": 90,
        "preview_mode": "live",
        "recording_fps": 6.0,
        "overlay": {
            "enabled": True,
            # PiSD_0_8_9: reduced Manual Drive overlay calibration controls. These are
            # the only user-facing/persisted visual controls; the renderer keeps
            # internal geometry constants for stability.
            "turn_rate_visual_scale": 2.2,
            "path_length_scale": 1.0,
            "path_width_scale": 0.34,
            "base_y": 96,
            "horizon_y": 31,
            "perspective_scale": 64,
            "opacity": 0.94,
        },
    },
    "ai_mode": {
        "model_id": "",
        "max_throttle": 0.22,
        "max_steering": 0.70,
        "fixed_throttle": 0.16,
        "steering_smoothing": 0.35,
        "throttle_smoothing": 0.25,
        "update_hz": 8.0,
        "command_timeout_s": 0.75,
        "output_mode": "steering_and_throttle",
        "preview_only_by_default": True,
        "motor_output_enabled": False,
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
        "ai_mode": "AI drive page defaults, model selection, prediction rate, and motor safety limits.",
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


    def _looks_like_old_awb_auto_camera_default(self, camera: dict[str, Any]) -> bool:
        """Return true only for the old uncustomised 0.5.x camera profile.

        PiSD_0_5_6 changes the OV5647 default to the tested 03/91-style
        locked-AWB visual profile. Existing runtime_settings.json files should
        inherit that only when they still look like the old stock AWB-auto
        default. User-chosen profiles such as daylight/tungsten/manual gains
        are intentionally preserved.
        """
        def _s(key: str, default: str = "") -> str:
            return str(camera.get(key, default) or default).strip().lower()

        def _f(key: str, default: float) -> float:
            try:
                return float(camera.get(key, default))
            except Exception:
                return default

        def _b(key: str, default: bool) -> bool:
            value = camera.get(key, default)
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"true", "1", "yes", "on"}

        return (
            _s("capture_source", "request") == "request"
            and _s("array_color_order", "rgb") == "rgb"
            and _s("format", "bgr888") == "bgr888"
            and _b("auto_white_balance", True) is True
            and _s("awb_mode", "auto") == "auto"
            and abs(_f("colour_gains_red", 0.0)) < 1e-9
            and abs(_f("colour_gains_blue", 0.0)) < 1e-9
            and _f("awb_settle_seconds", 0.5) <= 0.5
            and abs(_f("brightness", 0.0)) < 1e-9
            and abs(_f("contrast", 1.0) - 1.0) < 1e-9
            and abs(_f("saturation", 1.0) - 1.0) < 1e-9
        )

    def _apply_camera_default_profile_migration(self, camera: dict[str, Any]) -> None:
        if not isinstance(camera, dict):
            return
        if self._looks_like_old_awb_auto_camera_default(camera):
            camera["capture_source"] = "request"
            camera["array_color_order"] = "rgb"
            camera["format"] = "BGR888"
            camera["auto_white_balance"] = False
            camera["awb_mode"] = "auto"
            camera["colour_gains_red"] = 0.0
            camera["colour_gains_blue"] = 0.0
            camera["awb_settle_seconds"] = 1.0
            camera["brightness"] = 0.0
            camera["contrast"] = 1.0
            camera["saturation"] = 1.0

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

        # PiSD_0_5_6: migrate only the old uncustomised AWB-auto camera default
        # to the OV5647 03/91-style locked-AWB profile. This prevents existing
        # runtime_settings.json files from keeping the old red-prone default,
        # while preserving user-chosen camera profiles.
        camera = merged.setdefault("camera", {})
        self._apply_camera_default_profile_migration(camera)

        # Clamp persisted motor limits as settings are loaded, not only when the
        # MotorService receives them. Older runtime_settings.json files are normalised here before
        # the UI/service uses them, so stale or invalid values cannot break
        # runtime behaviour.
        motor = merged.setdefault("motor", {})
        for key in ("left_max_speed", "right_max_speed"):
            try:
                motor[key] = max(0.0, min(1.0, float(motor.get(key, self.defaults.get("motor", {}).get(key, 1.0)))))
            except Exception:
                motor[key] = self.defaults.get("motor", {}).get(key, 1.0)
        for key in ("left_bias", "right_bias"):
            try:
                motor[key] = max(-0.35, min(0.35, float(motor.get(key, self.defaults.get("motor", {}).get(key, 0.0)))))
            except Exception:
                motor[key] = self.defaults.get("motor", {}).get(key, 0.0)
        try:
            motor["steer_mix"] = max(0.0, min(1.0, float(motor.get("steer_mix", self.defaults.get("motor", {}).get("steer_mix", 1.0)))))
        except Exception:
            motor["steer_mix"] = self.defaults.get("motor", {}).get("steer_mix", 1.0)
        motor_defaults = self.defaults.get("motor", {})
        # PiSD_0_8_2: remove legacy turn_gain and turn_curve from persisted runtime state.
        # Existing files may still contain them, but steering X is now linear and
        # these keys should not affect motors or be surfaced back to the UI.
        motor.pop("turn_gain", None)
        motor.pop("turn_curve", None)
        steering_mode = str(motor.get("steering_mode", motor_defaults.get("steering_mode", "turn_rate")) or "turn_rate").strip().lower()
        motor["steering_mode"] = steering_mode if steering_mode in {"turn_rate", "arcade_mix"} else motor_defaults.get("steering_mode", "turn_rate")
        for key, lower, upper, default in (
            ("min_inside_speed", 0.0, 0.95, motor_defaults.get("min_inside_speed", 0.0)),
            ("start_deadzone", 0.0, 0.95, motor_defaults.get("start_deadzone", 0.0)),
            ("start_kick_seconds", 0.0, 0.75, motor_defaults.get("start_kick_seconds", 0.12)),
        ):
            try:
                motor[key] = max(lower, min(upper, float(motor.get(key, default))))
            except Exception:
                motor[key] = default
        motor["allow_pivot_turn"] = str(motor.get("allow_pivot_turn", motor_defaults.get("allow_pivot_turn", False))).lower() in {"true", "1", "yes", "on"}

        manual = merged.setdefault("manual_drive", {})
        # PiSD_0_8_4: manual steering X is now always direct/linear.
        # Legacy saved steer_strength is ignored and removed from normalised settings.
        manual.pop("steer_strength", None)
        try:
            manual["speed"] = max(0.0, min(1.0, float(manual.get("speed", self.defaults["manual_drive"].get("speed", 0.18)))))
        except Exception:
            manual["speed"] = self.defaults["manual_drive"].get("speed", 0.18)
        try:
            manual["max_speed_limit"] = max(0.1, min(1.0, float(manual.get("max_speed_limit", 1.0))))
        except Exception:
            manual["max_speed_limit"] = 1.0
        try:
            manual["drag_send_interval_ms"] = max(40, min(500, int(float(manual.get("drag_send_interval_ms", 90)))))
        except Exception:
            manual["drag_send_interval_ms"] = 90
        try:
            manual["recording_fps"] = max(0.2, min(30.0, float(manual.get("recording_fps", self.defaults["manual_drive"].get("recording_fps", 6.0)))))
        except Exception:
            manual["recording_fps"] = self.defaults["manual_drive"].get("recording_fps", 6.0)

        # PiSD_0_8_9: Manual Drive overlay calibration is intentionally small and bounded.
        # Older runtime files may contain many legacy/internal visual keys. Keep
        # compatibility by reading them when useful, but save back only the seven
        # user-facing visual controls plus the enabled flag.
        overlay_defaults = self.defaults["manual_drive"].get("overlay", {})
        overlay_source = manual.get("overlay") if isinstance(manual.get("overlay"), dict) else {}
        overlay: dict[str, Any] = {}
        overlay["enabled"] = str(overlay_source.get("enabled", overlay_defaults.get("enabled", True))).lower() not in {"false", "0", "no", "off"}
        legacy_tightness = overlay_source.get("turn_rate_visual_scale")
        if legacy_tightness is None and "curve_strength" in overlay_source:
            try:
                legacy_tightness = float(overlay_source.get("curve_strength", 3.35)) / 3.35 * float(overlay_defaults.get("turn_rate_visual_scale", 2.2))
            except Exception:
                legacy_tightness = overlay_defaults.get("turn_rate_visual_scale", 2.2)
        overlay_limits = {
            "turn_rate_visual_scale": (0.10, 6.00),
            "path_length_scale": (0.35, 2.50),
            "path_width_scale": (0.05, 1.20),
            "base_y": (55.0, 115.0),
            "horizon_y": (5.0, 80.0),
            "perspective_scale": (0.0, 140.0),
            "opacity": (0.05, 1.0),
        }
        for key, default in overlay_defaults.items():
            if key == "enabled":
                continue
            raw_value = legacy_tightness if key == "turn_rate_visual_scale" and legacy_tightness is not None else overlay_source.get(key, default)
            try:
                value = float(raw_value)
            except Exception:
                value = float(default)
            lower, upper = overlay_limits.get(key, (-1e9, 1e9))
            overlay[key] = max(lower, min(upper, value))
        if overlay.get("base_y", 96.0) <= overlay.get("horizon_y", 31.0) + 6.0:
            overlay["base_y"] = min(overlay_limits["base_y"][1], overlay.get("horizon_y", 31.0) + 6.0)
        manual["overlay"] = overlay

        ai = merged.setdefault("ai_mode", {})
        ai_defaults = self.defaults.get("ai_mode", {})
        ai["model_id"] = str(ai.get("model_id", ai_defaults.get("model_id", "")) or "").strip().replace("\\", "/")
        if ai["model_id"].startswith("/") or ".." in ai["model_id"].split("/"):
            ai["model_id"] = ""
        for key, lower, upper, default in (
            ("max_throttle", 0.0, 1.0, ai_defaults.get("max_throttle", 0.22)),
            ("max_steering", 0.0, 1.0, ai_defaults.get("max_steering", 0.70)),
            ("fixed_throttle", 0.0, 1.0, ai_defaults.get("fixed_throttle", 0.16)),
            ("steering_smoothing", 0.0, 1.0, ai_defaults.get("steering_smoothing", 0.35)),
            ("throttle_smoothing", 0.0, 1.0, ai_defaults.get("throttle_smoothing", 0.25)),
            ("update_hz", 1.0, 20.0, ai_defaults.get("update_hz", 8.0)),
            ("command_timeout_s", 0.2, 3.0, ai_defaults.get("command_timeout_s", 0.75)),
        ):
            try:
                ai[key] = max(lower, min(upper, float(ai.get(key, default))))
            except Exception:
                ai[key] = default
        if ai.get("output_mode") not in {"steering_only", "steering_and_throttle"}:
            ai["output_mode"] = ai_defaults.get("output_mode", "steering_and_throttle")
        ai["preview_only_by_default"] = str(ai.get("preview_only_by_default", ai_defaults.get("preview_only_by_default", True))).lower() not in {"false", "0", "no", "off"}
        # PiSD_0_5_12: motor_output_enabled is a live/session safety checkbox, not a persistent setting.
        ai["motor_output_enabled"] = False
        return merged
