# motor_controller.py
"""Motor controller for ZK-BM1 dual H-bridge driver (Pi-Car)."""

import atexit

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    GPIO = None
    _GPIO_AVAILABLE = False
    print("[WARN] RPi.GPIO not available. Motor output will be simulated only.")


IN1_PIN = 17  # LEFT motor
IN2_PIN = 27
IN3_PIN = 22  # RIGHT motor
IN4_PIN = 23

PWM_FREQ_HZ = 1000


class _MotorDriver:
    def __init__(self, pin_fwd: int, pin_rev: int):
        self.pin_fwd = pin_fwd
        self.pin_rev = pin_rev

        if _GPIO_AVAILABLE:
            GPIO.setup(self.pin_fwd, GPIO.OUT)
            GPIO.setup(self.pin_rev, GPIO.OUT)
            self.pwm_fwd = GPIO.PWM(self.pin_fwd, PWM_FREQ_HZ)
            self.pwm_rev = GPIO.PWM(self.pin_rev, PWM_FREQ_HZ)
            self.pwm_fwd.start(0)
            self.pwm_rev.start(0)
        else:
            self.pwm_fwd = None
            self.pwm_rev = None

    def set_speed(self, speed: float):
        speed = max(-1.0, min(1.0, float(speed)))

        if not _GPIO_AVAILABLE:
            print(f"[MOTOR SIM] pins=({self.pin_fwd},{self.pin_rev}) speed={speed:+.2f}")
            return

        if speed > 0:
            duty = speed * 100.0
            self.pwm_fwd.ChangeDutyCycle(duty)
            self.pwm_rev.ChangeDutyCycle(0.0)
        elif speed < 0:
            duty = -speed * 100.0
            self.pwm_fwd.ChangeDutyCycle(0.0)
            self.pwm_rev.ChangeDutyCycle(duty)
        else:
            self.pwm_fwd.ChangeDutyCycle(0.0)
            self.pwm_rev.ChangeDutyCycle(0.0)

    def stop(self):
        if _GPIO_AVAILABLE:
            self.pwm_fwd.ChangeDutyCycle(0.0)
            self.pwm_rev.ChangeDutyCycle(0.0)


class MotorController:
    def __init__(self):
        if _GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

        self.left = _MotorDriver(IN1_PIN, IN2_PIN)
        self.right = _MotorDriver(IN3_PIN, IN4_PIN)

        self.steering = 0.0
        self.throttle = 0.0
        self.mode = "manual"

        atexit.register(self._cleanup)

    @staticmethod
    def _map_steering_throttle_to_wheels(steering: float, throttle: float):
        v = max(0.0, min(1.0, float(throttle)))
        w = max(-1.0, min(1.0, float(steering)))
        k = 0.5

        left = v - k * w
        right = v + k * w

        left = max(0.0, min(1.0, left))
        right = max(0.0, min(1.0, right))
        return left, right

    def update(self, steering: float, throttle: float, mode: str):
        self.steering = float(steering)
        self.throttle = float(throttle)
        self.mode = mode

        left_speed, right_speed = self._map_steering_throttle_to_wheels(
            self.steering, self.throttle
        )

        self.left.set_speed(left_speed)
        self.right.set_speed(right_speed)

        print(
            f"[MOTOR] mode={mode:<10} steering={self.steering:+.2f} "
            f"throttle={self.throttle:.2f} left={left_speed:.2f} right={right_speed:.2f}"
        )

    def _cleanup(self):
        try:
            self.left.stop()
            self.right.stop()
        except Exception:
            pass

        if _GPIO_AVAILABLE:
            GPIO.cleanup()
