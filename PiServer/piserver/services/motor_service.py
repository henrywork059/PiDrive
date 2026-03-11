from __future__ import annotations

import atexit

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
        speed = max(-1.0, min(1.0, float(speed)))
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
        self.left_motor_scale = 1.0
        self.right_motor_scale = 1.0
        self.global_speed_limit = 0.75
        self.turn_gain = 1.0
        atexit.register(self.close)

    def update_calibration(
        self,
        *,
        left_motor_scale: float | None = None,
        right_motor_scale: float | None = None,
        global_speed_limit: float | None = None,
        turn_gain: float | None = None,
    ):
        if left_motor_scale is not None:
            self.left_motor_scale = max(0.2, min(1.8, float(left_motor_scale)))
        if right_motor_scale is not None:
            self.right_motor_scale = max(0.2, min(1.8, float(right_motor_scale)))
        if global_speed_limit is not None:
            self.global_speed_limit = max(0.0, min(1.0, float(global_speed_limit)))
        if turn_gain is not None:
            self.turn_gain = max(0.1, min(2.0, float(turn_gain)))

    def _map_drive(self, steering: float, throttle: float, steer_mix: float):
        throttle = max(0.0, min(float(throttle), float(self.global_speed_limit)))
        steering = max(-1.0, min(1.0, float(steering)))
        steer_mix = max(0.0, min(1.0, float(steer_mix))) * float(self.turn_gain)

        left = throttle - steer_mix * steering
        right = throttle + steer_mix * steering

        left = max(0.0, min(1.0, left * self.left_motor_scale))
        right = max(0.0, min(1.0, right * self.right_motor_scale))
        return left, right

    def update(self, steering: float, throttle: float, steer_mix: float):
        left, right = self._map_drive(steering, throttle, steer_mix)
        self.left.set_speed(left)
        self.right.set_speed(right)
        self.last_left = left
        self.last_right = right

        if not GPIO_AVAILABLE:
            print(
                f"[MOTOR SIM] steering={steering:+.2f} throttle={throttle:.2f} "
                f"mix={steer_mix:.2f} turn_gain={self.turn_gain:.2f} "
                f"left_scale={self.left_motor_scale:.2f} right_scale={self.right_motor_scale:.2f} "
                f"left={left:.2f} right={right:.2f}"
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
