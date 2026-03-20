from __future__ import annotations

import atexit
import threading
import time
from typing import Any

from piserver.core.value_utils import clamp_float, normalize_direction, parse_finite_float

try:
    import RPi.GPIO as GPIO  # type: ignore
    GPIO_AVAILABLE = True
except Exception:
    GPIO = None  # type: ignore
    GPIO_AVAILABLE = False

IN1_PIN = 17
IN2_PIN = 27
IN3_PIN = 22
IN4_PIN = 23
PWM_FREQ_HZ = 1000


class _MotorDriver:
    def __init__(self, pin_fwd: int, pin_rev: int):
        self.pin_fwd = pin_fwd
        self.pin_rev = pin_rev
        self.pwm_fwd = None
        self.pwm_rev = None

        if GPIO_AVAILABLE:
            GPIO.setup(self.pin_fwd, GPIO.OUT)
            GPIO.setup(self.pin_rev, GPIO.OUT)
            self.pwm_fwd = GPIO.PWM(self.pin_fwd, PWM_FREQ_HZ)
            self.pwm_rev = GPIO.PWM(self.pin_rev, PWM_FREQ_HZ)
            self.pwm_fwd.start(0)
            self.pwm_rev.start(0)

    def set_speed(self, speed: float):
        speed = clamp_float(speed, -1.0, 1.0)
        if not GPIO_AVAILABLE:
            return

        if speed > 0:
            self.pwm_fwd.ChangeDutyCycle(speed * 100.0)
            self.pwm_rev.ChangeDutyCycle(0.0)
        elif speed < 0:
            self.pwm_fwd.ChangeDutyCycle(0.0)
            self.pwm_rev.ChangeDutyCycle(-speed * 100.0)
        else:
            self.pwm_fwd.ChangeDutyCycle(0.0)
            self.pwm_rev.ChangeDutyCycle(0.0)

    def stop(self):
        if GPIO_AVAILABLE:
            self.set_speed(0.0)


class MotorService:
    def __init__(self):
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

        self.left = _MotorDriver(IN1_PIN, IN2_PIN)
        self.right = _MotorDriver(IN3_PIN, IN4_PIN)
        self.last_left = 0.0
        self.last_right = 0.0

        self.left_direction = 1
        self.right_direction = 1
        self.steering_direction = 1
        self.left_max_speed = 1.0
        self.right_max_speed = 1.0
        self.left_bias = 0.0
        self.right_bias = 0.0
        self._lock = threading.RLock()
        self._last_sim_log_at = 0.0

        atexit.register(self.close)

    def get_persisted_config(self) -> dict[str, Any]:
        with self._lock:
            return {
                "left_direction": self.left_direction,
                "right_direction": self.right_direction,
                "steering_direction": self.steering_direction,
                "left_max_speed": self.left_max_speed,
                "right_max_speed": self.right_max_speed,
                "left_bias": self.left_bias,
                "right_bias": self.right_bias,
            }

    def get_config(self) -> dict[str, Any]:
        data = self.get_persisted_config()
        data["gpio_available"] = GPIO_AVAILABLE
        return data

    def apply_settings(self, data: dict | None) -> dict[str, Any]:
        if not isinstance(data, dict):
            return self.get_config()

        with self._lock:
            if "left_direction" in data:
                self.left_direction = normalize_direction(data.get("left_direction", self.left_direction), self.left_direction)
            if "right_direction" in data:
                self.right_direction = normalize_direction(data.get("right_direction", self.right_direction), self.right_direction)
            if "steering_direction" in data:
                self.steering_direction = normalize_direction(data.get("steering_direction", self.steering_direction), self.steering_direction)
            if "left_max_speed" in data:
                self.left_max_speed = clamp_float(parse_finite_float(data.get("left_max_speed", self.left_max_speed), self.left_max_speed), 0.0, 1.0)
            if "right_max_speed" in data:
                self.right_max_speed = clamp_float(parse_finite_float(data.get("right_max_speed", self.right_max_speed), self.right_max_speed), 0.0, 1.0)
            if "left_bias" in data:
                self.left_bias = clamp_float(parse_finite_float(data.get("left_bias", self.left_bias), self.left_bias), -0.35, 0.35)
            if "right_bias" in data:
                self.right_bias = clamp_float(parse_finite_float(data.get("right_bias", self.right_bias), self.right_bias), -0.35, 0.35)
            self._stop_locked()
            return self.get_config()

    def _apply_motor_tuning(self, value: float, max_speed: float, bias: float, direction: int) -> float:
        value = clamp_float(value, -1.0, 1.0)
        if abs(value) > 1e-4 and abs(bias) > 1e-4:
            value += (1.0 if value > 0 else -1.0) * bias
        value = clamp_float(value, -1.0, 1.0)
        value *= clamp_float(max_speed, 0.0, 1.0)
        value = clamp_float(value, -1.0, 1.0)
        value *= -1.0 if int(direction) < 0 else 1.0
        return clamp_float(value, -1.0, 1.0)

    def _map_drive_locked(self, steering: float, throttle: float, steer_mix: float):
        throttle = clamp_float(throttle, -1.0, 1.0)
        steering = clamp_float(steering, -1.0, 1.0)
        steer_mix = clamp_float(steer_mix, 0.0, 1.0)

        steering *= -1.0 if int(self.steering_direction) < 0 else 1.0

        left = throttle - steer_mix * steering
        right = throttle + steer_mix * steering

        left = self._apply_motor_tuning(left, self.left_max_speed, self.left_bias, self.left_direction)
        right = self._apply_motor_tuning(right, self.right_max_speed, self.right_bias, self.right_direction)
        return left, right

    def update(self, steering: float, throttle: float, steer_mix: float):
        with self._lock:
            previous_left = self.last_left
            previous_right = self.last_right
            left, right = self._map_drive_locked(steering, throttle, steer_mix)
            self.left.set_speed(left)
            self.right.set_speed(right)
            self.last_left = left
            self.last_right = right

        if not GPIO_AVAILABLE:
            now = time.time()
            changed = abs(left - previous_left) > 0.01 or abs(right - previous_right) > 0.01
            if changed or (now - self._last_sim_log_at) >= 1.0:
                print(
                    f"[MOTOR SIM] steering={steering:+.2f} throttle={throttle:+.2f} "
                    f"mix={steer_mix:.2f} left={left:+.2f} right={right:+.2f}"
                )
                self._last_sim_log_at = now
        return left, right

    def _stop_locked(self):
        self.last_left = 0.0
        self.last_right = 0.0
        self.left.stop()
        self.right.stop()

    def stop(self):
        with self._lock:
            self._stop_locked()

    def close(self):
        try:
            self.stop()
        except Exception:
            pass
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except Exception:
                pass
