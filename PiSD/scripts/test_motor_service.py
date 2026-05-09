#!/usr/bin/env python3
"""Smoke-test PiSD motor mapping and optional real GPIO output.

By default this script is simulation-only. On the Raspberry Pi, real PWM output
requires BOTH --hardware and --enable-motor-output so accidental wheel movement
is less likely during service testing.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import load_defaults  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402


def _pin_pair(value: str) -> list[int]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("pin pair must be two BCM pins, for example 17,27")
    try:
        return [int(parts[0]), int(parts[1])]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("pins must be integers") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD motor service mapping and optional real output.")
    parser.add_argument("--hardware", action="store_true", help="Request real GPIO adapter.")
    parser.add_argument(
        "--enable-motor-output",
        action="store_true",
        help="Actually send PWM to GPIO pins. Use only with wheels lifted and low power.",
    )
    parser.add_argument("--duration", type=float, default=0.25, help="Seconds to hold each test command.")
    parser.add_argument("--throttle", type=float, default=0.18, help="Small throttle used for the forward/reverse checks.")
    parser.add_argument("--steering", type=float, default=0.35, help="Small steering value used for mix checks.")
    parser.add_argument("--left-pins", type=_pin_pair, help="Override left motor BCM pins, e.g. 17,27.")
    parser.add_argument("--right-pins", type=_pin_pair, help="Override right motor BCM pins, e.g. 22,23.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    real_output = bool(args.hardware and args.enable_motor_output)
    if args.hardware and not args.enable_motor_output:
        print("Hardware requested, but real motor output is disabled. Add --enable-motor-output to move motors.")

    defaults = load_defaults()
    config = dict(defaults.get("motor") or {})
    if args.left_pins:
        config["left_pins"] = args.left_pins
    if args.right_pins:
        config["right_pins"] = args.right_pins

    motor = MotorService(config, hardware_enabled=real_output)
    commands = [
        (0.0, args.throttle, "forward-low"),
        (args.steering, args.throttle, "forward-steer-right"),
        (-args.steering, args.throttle, "forward-steer-left"),
        (0.0, -abs(args.throttle), "reverse-low"),
        (0.0, 0.0, "stop"),
    ]

    results = []
    try:
        for steering, throttle, label in commands:
            left, right = motor.update(steering=steering, throttle=throttle)
            item = {
                "label": label,
                "steering": steering,
                "throttle": throttle,
                "left": left,
                "right": right,
                "hardware_output_enabled": real_output,
            }
            results.append(item)
            print(json.dumps(item))
            time.sleep(max(0.05, args.duration))
        motor.stop()
        status = motor.status()
    finally:
        motor.close()

    print(json.dumps({"results": results, "final_status": status}, indent=2))
    if abs(status.get("last_left", 0.0)) > 1e-6 or abs(status.get("last_right", 0.0)) > 1e-6:
        print(f"{PiSDErrorCodes.TEST_MOTOR_STOP_FAILED}: motor status did not stop cleanly.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
