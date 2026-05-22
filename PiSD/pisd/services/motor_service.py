from __future__ import annotations

import atexit
import threading
import time
from dataclasses import dataclass
from typing import Any

from pisd.core.errors import ErrorReport, ErrorReporter, PiSDErrorCodes
from pisd.core.value_utils import clamp_float, clamp_int, normalize_direction

try:  # PiServer uses the same RPi.GPIO style path. rpi-lgpio can provide compatibility on newer OS installs.
    import RPi.GPIO as GPIO  # type: ignore

    GPIO_AVAILABLE = True
except Exception:  # pragma: no cover
    GPIO = None  # type: ignore
    GPIO_AVAILABLE = False


def normalize_test_direction(value: Any, default: int = 1) -> int:
    """Accept user-facing motor test directions and convert to +1/-1.

    Direction 1 means the driver's first/forward pin is active. Direction 2
    means the driver's second/reverse pin is active. These are deliberately
    raw channel directions so each physical car can be calibrated.
    """
    if isinstance(value, str):
        text = value.strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"1", "+1", "direction_1", "direction1", "dir_1", "dir1", "forward", "fwd", "pin1", "a"}:
            return 1
        if text in {"2", "_1", "-1", "direction_2", "direction2", "dir_2", "dir2", "reverse", "rev", "backward", "pin2", "b"}:
            return -1
    return normalize_direction(value, default)


def motor_side_name(value: Any) -> str:
    """Normalize a motor-side name for calibration commands."""
    side = str(value or "").strip().lower()
    if side in {"l", "left"}:
        return "left"
    if side in {"r", "right"}:
        return "right"
    return side


