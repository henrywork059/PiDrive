#!/usr/bin/env python3
"""Validate PiSD motor steering-mode mapping without moving hardware."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402


def line(ok: bool, label: str, message: str, details: dict | None = None) -> bool:
    code = PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED
    print(f"{'OK  ' if ok else 'FAIL'} {code}   {label} - {message}")
    if details is not None:
        print(json.dumps(details, indent=2, sort_keys=True))
    return ok


def close_motor(motor: MotorService) -> None:
    try:
        motor.close()
    except Exception:
        pass


def main() -> int:
    ok = True

    motor = MotorService({"steering_mode": "turn_rate", "turn_gain": 0.75, "turn_curve": 1.5}, hardware_enabled=False)
    try:
        left, right = motor.update(steering=1.0, throttle=0.40)
        ok &= line(left > right >= 0.0, "motor.turn_rate.right_curve", "right curve slows the right/inside wheel without reversing", {"left": left, "right": right})
        left, right = motor.update(steering=-1.0, throttle=0.40)
        ok &= line(right > left >= 0.0, "motor.turn_rate.left_curve", "left curve slows the left/inside wheel without reversing", {"left": left, "right": right})
        left, right = motor.update(steering=0.0, throttle=0.40)
        ok &= line(abs(left - 0.40) < 1e-9 and abs(right - 0.40) < 1e-9, "motor.turn_rate.straight", "straight command keeps both wheels equal", {"left": left, "right": right})
        left, right = motor.update(steering=1.0, throttle=0.0)
        ok &= line(abs(left) < 1e-9 and abs(right) < 1e-9, "motor.turn_rate.no_pivot_default", "default turn-rate mode does not pivot with zero throttle", {"left": left, "right": right})
    finally:
        close_motor(motor)

    motor = MotorService({"steering_mode": "turn_rate", "turn_gain": 0.75, "turn_curve": 1.5, "allow_pivot_turn": True}, hardware_enabled=False)
    try:
        left, right = motor.update(steering=1.0, throttle=0.0)
        ok &= line(left > 0.0 and right < 0.0, "motor.turn_rate.pivot_optional", "optional pivot mode can still spin in place when explicitly enabled", {"left": left, "right": right})
    finally:
        close_motor(motor)

    motor = MotorService({"steering_mode": "arcade_mix", "steer_mix": 1.0}, hardware_enabled=False)
    try:
        left, right = motor.update(steering=1.0, throttle=0.40)
        ok &= line(left < 0.0 and right > 0.0, "motor.arcade_mix.fallback", "old arcade mixer remains available as fallback", {"left": left, "right": right})
    finally:
        close_motor(motor)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
