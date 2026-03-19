from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import time

from .fake_robot import RobotLogEntry


@dataclass
class PiCarRobotBridge:
    """Adapter for CustomDrive to reuse PiServer-style motor services.

    The bridge now accepts either:
    - PiServer's ``MotorService.update(steering, throttle, steer_mix)``, or
    - older controllers that accept ``mode=...`` style keyword arguments.

    ``arm`` remains optional. When no real arm is bound you can choose between
    failing pickup/release (safer default) or virtual success for field-path
    debugging by enabling ``allow_virtual_grab_without_arm``.
    """

    motor: Any
    arm: Optional[Any] = None
    mode_name: str = "custom_drive"
    started_at: float = field(default_factory=time.monotonic)
    steer_mix: float = 0.75
    allow_virtual_grab_without_arm: bool = False
    history: list[RobotLogEntry] = field(default_factory=list)
    has_payload: bool = False
    last_error: str = ''

    def reset_mission_state(self) -> None:
        self.started_at = time.monotonic()
        self.history.clear()
        self.has_payload = False

    def now(self) -> float:
        return time.monotonic() - self.started_at

    def _log(self, action: str, detail: str) -> None:
        self.history.append(RobotLogEntry(self.now(), action, detail))

    def _call_motor_update(self, steering: float, throttle: float):
        update = getattr(self.motor, "update", None)
        if update is None:
            raise AttributeError("Motor object does not expose update().")

        last_error: Exception | None = None
        call_patterns = [
            {"steering": steering, "throttle": throttle, "steer_mix": self.steer_mix},
            {"steering": steering, "throttle": throttle, "mode": self.mode_name},
            {"steering": steering, "throttle": throttle},
        ]
        for kwargs in call_patterns:
            try:
                return update(**kwargs)
            except TypeError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        return update(steering, throttle)

    def set_drive(self, steering: float, throttle: float, note: str = "") -> None:
        try:
            result = self._call_motor_update(steering=steering, throttle=throttle)
            self.last_error = ''
        except Exception as exc:
            self.last_error = str(exc)
            self._log('drive_error', f"steering={steering:+.2f}, throttle={throttle:+.2f}, note={note}, error={exc}")
            return
        extra = ""
        if isinstance(result, tuple) and len(result) >= 2:
            extra = f" | left={float(result[0]):+.2f} right={float(result[1]):+.2f}"
        self._log("drive", f"steering={steering:+.2f}, throttle={throttle:+.2f}, note={note}{extra}")

    def stop(self, note: str = "") -> None:
        try:
            stop = getattr(self.motor, "stop", None)
            if callable(stop):
                stop()
            else:
                self._call_motor_update(steering=0.0, throttle=0.0)
            self.last_error = ''
        except Exception as exc:
            self.last_error = str(exc)
            self._log('stop_error', f"note={note}, error={exc}")
            return
        self._log("stop", note)

    def _run_arm_step(self, *names: str) -> bool:
        if self.arm is None:
            return False
        for name in names:
            fn = getattr(self.arm, name, None)
            if callable(fn):
                fn()
                return True
        return False

    def pickup_sequence(self) -> bool:
        if self.arm is None:
            if self.allow_virtual_grab_without_arm:
                self.has_payload = True
                self._log("pickup", "virtual pickup succeeded (no arm bound)")
                return True
            self._log("pickup", "pickup failed: no arm bound")
            return False

        self._run_arm_step("open", "release", "unclamp")
        self._run_arm_step("lower", "down")
        grabbed = self._run_arm_step("close", "grab", "clamp")
        self._run_arm_step("raise_up", "raise_", "lift", "up")
        ok = bool(grabbed)
        self.has_payload = ok
        self._log("pickup", "pickup sequence succeeded" if ok else "pickup sequence incomplete")
        return ok

    def release_sequence(self) -> bool:
        if not self.has_payload and not self.allow_virtual_grab_without_arm:
            self._log("release", "release failed: no payload")
            return False

        if self.arm is None:
            if self.allow_virtual_grab_without_arm:
                self.has_payload = False
                self._log("release", "virtual release succeeded (no arm bound)")
                return True
            self._log("release", "release failed: no arm bound")
            return False

        self._run_arm_step("lower", "down")
        opened = self._run_arm_step("open", "release", "unclamp")
        self._run_arm_step("raise_up", "raise_", "lift", "up")
        ok = bool(opened)
        if ok:
            self.has_payload = False
        self._log("release", "release sequence succeeded" if ok else "release sequence incomplete")
        return ok
