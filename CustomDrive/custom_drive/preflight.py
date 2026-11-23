"""R48 CustomDrive GUI and Mission 1 passive preflight summaries.

The two apps share only this component-local pure formatter. Calling this
module never starts a camera, detector, GPIO motor, servo or mission; never
touches persistent settings; and makes no outbound network connection.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_GIB = 1024 ** 3


def _item(key: str, title: str, state: str, detail: str, next_step: str) -> dict[str, str]:
    return {"key": key, "title": title, "state": state, "detail": detail, "next_step": next_step}


def disk_check(project_root: Path) -> dict[str, str]:
    try:
        usage = shutil.disk_usage(project_root)
        free, total = int(usage.free), int(usage.total)
        if total <= 0:
            raise OSError("invalid capacity")
    except (OSError, ValueError):
        return _item("disk", "Disk space", "unknown",
                     "Disk capacity unavailable; no files or settings were changed.",
                     "Check disk space on the Pi before recording.")
    low = free < _GIB or free / total < 0.05
    return _item("disk", "Disk space", "attention" if low else "ready",
                 f"{free / _GIB:.1f} GiB free ({free / total:.0%} of volume).",
                 "Free space before starting a mission/recording." if low
                 else "No action required.")


def _common_result(component: str, mode: str, checks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "ok": True, "read_only": True, "component": component, "mode": mode,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "note": "Passive inspection only. No camera, motor, servo, inference, network probe or settings mutation.",
    }


def _motor_row(motor: dict[str, Any], safety: dict[str, Any]) -> dict[str, str]:
    hardware = motor.get("gpio_available") is True
    latched = safety.get("latched") is True
    return _item(
        "motor", "Motor adapter", "attention" if latched else ("ready" if hardware else "simulation"),
        "Safety STOP latched; movement disabled." if latched else
        "GPIO adapter available; motor outputs not tested." if hardware else
        "Simulation adapter (no GPIO motor outputs).",
        "Inspect the fault and explicitly rearm when safe." if latched else
        "Secure the vehicle before any physical motor test." if hardware else
        "Run on a Pi with a supported GPIO adapter for physical driving.",
    )


def _arm_row(arm: dict[str, Any]) -> dict[str, str]:
    enabled = arm.get("enabled") is True
    available = arm.get("available") is True
    simulated = arm.get("simulated") is True
    if not enabled:
        return _item("arm", "Arm adapter", "attention", "Arm is disabled by configuration.",
                     "Enable arm only after checking servo wiring.")
    if simulated:
        return _item("arm", "Arm adapter", "simulation", "Simulated servo backend; no physical arm motion.",
                     "Use a supported Pi servo backend for a real arm.")
    if not available:
        return _item("arm", "Arm adapter", "attention", "Real arm backend unavailable; no servo test attempted.",
                     "Check power, I2C and servo backend status.")
    return _item("arm", "Arm adapter", "ready",
                 "Real arm backend reported available; servo movement not tested.",
                 "Check safe pose and clearance before moving the arm.")


def _network_row() -> dict[str, str]:
    return _item("network", "Network", "ready",
                 "This browser reached the CustomDrive server by HTTP; no internet/Wi-Fi probe.",
                 "Check PiBooter/network setup if remote clients cannot connect.")


def build_gui_preflight(
    *,
    camera: dict[str, Any], motor: dict[str, Any],
    ai: dict[str, Any], arm: dict[str, Any],
    safety: dict[str, Any], project_root: Path,
) -> dict[str, Any]:
    backend = str(camera.get("backend") or "").lower()
    camera_real = backend in {"picamera2", "opencv"}
    gpio = motor.get("gpio_available") is True
    ai_backend = str(ai.get("backend") or "").lower()
    ai_ready = ai.get("ready") is True
    ai_color = ai_backend == "color"
    checks = [
        _item("mode", "Service mode", "ready" if gpio else "simulation",
              "Real GPIO adapter detected; this does not authorize or test movement." if gpio
              else "Simulation/no GPIO adapter; no real motor output.",
              "Check adapter details below before driving."),
        _item("camera", "Camera", "ready" if camera_real else "attention",
              "Hardware camera backend recognized; fresh frames not verified." if camera_real
              else "Placeholder camera or no hardware backend.",
              "Use camera preview to verify fresh frames." if camera_real
              else "Check camera connection and PiServer camera logs."),
        _item("model", "AI model", "ready" if ai_ready or ai_color else "attention",
              "Object detection backend reports ready; no inference run." if ai_ready
              else "Color detection selected; TFLite model not required." if ai_color
              else "No ready TFLite deployment; AI detection may be unavailable.",
              "Inspect AI overlay before acting." if ai_ready
              else "Deploy a compatible model for TFLite detection." if not ai_color
              else "Switch to TFLite only when a model is available."),
        _motor_row(motor, safety),
        _arm_row(arm),
        disk_check(project_root),
        _network_row(),
    ]
    return _common_result("CustomDrive GUI", "hardware-adapter" if gpio else "simulation", checks)


def build_mission1_preflight(
    *,
    camera: dict[str, Any] | None, motor: dict[str, Any],
    model_selected: bool, model_loaded: bool,
    arm: dict[str, Any], safety: dict[str, Any],
    mission_running: bool, project_root: Path,
) -> dict[str, Any]:
    # No attempt to create/start the camera. Mission 1 may intentionally leave
    # camera_service = None until the route stage has completed.
    cam_backend = str((camera or {}).get("backend") or "").lower()
    cam_real = cam_backend in {"picamera2", "opencv"}
    gpio = motor.get("gpio_available") is True
    checks = [
        _item("mode", "Service mode", "ready" if gpio else "simulation",
              "Mission 1 on a GPIO-capable Pi; no motion test performed." if gpio
              else "Simulation/no GPIO adapter. Mission may not drive physical motors.",
              "Review safety and hardware before pressing Start."),
        _item("camera", "Camera", "ready" if cam_real else "attention",
              "Camera service exists; freshness not tested." if cam_real else
              "Camera not started yet (expected before route completion)." if camera is None
              else "Camera has no live hardware backend.",
              "Camera starts at the configured stage; check live frame then."
              if camera is None else "Inspect the live annotated frame."),
        _item("model", "AI model", "ready" if model_loaded else "attention",
              "Mission AI model already loaded; inference not tested." if model_loaded
              else "Model selected for next mission stage; not loaded yet." if model_selected
              else "No Mission 1 model selected. Detection stage will be unavailable.",
              "Check model detections after the route." if model_selected or model_loaded
              else "Upload/select a compatible Mission 1 TFLite model."),
        _motor_row(motor, safety),
        _arm_row(arm),
        disk_check(project_root),
        _network_row(),
    ]
    return _common_result("CustomDrive Mission 1",
                          "running" if mission_running else
                          "hardware-adapter" if gpio else "simulation", checks)
