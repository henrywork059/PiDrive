"""R48 PiSD read-only preflight, using existing runtime service snapshots.

Does not call camera.start, motor.update/stop, AI load/infer, mkdir, DNS,
subprocess, save/reset config or any real network probe. The network row
only confirms that this already-served HTTP GET reached this process.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_GIB = 1024 ** 3


def _item(key: str, title: str, state: str, detail: str, next_step: str) -> dict[str, str]:
    return dict(key=key, title=title, state=state, detail=detail, next_step=next_step)


def disk_check(project_root: Path) -> dict[str, str]:
    try:
        usage = shutil.disk_usage(project_root)
        free, total = int(usage.free), int(usage.total)
        if total <= 0:
            raise OSError("invalid capacity")
    except (OSError, ValueError):
        return _item("disk", "Disk space", "unknown",
                     "Disk capacity unavailable; no storage changes made.",
                     "Check free space on the Pi before recording.")
    low = free < _GIB or free / total < 0.05
    return _item("disk", "Disk space", "attention" if low else "ready",
                 f"{free / _GIB:.1f} GiB available ({free / total:.0%} of volume).",
                 "Free space before recording." if low else "No action required.")


def build_preflight(
    *,
    hardware_requested: bool,
    camera: dict[str, Any],
    motor: dict[str, Any],
    ai: dict[str, Any],
    safety: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    cam_backend = str(camera.get("backend") or "").lower()
    cam_hw = camera.get("hardware_enabled") is True and cam_backend == "picamera2"
    cam_running = camera.get("running") is True
    motor_hw = motor.get("hardware_enabled") is True
    latched = safety.get("latched") is True
    model_ready = ai.get("model_loaded") is True and ai.get("model_ready") is True
    runtime = ai.get("runtime_support") if isinstance(ai.get("runtime_support"), dict) else {}
    tflite_available = runtime.get("tflite") is True
    mode = "hardware-requested" if hardware_requested else "simulation-requested"
    checks = [
        _item("mode", "Service mode",
              "ready" if hardware_requested and cam_hw and motor_hw else "simulation",
              ("Hardware requested and camera/GPIO adapters active; outputs not tested."
               if hardware_requested and cam_hw and motor_hw else
               "Hardware requested, but at least one adapter is simulated or unavailable."
               if hardware_requested else "Simulation requested; no real motor/camera required."),
              "Check the adapters below before enabling motor output." if hardware_requested
              else "Start PiSD with --hardware only on a wired Pi."),
        _item("camera", "Camera", "ready" if cam_hw and cam_running else
              ("simulation" if cam_backend == "simulation" else "attention"),
              "Picamera2 active; a fresh frame was not captured by preflight."
              if cam_hw and cam_running else
              "Simulation frames active; not a physical Pi camera."
              if cam_backend == "simulation" and cam_running else
              "Camera not running or hardware backend unavailable.",
              "Use Start live to inspect fresh preview frames." if cam_running
              else "Check Pi camera setup, then Start live."),
        _item("model", "AI model", "ready" if model_ready else "attention",
              "AI model loaded and backend marked ready; no inference run."
              if model_ready else
              "TFLite runtime missing in this Python environment; AI model unavailable."
              if not tflite_available else
              "No ready AI model; manual driving remains available.",
              "Verify AI inference with the car secured." if model_ready
              else "Install tflite-runtime, restart PiSD, then load a model."
              if not tflite_available else
              "Upload/select a compatible TFLite model in AI Mode."),
        _item("motor", "Motor adapter",
              "attention" if latched or (hardware_requested and not motor_hw) else
              ("ready" if motor_hw else "simulation"),
              "AI camera-fault safety latch active; output blocked."
              if latched else
              "Real Raspberry Pi GPIO motor adapter initialized; no movement test."
              if motor_hw else
              "Hardware requested but GPIO adapter unavailable; simulation fallback."
              if hardware_requested else "Simulation adapter; no physical motor output.",
              "Review camera fault and explicitly rearm when safe." if latched else
              "Check GPIO library/wiring before real driving." if hardware_requested and not motor_hw
              else "Do not infer motor motion from this passive check."),
        disk_check(project_root),
        _item("network", "Network", "ready",
              "This browser reached PiSD by HTTP. Router, internet and Wi-Fi not tested.",
              "Check PiBooter/network status if another device cannot connect."),
    ]
    return {
        "ok": True, "read_only": True, "component": "PiSD", "mode": mode,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "note": "Observation only: no camera start, motor command, model load, outbound probe, or settings write.",
    }
