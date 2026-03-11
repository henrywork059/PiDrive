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
        atexit.register(self.close)

    def _map_drive(self, steering: float, throttle: float, steer_mix: float):
        throttle = max(0.0, min(1.0, float(throttle)))
        steering = max(-1.0, min(1.0, float(steering)))
        steer_mix = max(0.0, min(1.0, float(steer_mix)))

        left = throttle - steer_mix * steering
        right = throttle + steer_mix * steering

        left = max(0.0, min(1.0, left))
        right = max(0.0, min(1.0, right))
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
                f"mix={steer_mix:.2f} left={left:.2f} right={right:.2f}"
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
