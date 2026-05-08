from __future__ import annotations

import atexit
import threading
import time
from dataclasses import dataclass
from typing import Any

from pisd.core.value_utils import clamp_float, clamp_int, normalize_direction

try:  # PiServer uses the same RPi.GPIO style path. rpi-lgpio can provide compatibility on newer OS installs.
    import RPi.GPIO as GPIO  # type: ignore
    GPIO_AVAILABLE = True
except Exception:  # pragma: no cover
    GPIO = None  # type: ignore
    GPIO_AVAILABLE = False


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

    def apply(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        if "left_pins" in data and isinstance(data["left_pins"], (list, tuple)) and len(data["left_pins"]) == 2:
            self.left_pins = (clamp_int(data["left_pins"][0], 0, 27, self.left_pins[0]), clamp_int(data["left_pins"][1], 0, 27, self.left_pins[1]))
        if "right_pins" in data and isinstance(data["right_pins"], (list, tuple)) and len(data["right_pins"]) == 2:
            self.right_pins = (clamp_int(data["right_pins"][0], 0, 27, self.right_pins[0]), clamp_int(data["right_pins"][1], 0, 27, self.right_pins[1]))
        self.pwm_frequency_hz = clamp_int(data.get("pwm_frequency_hz", self.pwm_frequency_hz), 50, 5000, self.pwm_frequency_hz)
        self.left_direction = normalize_direction(data.get("left_direction", self.left_direction), self.left_direction)
        self.right_direction = normalize_direction(data.get("right_direction", self.right_direction), self.right_direction)
        self.steering_direction = normalize_direction(data.get("steering_direction", self.steering_direction), self.steering_direction)
        self.left_max_speed = clamp_float(data.get("left_max_speed", self.left_max_speed), 0.0, 1.0, self.left_max_speed)
        self.right_max_speed = clamp_float(data.get("right_max_speed", self.right_max_speed), 0.0, 1.0, self.right_max_speed)
        self.left_bias = clamp_float(data.get("left_bias", self.left_bias), -0.35, 0.35, self.left_bias)
        self.right_bias = clamp_float(data.get("right_bias", self.right_bias), -0.35, 0.35, self.right_bias)
        self.steer_mix = clamp_float(data.get("steer_mix", self.steer_mix), 0.0, 1.0, self.steer_mix)

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
        }


class _MotorDriver:
    def __init__(self, pin_forward: int, pin_reverse: int, pwm_frequency_hz: int, hardware_enabled: bool):
        self.pin_forward = int(pin_forward)
        self.pin_reverse = int(pin_reverse)
        self.pwm_forward = None
        self.pwm_reverse = None
        self.hardware_enabled = bool(hardware_enabled and GPIO_AVAILABLE)
        if self.hardware_enabled:
            GPIO.setup(self.pin_forward, GPIO.OUT)
            GPIO.setup(self.pin_reverse, GPIO.OUT)
            self.pwm_forward = GPIO.PWM(self.pin_forward, int(pwm_frequency_hz))
            self.pwm_reverse = GPIO.PWM(self.pin_reverse, int(pwm_frequency_hz))
            self.pwm_forward.start(0.0)
            self.pwm_reverse.start(0.0)

    def set_speed(self, speed: float) -> None:
        speed = clamp_float(speed, -1.0, 1.0, 0.0)
        if not self.hardware_enabled:
            return
        if speed > 0:
            self.pwm_forward.ChangeDutyCycle(speed * 100.0)
            self.pwm_reverse.ChangeDutyCycle(0.0)
        elif speed < 0:
            self.pwm_forward.ChangeDutyCycle(0.0)
            self.pwm_reverse.ChangeDutyCycle(-speed * 100.0)
        else:
            self.pwm_forward.ChangeDutyCycle(0.0)
            self.pwm_reverse.ChangeDutyCycle(0.0)

    def stop(self) -> None:
        self.set_speed(0.0)

    def close(self) -> None:
        self.stop()
        for pwm in (self.pwm_forward, self.pwm_reverse):
            try:
                if pwm is not None:
                    pwm.stop()
            except Exception:
                pass


