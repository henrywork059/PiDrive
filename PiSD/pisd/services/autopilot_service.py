from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pisd.core.errors import ErrorReport, ErrorReporter, PiSDErrorCodes
from pisd.core.value_utils import clamp_float
from pisd.services.motor_service import MotorService


AUTOPILOT_MODES = {
    "hold": "Hold stopped",
    "straight_slow": "Straight slow cruise",
    "gentle_s_curve": "Gentle S-curve cruise",
    "test_arc_left": "Test arc left",
    "test_arc_right": "Test arc right",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AutopilotConfig:
    """Conservative scripted autopilot settings.

    This first PiSD autopilot page intentionally runs only bounded bench-test
    profiles. Camera/AI control can be plugged into this service later without
    pretending a detector/policy already exists.
    """

    mode: str = "hold"
    max_throttle: float = 0.16
    steer_limit: float = 0.35
    steering_bias: float = 0.0
    steer_mix: float = 1.0
    max_run_seconds: float = 12.0
    tick_hz: float = 8.0
    s_curve_period_s: float = 4.0

    def apply(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        mode = str(data.get("mode", self.mode) or self.mode).strip()
        self.mode = mode if mode in AUTOPILOT_MODES else "hold"
        self.max_throttle = clamp_float(data.get("max_throttle", self.max_throttle), 0.0, 0.35, self.max_throttle)
        self.steer_limit = clamp_float(data.get("steer_limit", self.steer_limit), 0.0, 0.75, self.steer_limit)
        self.steering_bias = clamp_float(data.get("steering_bias", self.steering_bias), -0.35, 0.35, self.steering_bias)
        self.steer_mix = clamp_float(data.get("steer_mix", self.steer_mix), 0.0, 1.0, self.steer_mix)
        self.max_run_seconds = clamp_float(data.get("max_run_seconds", self.max_run_seconds), 1.0, 60.0, self.max_run_seconds)
        self.tick_hz = clamp_float(data.get("tick_hz", self.tick_hz), 2.0, 20.0, self.tick_hz)
        self.s_curve_period_s = clamp_float(data.get("s_curve_period_s", self.s_curve_period_s), 1.5, 12.0, self.s_curve_period_s)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "max_throttle": float(self.max_throttle),
            "steer_limit": float(self.steer_limit),
            "steering_bias": float(self.steering_bias),
            "steer_mix": float(self.steer_mix),
            "max_run_seconds": float(self.max_run_seconds),
            "tick_hz": float(self.tick_hz),
            "s_curve_period_s": float(self.s_curve_period_s),
            "available_modes": dict(AUTOPILOT_MODES),
        }


class AutopilotService:
    """Small bounded autopilot runner for PiSD.

    The service owns only autopilot state and calls MotorService.update(). It is
    deliberately stopped by default, capped in speed/duration, and stopped when
    manual control or STOP API paths override it.
    """

    def __init__(self, motor_service: MotorService, config: dict[str, Any] | None = None, *, hardware_enabled: bool = False):
        self.motor_service = motor_service
        self.config = AutopilotConfig()
        self.config.apply(config or {})
        self.requested_hardware = bool(hardware_enabled)
        self.errors = ErrorReporter("autopilot")
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._armed = False
        self._last_error = ""
        self._last_error_code = PiSDErrorCodes.OK
        self._last_message = "Autopilot idle."
        self._last_reason = "idle"
        self._started_at_monotonic = 0.0
        self._started_at_utc = ""
        self._stopped_at_utc = ""
        self._last_tick_utc = ""
        self._last_command: dict[str, Any] = {"steering": 0.0, "throttle": 0.0, "steer_mix": self.config.steer_mix}
        self._last_output: dict[str, Any] = {"left": 0.0, "right": 0.0}

    def _record(self, code: str, message: str, *, severity: str = "error", context: dict[str, Any] | None = None) -> ErrorReport:
        report = self.errors.report(code, message, severity=severity, context=context)
        self._last_error = report.message
        self._last_error_code = report.code
        self._last_message = report.message
        return report

    def apply_settings(self, data: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            if self._running:
                # Runtime changes are allowed, but they are picked up safely on
                # the next worker tick because the worker snapshots config while locked.
                self._last_message = "Autopilot settings updated while running."
            self.config.apply(data or {})
            return self.status()

    def start(self, data: dict[str, Any] | None = None) -> tuple[bool, str, dict[str, Any], ErrorReport | None]:
        data = data or {}
        with self._lock:
            self.config.apply(data.get("config") if isinstance(data.get("config"), dict) else data)
            if self._running:
                report = self._record(
                    PiSDErrorCodes.AUTOPILOT_ALREADY_RUNNING,
                    "Autopilot is already running. Stop it before starting another profile.",
                    context={"mode": self.config.mode},
                )
                return False, report.message, self.status(), report
            safety_ack = bool(data.get("safety_ack") or data.get("enable_autopilot"))
            enable_output = bool(data.get("enable_motor_output"))
            if not safety_ack:
                report = self._record(
                    PiSDErrorCodes.AUTOPILOT_NOT_ARMED,
                    "Autopilot refused: tick the safety acknowledgement before starting.",
                    context={"mode": self.config.mode},
                )
                return False, report.message, self.status(), report
            if self.motor_service.hardware_enabled and not enable_output:
                report = self._record(
                    PiSDErrorCodes.AUTOPILOT_NOT_ARMED,
                    "Autopilot refused: enable_motor_output must be true when hardware output is active.",
                    context={"mode": self.config.mode},
                )
                return False, report.message, self.status(), report
            self._armed = True
            self._stop_event.clear()
            self._running = True
            self._started_at_monotonic = time.monotonic()
            self._started_at_utc = _utc_now()
            self._stopped_at_utc = ""
            self._last_reason = "running"
            self._last_message = f"Autopilot started: {AUTOPILOT_MODES.get(self.config.mode, self.config.mode)}."
            self._last_command = {"steering": 0.0, "throttle": 0.0, "steer_mix": self.config.steer_mix}
            self._last_output = {"left": 0.0, "right": 0.0}
            self._thread = threading.Thread(target=self._run_loop, name="PiSD-Autopilot", daemon=True)
            self._thread.start()
            return True, self._last_message, self.status(), None

    def stop(self, reason: str = "user_stop") -> dict[str, Any]:
        thread: threading.Thread | None = None
        with self._lock:
            thread = self._thread
            self._stop_event.set()
            self._last_reason = str(reason or "user_stop")
            self._last_message = f"Autopilot stop requested: {self._last_reason}."
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        with self._lock:
            if self._running:
                self._finish_locked(self._last_reason)
            else:
                # Keep a deterministic stopped state even if the worker had already finished.
                self.motor_service.stop()
                self._last_command = {"steering": 0.0, "throttle": 0.0, "steer_mix": self.config.steer_mix}
                self._last_output = {"left": 0.0, "right": 0.0}
            return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            elapsed = max(0.0, time.monotonic() - self._started_at_monotonic) if self._running and self._started_at_monotonic else 0.0
            remaining = max(0.0, self.config.max_run_seconds - elapsed) if self._running else 0.0
            latest = self.errors.latest()
            return {
                "running": bool(self._running),
                "armed": bool(self._armed),
                "mode": self.config.mode,
                "mode_label": AUTOPILOT_MODES.get(self.config.mode, self.config.mode),
                "config": self.config.as_dict(),
                "elapsed_s": round(elapsed, 3),
                "remaining_s": round(remaining, 3),
                "started_at_utc": self._started_at_utc,
                "stopped_at_utc": self._stopped_at_utc,
                "last_tick_utc": self._last_tick_utc,
                "last_command": dict(self._last_command),
                "last_output": dict(self._last_output),
                "last_reason": self._last_reason,
                "last_message": self._last_message,
                "hardware_requested": bool(self.requested_hardware),
                "hardware_output_enabled": bool(self.motor_service.hardware_enabled),
                "last_error_code": latest.code if latest else self._last_error_code,
                "last_error": latest.message if latest else self._last_error,
                "recent_errors": self.errors.history(limit=5),
            }

    def _finish_locked(self, reason: str) -> None:
        self._running = False
        self._armed = False
        self._thread = None
        self._stopped_at_utc = _utc_now()
        self._last_reason = str(reason or "stopped")
        self._last_message = f"Autopilot stopped: {self._last_reason}."
        self._last_command = {"steering": 0.0, "throttle": 0.0, "steer_mix": self.config.steer_mix}
        self._last_output = {"left": 0.0, "right": 0.0}
        self.motor_service.stop()

    def _run_loop(self) -> None:
        reason = "completed"
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    config = AutopilotConfig()
                    config.apply(self.config.as_dict())
                    elapsed = max(0.0, time.monotonic() - self._started_at_monotonic)
                    if elapsed >= config.max_run_seconds:
                        reason = "timeout"
                        break
                    steering, throttle = self._profile_command(config, elapsed)
                left, right = self.motor_service.update(steering=steering, throttle=throttle, steer_mix=config.steer_mix)
                with self._lock:
                    self._last_command = {
                        "mode": "autopilot",
                        "profile": config.mode,
                        "steering": steering,
                        "throttle": throttle,
                        "steer_mix": config.steer_mix,
                        "elapsed_s": round(elapsed, 3),
                        "timestamp": time.time(),
                    }
                    self._last_output = {"left": float(left), "right": float(right)}
                    self._last_tick_utc = _utc_now()
                sleep_s = max(0.02, min(0.5, 1.0 / max(1.0, config.tick_hz)))
                self._stop_event.wait(sleep_s)
            if self._stop_event.is_set() and reason == "completed":
                reason = self._last_reason or "user_stop"
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            report = self.errors.report(PiSDErrorCodes.AUTOPILOT_RUNTIME_FAILED, f"Autopilot runtime failed: {exc}", exc=exc)
            reason = report.code
        finally:
            with self._lock:
                self._finish_locked(reason)

    def _profile_command(self, config: AutopilotConfig, elapsed_s: float) -> tuple[float, float]:
        mode = config.mode
        bias = config.steering_bias
        if mode == "hold":
            return 0.0, 0.0
        if mode == "straight_slow":
            return clamp_float(bias, -config.steer_limit, config.steer_limit, 0.0), config.max_throttle
        if mode == "test_arc_left":
            return clamp_float(-abs(config.steer_limit) + bias, -1.0, 1.0, 0.0), config.max_throttle
        if mode == "test_arc_right":
            return clamp_float(abs(config.steer_limit) + bias, -1.0, 1.0, 0.0), config.max_throttle
        if mode == "gentle_s_curve":
            phase = (elapsed_s / max(0.1, config.s_curve_period_s)) * math.tau
            steering = math.sin(phase) * config.steer_limit + bias
            return clamp_float(steering, -1.0, 1.0, 0.0), config.max_throttle
        return 0.0, 0.0
