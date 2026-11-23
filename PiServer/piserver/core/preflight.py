"""R48 passive readiness summary. Does not initialize hardware or write settings.

All inputs come from already-running services' read-only getters. The disk
probe reads filesystem metadata only. No sockets, internet probe, subprocess,
model loading, camera start or motor/servo command is performed.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_GIB = 1024 ** 3


def _check(key: str, title: str, state: str, detail: str, action: str) -> dict[str, str]:
    return {"key": key, "title": title, "state": state, "detail": detail, "next_step": action}


def disk_check(root: Path) -> dict[str, str]:
    """Read-only metadata query; return no absolute path or exception text."""
    try:
        usage = shutil.disk_usage(root)
        free = int(usage.free)
        total = int(usage.total)
        if total <= 0:
            raise OSError("invalid size")
    except (OSError, ValueError):
        return _check("disk", "Disk space", "unknown",
                      "Storage capacity could not be read.",
                      "Check free space on the Pi before recording.")
    free_gib = free / _GIB
    low = free < _GIB or free / total < 0.05
    return _check("disk", "Disk space", "attention" if low else "ready",
                  f"{free_gib:.1f} GiB available ({free / total:.0%} of volume).",
                  "Free disk space before recording." if low else "No action required.")


def build_preflight(
    *,
    camera: dict[str, Any],
    motor: dict[str, Any],
    model_active: bool,
    safety: dict[str, Any],
    disk_root: Path,
) -> dict[str, Any]:
    """No side effects beyond read-only disk_usage. Never return raw service errors."""
    camera_backend = str(camera.get("backend") or "").lower()
    camera_real = camera_backend in {"picamera2", "opencv"}
    gpio = motor.get("gpio_available") is True
    latched = safety.get("latched") is True
    simulated = not gpio
    mode = "hardware-adapter" if gpio else "simulation"
    checks = [
        _check("mode", "Service mode", "ready" if gpio else "simulation",
               "GPIO adapter available; this is not a motor output test." if gpio
               else "Simulation/no GPIO adapter. Commands cannot drive real motors.",
               "Check PiServer hardware adapter configuration." if not gpio else "No action required."),
        _check("camera", "Camera", "ready" if camera_real else "attention",
               ("Camera backend detected (" + camera_backend + "); frame freshness not proven."
                if camera_real else "No live hardware camera backend; placeholder or camera unavailable."),
               "Open live preview to verify fresh frames." if camera_real
               else "Check camera cable and startup logs; do not assume preview is live."),
        _check("model", "AI model", "ready" if model_active else "attention",
               "An AI model is selected; inference quality not verified." if model_active
               else "No active TFLite model; manual driving remains available.",
               "Check model compatibility before AI mode." if model_active
               else "Upload and load a compatible .tflite model."),
        _check("motor", "Motor adapter", "attention" if latched else ("ready" if gpio else "simulation"),
               "Safety STOP is latched; motor output disabled." if latched
               else ("GPIO adapter initialized by the main server; motor output not tested." if gpio
                     else "Simulation motor adapter; no GPIO output."),
               "Inspect and explicitly rearm safety only when safe." if latched
               else ("Use Motor Tuning only with the vehicle secured." if gpio
                     else "Run PiServer on a Pi with GPIO for physical driving.")),
        disk_check(disk_root),
        _check("network", "Network", "ready",
               "Browser HTTP request reached PiServer. Internet/Wi-Fi reachability not tested.",
               "If other devices cannot connect, check PiBooter/network settings."),
    ]
    return {
        "ok": True,
        "read_only": True,
        "component": "PiServer",
        "mode": mode,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "note": "Observation only. No motor, camera, network probe, model load or settings Apply.",
    }