class MotorService:
    """Differential-drive motor service with real GPIO and simulation paths."""

    def __init__(self, config: dict[str, Any] | None = None, hardware_enabled: bool = False):
        self.config = MotorConfig()
        self.config.apply(config or {})
        self.hardware_enabled = bool(hardware_enabled and GPIO_AVAILABLE)
        self.last_left = 0.0
        self.last_right = 0.0
        self.last_command: dict[str, Any] = {}
        self.last_error = ""
        self._lock = threading.RLock()
        self._last_sim_log_at = 0.0
        if hardware_enabled and not GPIO_AVAILABLE:
            self.last_error = "RPi.GPIO is not available; motor service is in simulation mode."
        if self.hardware_enabled:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
        self.left = _MotorDriver(*self.config.left_pins, self.config.pwm_frequency_hz, self.hardware_enabled)
        self.right = _MotorDriver(*self.config.right_pins, self.config.pwm_frequency_hz, self.hardware_enabled)
        atexit.register(self.close)

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            data = self.config.as_dict()
            data.update(
                {
                    "hardware_enabled": bool(self.hardware_enabled),
                    "gpio_available": bool(GPIO_AVAILABLE),
                    "adapter": "rpigpio" if self.hardware_enabled else "simulation",
                    "last_left": float(self.last_left),
                    "last_right": float(self.last_right),
                    "last_command": dict(self.last_command),
                    "last_error": str(self.last_error),
                }
            )
            return data

    def status(self) -> dict[str, Any]:
        return self.get_config()

    def apply_settings(self, data: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            pin_or_pwm_changed = False
            if isinstance(data, dict):
                old = self.config.as_dict()
                self.config.apply(data)
                new = self.config.as_dict()
                pin_or_pwm_changed = old["left_pins"] != new["left_pins"] or old["right_pins"] != new["right_pins"] or old["pwm_frequency_hz"] != new["pwm_frequency_hz"]
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
            self.left.set_speed(left)
            self.right.set_speed(right)
            self.last_left = left
            self.last_right = right
            self.last_command = {
                "steering": steering,
                "throttle": throttle,
                "steer_mix": mix,
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
            except Exception:
                pass
            if self.hardware_enabled and GPIO_AVAILABLE:
                try:
                    GPIO.cleanup()
                except Exception:
                    pass

    def _map_drive_locked(self, steering: float, throttle: float, steer_mix: float) -> tuple[float, float]:
        steering *= -1.0 if self.config.steering_direction < 0 else 1.0
        left = throttle - steer_mix * steering
        right = throttle + steer_mix * steering
        left = self._apply_tuning(left, self.config.left_max_speed, self.config.left_bias, self.config.left_direction)
        right = self._apply_tuning(right, self.config.right_max_speed, self.config.right_bias, self.config.right_direction)
        return left, right

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
        self.last_command = {"steering": 0.0, "throttle": 0.0, "steer_mix": self.config.steer_mix, "timestamp": time.time()}
        self.left.stop()
        self.right.stop()

    def _rebuild_drivers_locked(self) -> None:
        self.left.close()
        self.right.close()
        self.left = _MotorDriver(*self.config.left_pins, self.config.pwm_frequency_hz, self.hardware_enabled)
        self.right = _MotorDriver(*self.config.right_pins, self.config.pwm_frequency_hz, self.hardware_enabled)

    def _log_sim_command(self, steering: float, throttle: float, steer_mix: float, left: float, right: float) -> None:
        now = time.time()
        if now - self._last_sim_log_at >= 0.35:
            print(
                f"[PiSD MOTOR SIM] steering={steering:+.2f} throttle={throttle:+.2f} "
                f"mix={steer_mix:.2f} left={left:+.2f} right={right:+.2f}"
            )
            self._last_sim_log_at = now
