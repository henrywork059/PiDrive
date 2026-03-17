from __future__ import annotations

import atexit
from typing import Any

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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


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
        speed = _clamp(speed, -1.0, 1.0)
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

        atexit.register(self.close)

    def get_config(self) -> dict[str, Any]:
        return {
            "left_direction": self.left_direction,
            "right_direction": self.right_direction,
            "steering_direction": self.steering_direction,
            "left_max_speed": self.left_max_speed,
            "right_max_speed": self.right_max_speed,
            "left_bias": self.left_bias,
            "right_bias": self.right_bias,
            "gpio_available": GPIO_AVAILABLE,
        }

    def apply_settings(self, data: dict | None) -> dict[str, Any]:
        if not isinstance(data, dict):
            return self.get_config()

        if "left_direction" in data:
            self.left_direction = -1 if int(data.get("left_direction", 1)) < 0 else 1
        if "right_direction" in data:
            self.right_direction = -1 if int(data.get("right_direction", 1)) < 0 else 1
        if "steering_direction" in data:
            self.steering_direction = -1 if int(data.get("steering_direction", 1)) < 0 else 1
        if "left_max_speed" in data:
            self.left_max_speed = _clamp(float(data.get("left_max_speed", 1.0)), 0.0, 1.0)
        if "right_max_speed" in data:
            self.right_max_speed = _clamp(float(data.get("right_max_speed", 1.0)), 0.0, 1.0)
        if "left_bias" in data:
            self.left_bias = _clamp(float(data.get("left_bias", 0.0)), -0.35, 0.35)
        if "right_bias" in data:
            self.right_bias = _clamp(float(data.get("right_bias", 0.0)), -0.35, 0.35)

        self.stop()
        return self.get_config()

    def _apply_motor_tuning(self, value: float, max_speed: float, bias: float, direction: int) -> float:
        value = _clamp(value, -1.0, 1.0)
        if abs(value) > 1e-4 and abs(bias) > 1e-4:
            value += (1.0 if value > 0 else -1.0) * bias
        value = _clamp(value, -1.0, 1.0)
        value *= _clamp(max_speed, 0.0, 1.0)
        value = _clamp(value, -1.0, 1.0)
        value *= -1.0 if int(direction) < 0 else 1.0
        return _clamp(value, -1.0, 1.0)

    def _map_drive(self, steering: float, throttle: float, steer_mix: float):
        throttle = _clamp(throttle, -1.0, 1.0)
        steering = _clamp(steering, -1.0, 1.0)
        steer_mix = _clamp(steer_mix, 0.0, 1.0)

        steering *= -1.0 if int(self.steering_direction) < 0 else 1.0

        left = throttle - steer_mix * steering
        right = throttle + steer_mix * steering

        left = self._apply_motor_tuning(left, self.left_max_speed, self.left_bias, self.left_direction)
        right = self._apply_motor_tuning(right, self.right_max_speed, self.right_bias, self.right_direction)
        return left, right

    def update(self, steering: float, throttle: float, steer_mix: float):
        left, right = self._map_drive(steering, throttle, steer_mix)
        self.left.set_speed(left)
        self.right.set_speed(right)
        self.last_left = left
        self.last_right = right

        if not GPIO_AVAILABLE:
            print(
                f"[MOTOR SIM] steering={steering:+.2f} throttle={throttle:+.2f} "
                f"mix={steer_mix:.2f} left={left:+.2f} right={right:+.2f}"
            )
        return left, right

    def stop(self):
        self.last_left = 0.0
        self.last_right = 0.0
        self.left.stop()
        self.right.stop()

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