@dataclass
class MotorConfig:
    left_pins: tuple[int, int] = (17, 27)
    right_pins: tuple[int, int] = (22, 23)
    pwm_frequency_hz: int = 1000
    left_direction: int = 1
    right_direction: int = 1
    steering_direction: int = 1
    left_max_speed: float = 1.0
    right_max_speed: float = 1.0
    left_bias: float = 0.0
    right_bias: float = 0.0
    steer_mix: float = 1.0
    steering_mode: str = "turn_rate"
    turn_gain: float = 0.75
    turn_curve: float = 1.5
    min_inside_speed: float = 0.0
    allow_pivot_turn: bool = False

    def apply(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        if "left_pins" in data and isinstance(data["left_pins"], (list, tuple)) and len(data["left_pins"]) == 2:
            self.left_pins = (
                clamp_int(data["left_pins"][0], 0, 27, self.left_pins[0]),
                clamp_int(data["left_pins"][1], 0, 27, self.left_pins[1]),
            )
        if "right_pins" in data and isinstance(data["right_pins"], (list, tuple)) and len(data["right_pins"]) == 2:
            self.right_pins = (
                clamp_int(data["right_pins"][0], 0, 27, self.right_pins[0]),
                clamp_int(data["right_pins"][1], 0, 27, self.right_pins[1]),
            )
        self.pwm_frequency_hz = clamp_int(data.get("pwm_frequency_hz", self.pwm_frequency_hz), 50, 5000, self.pwm_frequency_hz)
        self.left_direction = normalize_direction(data.get("left_direction", self.left_direction), self.left_direction)
        self.right_direction = normalize_direction(data.get("right_direction", self.right_direction), self.right_direction)
        self.steering_direction = normalize_direction(data.get("steering_direction", self.steering_direction), self.steering_direction)
        self.left_max_speed = clamp_float(data.get("left_max_speed", self.left_max_speed), 0.0, 1.0, self.left_max_speed)
        self.right_max_speed = clamp_float(data.get("right_max_speed", self.right_max_speed), 0.0, 1.0, self.right_max_speed)
        self.left_bias = clamp_float(data.get("left_bias", self.left_bias), -0.35, 0.35, self.left_bias)
        self.right_bias = clamp_float(data.get("right_bias", self.right_bias), -0.35, 0.35, self.right_bias)
        self.steer_mix = clamp_float(data.get("steer_mix", self.steer_mix), 0.0, 1.0, self.steer_mix)
        steering_mode = str(data.get("steering_mode", self.steering_mode) or self.steering_mode).strip().lower()
        self.steering_mode = steering_mode if steering_mode in {"turn_rate", "arcade_mix"} else self.steering_mode
        self.turn_gain = clamp_float(data.get("turn_gain", self.turn_gain), 0.0, 2.0, self.turn_gain)
        self.turn_curve = clamp_float(data.get("turn_curve", self.turn_curve), 0.1, 5.0, self.turn_curve)
        self.min_inside_speed = clamp_float(data.get("min_inside_speed", self.min_inside_speed), 0.0, 0.95, self.min_inside_speed)
        raw_pivot = data.get("allow_pivot_turn", self.allow_pivot_turn)
        if isinstance(raw_pivot, str):
            self.allow_pivot_turn = raw_pivot.strip().lower() in {"true", "1", "yes", "on"}
        else:
            self.allow_pivot_turn = bool(raw_pivot)

    def as_dict(self) -> dict[str, Any]:
        return {
            "left_pins": list(self.left_pins),
            "right_pins": list(self.right_pins),
            "pwm_frequency_hz": int(self.pwm_frequency_hz),
            "left_direction": int(self.left_direction),
            "right_direction": int(self.right_direction),
            "steering_direction": int(self.steering_direction),
            "left_max_speed": float(self.left_max_speed),
            "right_max_speed": float(self.right_max_speed),
            "left_bias": float(self.left_bias),
            "right_bias": float(self.right_bias),
            "steer_mix": float(self.steer_mix),
            "steering_mode": str(self.steering_mode),
            "turn_gain": float(self.turn_gain),
            "turn_curve": float(self.turn_curve),
            "min_inside_speed": float(self.min_inside_speed),
            "allow_pivot_turn": bool(self.allow_pivot_turn),
        }


class _MotorDriver:
    def __init__(
        self,
        pin_forward: int,
        pin_reverse: int,
        pwm_frequency_hz: int,
        hardware_enabled: bool,
        reporter: ErrorReporter,
        side: str,
    ):
        self.pin_forward = int(pin_forward)
        self.pin_reverse = int(pin_reverse)
        self.pwm_forward = None
        self.pwm_reverse = None
        self.side = side
        self.reporter = reporter
        self.hardware_enabled = bool(hardware_enabled and GPIO_AVAILABLE)
        if self.hardware_enabled:
            try:
                GPIO.setup(self.pin_forward, GPIO.OUT)
                GPIO.setup(self.pin_reverse, GPIO.OUT)
                self.pwm_forward = GPIO.PWM(self.pin_forward, int(pwm_frequency_hz))
                self.pwm_reverse = GPIO.PWM(self.pin_reverse, int(pwm_frequency_hz))
                self.pwm_forward.start(0.0)
                self.pwm_reverse.start(0.0)
            except Exception as exc:
                self.hardware_enabled = False
                self.pwm_forward = None
                self.pwm_reverse = None
                self.reporter.report(
                    PiSDErrorCodes.MOTOR_GPIO_SETUP_FAILED,
                    f"Failed to set up {side} motor GPIO/PWM; output disabled: {exc}",
                    context={"side": side, "forward_pin": self.pin_forward, "reverse_pin": self.pin_reverse},
                    exc=exc,
                )

    def set_speed(self, speed: float) -> bool:
        speed = clamp_float(speed, -1.0, 1.0, 0.0)
        if not self.hardware_enabled:
            return True
        try:
            if speed > 0:
                self.pwm_forward.ChangeDutyCycle(speed * 100.0)
                self.pwm_reverse.ChangeDutyCycle(0.0)
            elif speed < 0:
                self.pwm_forward.ChangeDutyCycle(0.0)
                self.pwm_reverse.ChangeDutyCycle(-speed * 100.0)
            else:
                self.pwm_forward.ChangeDutyCycle(0.0)
                self.pwm_reverse.ChangeDutyCycle(0.0)
            return True
        except Exception as exc:
            self.reporter.report(
                PiSDErrorCodes.MOTOR_OUTPUT_FAILED,
                f"Failed to update {self.side} motor output: {exc}",
                context={"side": self.side, "speed": speed},
                exc=exc,
            )
            return False

    def stop(self) -> bool:
        return self.set_speed(0.0)

    def close(self) -> None:
        self.stop()
        for pwm in (self.pwm_forward, self.pwm_reverse):
            try:
                if pwm is not None:
                    pwm.stop()
            except Exception as exc:
                self.reporter.report(
                    PiSDErrorCodes.MOTOR_CLOSE_FAILED,
                    f"Failed to stop PWM on {self.side} motor: {exc}",
                    context={"side": self.side},
                    exc=exc,
                )


class MotorService:
    """Differential-drive motor service with real GPIO and simulation paths.

    All GPIO/PWM failures are captured with PiSD error codes and exposed in the
    service status. Real motor movement still requires explicit hardware mode.
    """

    def __init__(self, config: dict[str, Any] | None = None, hardware_enabled: bool = False):
        self.config = MotorConfig()
        self.config.apply(config or {})
        self.requested_hardware = bool(hardware_enabled)
        self.hardware_enabled = bool(hardware_enabled and GPIO_AVAILABLE)
        self.last_left = 0.0
        self.last_right = 0.0
        self.last_command: dict[str, Any] = {}
        self.last_error = ""
        self.last_error_code = PiSDErrorCodes.OK
        self.errors = ErrorReporter("motor")
        self._lock = threading.RLock()
        self._last_sim_log_at = 0.0
        if hardware_enabled and not GPIO_AVAILABLE:
            self._record(
                PiSDErrorCodes.MOTOR_GPIO_MISSING,
                "RPi.GPIO is not available; motor service is in simulation mode.",
                severity="warning",
            )
        if self.hardware_enabled:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
            except Exception as exc:
                self.hardware_enabled = False
                self._record(
                    PiSDErrorCodes.MOTOR_GPIO_SETUP_FAILED,
                    f"Failed to initialise GPIO; motor service is in simulation mode: {exc}",
                    exc=exc,
                )
        self.left = _MotorDriver(*self.config.left_pins, self.config.pwm_frequency_hz, self.hardware_enabled, self.errors, "left")
        self.right = _MotorDriver(*self.config.right_pins, self.config.pwm_frequency_hz, self.hardware_enabled, self.errors, "right")
        if self.hardware_enabled and not (self.left.hardware_enabled and self.right.hardware_enabled):
            self.hardware_enabled = False
            self._record(
                PiSDErrorCodes.MOTOR_GPIO_SETUP_FAILED,
                "One or more motor drivers failed to initialise; motor service is in simulation mode.",
            )
        atexit.register(self.close)

    def _record(
        self,
        code: str,
        message: str,
        *,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        exc: BaseException | None = None,
    ) -> ErrorReport:
        report = self.errors.report(code, message, severity=severity, context=context, exc=exc)
        self.last_error = report.message
        self.last_error_code = report.code
        return report

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            data = self.config.as_dict()
            data.update(
                {
                    "hardware_requested": bool(self.requested_hardware),
                    "hardware_enabled": bool(self.hardware_enabled),
                    "gpio_available": bool(GPIO_AVAILABLE),
                    "adapter": "rpigpio" if self.hardware_enabled else "simulation",
                    "last_left": float(self.last_left),
                    "last_right": float(self.last_right),
                    "last_command": dict(self.last_command),
                    "last_error": str(self.last_error),
                    "last_error_code": str(self.last_error_code),
                }
            )
            data.update(self.errors.status_fields(limit=5))
            return data

    def status(self) -> dict[str, Any]:
        return self.get_config()

    def test_motor_channel(
        self,
        side: str,
        *,
        direction: int | str = 1,
        speed: float = 0.2,
        duration: float = 0.35,
        apply_config_direction: bool = False,
    ) -> dict[str, Any]:
        """Run one motor, one direction, one speed, then stop.

        This is for hardware calibration. It bypasses differential steering mix
        so the user can identify each physical motor direction independently.
        Direction 1 drives the driver's first/forward pin. Direction 2 drives
        the driver's second/reverse pin. When ``apply_config_direction`` is
        true, the saved left/right direction multiplier is also applied.
        """
        side_name = motor_side_name(side)
        if side_name not in {"left", "right"}:
            report = self._record(
                PiSDErrorCodes.MOTOR_TEST_INVALID,
                "Motor channel test side must be 'left' or 'right'.",
                context={"side": side},
            )
            return {"ok": False, "code": report.code, "message": report.message, "error": report.as_dict(), "motor": self.status()}

        direction_value = normalize_test_direction(direction, 1)
        requested_speed = clamp_float(speed, 0.0, 1.0, 0.2)
        if requested_speed < 0.01:
            report = self._record(
                PiSDErrorCodes.MOTOR_TEST_INVALID,
                "Motor channel test speed must be at least 0.01.",
                context={"side": side_name, "speed": speed},
            )
            return {"ok": False, "code": report.code, "message": report.message, "error": report.as_dict(), "motor": self.status()}

        duration_s = clamp_float(duration, 0.05, 2.0, 0.35)
        config_direction = self.config.left_direction if side_name == "left" else self.config.right_direction
        effective_direction = direction_value * (config_direction if apply_config_direction else 1)
        effective_speed = clamp_float(requested_speed * effective_direction, -1.0, 1.0, 0.0)

        with self._lock:
            self._stop_locked()
            driver = self.left if side_name == "left" else self.right
            other = self.right if side_name == "left" else self.left
            other.stop()
            ok = driver.set_speed(effective_speed)
            if side_name == "left":
                self.last_left = effective_speed
                self.last_right = 0.0
            else:
                self.last_left = 0.0
                self.last_right = effective_speed
            self.last_command = {
                "mode": "motor_channel_test",
                "side": side_name,
                "direction": direction_value,
                "direction_label": "direction_1" if direction_value > 0 else "direction_2",
                "speed": requested_speed,
                "effective_speed": effective_speed,
                "duration": duration_s,
                "apply_config_direction": bool(apply_config_direction),
                "timestamp": time.time(),
            }
            if not ok:
                self._record(
                    PiSDErrorCodes.MOTOR_TEST_OUTPUT_FAILED,
                    "Motor channel test output command failed.",
                    context=dict(self.last_command),
                )

        if not self.hardware_enabled:
            print(
                f"[PiSD MOTOR TEST SIM] side={side_name} direction={'direction_1' if direction_value > 0 else 'direction_2'} "
                f"speed={requested_speed:.2f} effective={effective_speed:+.2f} duration={duration_s:.2f}s"
            )

        try:
            time.sleep(duration_s)
        finally:
            with self._lock:
                self._stop_locked()

        status = self.status()
        return {
            "ok": bool(ok),
            "code": PiSDErrorCodes.OK if ok else PiSDErrorCodes.MOTOR_TEST_OUTPUT_FAILED,
            "message": "Motor channel test completed and stopped." if ok else "Motor channel test failed and stop was requested.",
            "side": side_name,
            "direction": direction_value,
            "direction_label": "direction_1" if direction_value > 0 else "direction_2",
            "speed": requested_speed,
            "effective_speed": effective_speed,
            "duration": duration_s,
            "apply_config_direction": bool(apply_config_direction),
            "hardware_output_enabled": bool(self.hardware_enabled),
            "motor": status,
        }

    def apply_settings(self, data: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            pin_or_pwm_changed = False
            if isinstance(data, dict):
                old = self.config.as_dict()
                self.config.apply(data)
                new = self.config.as_dict()
                pin_or_pwm_changed = (
                    old["left_pins"] != new["left_pins"]
                    or old["right_pins"] != new["right_pins"]
                    or old["pwm_frequency_hz"] != new["pwm_frequency_hz"]
                )
            else:
                self._record(PiSDErrorCodes.MOTOR_CONFIG_INVALID, "Motor settings payload was not an object.")
            self._stop_locked()
            if pin_or_pwm_changed:
                self._rebuild_drivers_locked()
            return self.get_config()

    def update(self, steering: float = 0.0, throttle: float = 0.0, steer_mix: float | None = None) -> tuple[float, float]:
        with self._lock:
            steering = clamp_float(steering, -1.0, 1.0, 0.0)
            throttle = clamp_float(throttle, -1.0, 1.0, 0.0)
            mix = self.config.steer_mix if steer_mix is None else clamp_float(steer_mix, 0.0, 1.0, self.config.steer_mix)
            left, right = self._map_drive_locked(steering, throttle, mix)
            left_ok = self.left.set_speed(left)
            right_ok = self.right.set_speed(right)
            if not left_ok or not right_ok:
                self._record(
                    PiSDErrorCodes.MOTOR_OUTPUT_FAILED,
                    "Motor output command failed; last command retained for diagnosis.",
                    context={"left_ok": left_ok, "right_ok": right_ok, "left": left, "right": right},
                )
            self.last_left = left
            self.last_right = right
            self.last_command = {
                "steering": steering,
                "throttle": throttle,
                "steer_mix": mix,
                "steering_mode": self.config.steering_mode,
                "turn_gain": self.config.turn_gain,
                "turn_curve": self.config.turn_curve,
                "min_inside_speed": self.config.min_inside_speed,
                "allow_pivot_turn": self.config.allow_pivot_turn,
                "timestamp": time.time(),
            }
        if not self.hardware_enabled:
            self._log_sim_command(steering, throttle, mix, left, right)
        return left, right

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def close(self) -> None:
        with self._lock:
            try:
                self._stop_locked()
                self.left.close()
                self.right.close()
            except Exception as exc:
                self._record(PiSDErrorCodes.MOTOR_CLOSE_FAILED, f"Motor close failed: {exc}", exc=exc)
            if self.hardware_enabled and GPIO_AVAILABLE:
                try:
                    GPIO.cleanup()
                except Exception as exc:
                    self._record(PiSDErrorCodes.MOTOR_CLOSE_FAILED, f"GPIO cleanup failed: {exc}", exc=exc)

    def _map_drive_locked(self, steering: float, throttle: float, steer_mix: float) -> tuple[float, float]:
        steering *= -1.0 if self.config.steering_direction < 0 else 1.0
        if self.config.steering_mode == "arcade_mix":
            left = throttle - steer_mix * steering
            right = throttle + steer_mix * steering
        else:
            left, right = self._map_turn_rate_locked(steering, throttle)
        left = self._apply_tuning(left, self.config.left_max_speed, self.config.left_bias, self.config.left_direction)
        right = self._apply_tuning(right, self.config.right_max_speed, self.config.right_bias, self.config.right_direction)
        return left, right

    def _map_turn_rate_locked(self, steering: float, throttle: float) -> tuple[float, float]:
        """Map speed + curvature intent to differential output.

        In turn-rate mode, throttle controls travel speed along the selected
        curve and steering controls curve tightness. Positive steering means a
        right curve; negative steering means a left curve. The default mapping
        slows the inside wheel rather than reversing it, so full steering gives
        the tightest non-pivot curve instead of immediately spinning in place.
        """
        speed = clamp_float(throttle, -1.0, 1.0, 0.0)
        steer = clamp_float(steering, -1.0, 1.0, 0.0)
        gain = clamp_float(self.config.turn_gain, 0.0, 2.0, 0.75)
        curve = clamp_float(self.config.turn_curve, 0.1, 5.0, 1.5)
        turn_mag = clamp_float((abs(steer) ** curve) * gain, 0.0, 1.0, 0.0)
        if turn_mag <= 1e-6:
            return speed, speed

        if self.config.allow_pivot_turn and abs(speed) < 1e-4:
            pivot = turn_mag
            return (pivot, -pivot) if steer > 0 else (-pivot, pivot)

        if self.config.allow_pivot_turn:
            inside_factor = 1.0 - (2.0 * turn_mag)
        else:
            inside_factor = max(clamp_float(self.config.min_inside_speed, 0.0, 0.95, 0.0), 1.0 - turn_mag)

        if steer > 0:
            # Right curve: left/outside wheel keeps requested speed, right/inside wheel slows.
            return speed, speed * inside_factor
        # Left curve: right/outside wheel keeps requested speed, left/inside wheel slows.
        return speed * inside_factor, speed

    def _apply_tuning(self, value: float, max_speed: float, bias: float, direction: int) -> float:
        value = clamp_float(value, -1.0, 1.0, 0.0)
        if abs(value) > 1e-4 and abs(bias) > 1e-4:
            value += (1.0 if value > 0 else -1.0) * bias
        value = clamp_float(value, -1.0, 1.0, 0.0)
        value *= clamp_float(max_speed, 0.0, 1.0, 1.0)
        value *= -1.0 if direction < 0 else 1.0
        return clamp_float(value, -1.0, 1.0, 0.0)

    def _stop_locked(self) -> None:
        self.last_left = 0.0
        self.last_right = 0.0
        self.last_command = {
            "steering": 0.0,
            "throttle": 0.0,
            "steer_mix": self.config.steer_mix,
            "steering_mode": self.config.steering_mode,
            "turn_gain": self.config.turn_gain,
            "turn_curve": self.config.turn_curve,
            "min_inside_speed": self.config.min_inside_speed,
            "allow_pivot_turn": self.config.allow_pivot_turn,
            "timestamp": time.time(),
        }
        left_ok = self.left.stop()
        right_ok = self.right.stop()
        if not left_ok or not right_ok:
            self._record(
                PiSDErrorCodes.MOTOR_STOP_FAILED,
                "Motor stop command failed on one or more channels.",
                context={"left_ok": left_ok, "right_ok": right_ok},
            )

    def _rebuild_drivers_locked(self) -> None:
        self.left.close()
        self.right.close()
        self.left = _MotorDriver(*self.config.left_pins, self.config.pwm_frequency_hz, self.hardware_enabled, self.errors, "left")
        self.right = _MotorDriver(*self.config.right_pins, self.config.pwm_frequency_hz, self.hardware_enabled, self.errors, "right")

    def _log_sim_command(self, steering: float, throttle: float, steer_mix: float, left: float, right: float) -> None:
        now = time.time()
        if now - self._last_sim_log_at >= 0.35:
            print(
                f"[PiSD MOTOR SIM] steering={steering:+.2f} throttle={throttle:+.2f} "
                f"mode={self.config.steering_mode} mix={steer_mix:.2f} turn_gain={self.config.turn_gain:.2f} "
                f"left={left:+.2f} right={right:+.2f}"
            )
            self._last_sim_log_at = now
