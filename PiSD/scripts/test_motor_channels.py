#!/usr/bin/env python3
"""Calibrate PiSD motors one side, one raw direction, one speed at a time.

Default mode is simulation-only. Real GPIO movement requires BOTH:

    --hardware --enable-motor-output

When real output is enabled, the script prompts before movement unless --yes is
used. Keep the wheels lifted and be ready to cut motor power.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
# PiSD_0_4_1 cleanup: Iterable was left over from an earlier CLI batching draft and is not used.
# from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import load_defaults  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.motor_service import MotorService, motor_side_name, normalize_test_direction  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "motor_channels"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


def _pin_pair(value: str) -> list[int]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("pin pair must be two BCM pins, for example 17,27")
    try:
        return [int(parts[0]), int(parts[1])]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("pins must be integers") from exc


def _float_list(value: str) -> list[float]:
    items: list[float] = []
    for part in value.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            parsed = float(text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("speeds must be comma-separated numbers") from exc
        if parsed <= 0 or parsed > 1:
            raise argparse.ArgumentTypeError("speeds must be in the range 0 < speed <= 1")
        items.append(parsed)
    if not items:
        raise argparse.ArgumentTypeError("at least one speed is required")
    return items


def _side_list(value: str) -> list[str]:
    sides = [motor_side_name(part) for part in value.split(",") if part.strip()]
    invalid = [side for side in sides if side not in {"left", "right"}]
    if invalid or not sides:
        raise argparse.ArgumentTypeError("sides must be left, right, or left,right")
    return sides


def _direction_list(value: str) -> list[int]:
    directions: list[int] = []
    for part in value.split(","):
        text = part.strip()
        if not text:
            continue
        directions.append(normalize_test_direction(text, 1))
    if not directions:
        raise argparse.ArgumentTypeError("at least one direction is required")
    return directions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD motor channels one by one for car-specific calibration.")
    parser.add_argument("--hardware", action="store_true", help="Request real GPIO adapter.")
    parser.add_argument(
        "--enable-motor-output",
        action="store_true",
        help="Actually send PWM to GPIO pins. Use only with wheels lifted and low power.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Do not prompt before each real movement. Still requires --hardware --enable-motor-output.",
    )
    parser.add_argument("--sides", type=_side_list, default=["left", "right"], help="Comma list: left,right,left or right.")
    parser.add_argument("--directions", type=_direction_list, default=[1, -1], help="Comma list: 1,2 or direction_1,direction_2.")
    parser.add_argument("--speeds", type=_float_list, default=[0.12, 0.2, 0.3], help="Comma list of test speeds, e.g. 0.12,0.2,0.3.")
    parser.add_argument("--duration", type=float, default=0.35, help="Seconds to run each individual motor command.")
    parser.add_argument("--pause", type=float, default=0.35, help="Seconds to wait after each automatic stop.")
    parser.add_argument("--left-pins", type=_pin_pair, help="Override left motor BCM pins, e.g. 17,27.")
    parser.add_argument("--right-pins", type=_pin_pair, help="Override right motor BCM pins, e.g. 22,23.")
    parser.add_argument("--pwm-frequency-hz", type=int, help="Override PWM frequency, e.g. 1000.")
    parser.add_argument("--left-direction", type=int, choices=(-1, 1), help="Temporarily set left logical direction multiplier.")
    parser.add_argument("--right-direction", type=int, choices=(-1, 1), help="Temporarily set right logical direction multiplier.")
    parser.add_argument(
        "--apply-config-direction",
        action="store_true",
        help="Apply left_direction/right_direction during the single-motor tests. Default is raw pin direction.",
    )
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def _direction_label(direction: int) -> str:
    return "direction_1" if direction > 0 else "direction_2"


def _confirm(real_output: bool, yes: bool, side: str, direction: int, speed: float, duration: float) -> bool:
    if not real_output or yes:
        return True
    prompt = (
        f"About to run {side} motor {_direction_label(direction)} at speed {speed:.2f} "
        f"for {duration:.2f}s. Wheels lifted? Type RUN to continue, or Enter to skip: "
    )
    try:
        return input(prompt).strip().upper() == "RUN"
    except EOFError:
        return False


def main() -> int:
    args = parse_args()
    real_output = bool(args.hardware and args.enable_motor_output)
    if args.hardware and not args.enable_motor_output:
        print("Hardware requested, but real motor output is disabled. Add --enable-motor-output to move motors.")
    if real_output:
        print("SAFETY: lift the wheels and keep motor power reachable. Each step stops automatically.")

    defaults = load_defaults()
    config = dict(defaults.get("motor") or {})
    if args.left_pins:
        config["left_pins"] = args.left_pins
    if args.right_pins:
        config["right_pins"] = args.right_pins
    if args.pwm_frequency_hz:
        config["pwm_frequency_hz"] = args.pwm_frequency_hz
    if args.left_direction is not None:
        config["left_direction"] = args.left_direction
    if args.right_direction is not None:
        config["right_direction"] = args.right_direction

    motor = MotorService(config, hardware_enabled=real_output)
    results: list[dict] = []
    failures: list[dict] = []

    try:
        for side in args.sides:
            for direction in args.directions:
                for speed in args.speeds:
                    label = f"{side}_{_direction_label(direction)}_{speed:.2f}"
                    if not _confirm(real_output, args.yes, side, direction, speed, args.duration):
                        item = {
                            "label": label,
                            "side": side,
                            "direction": direction,
                            "direction_label": _direction_label(direction),
                            "speed": speed,
                            "skipped": True,
                            "reason": "user did not confirm movement",
                        }
                        results.append(item)
                        print(json.dumps(item))
                        continue
                    result = motor.test_motor_channel(
                        side,
                        direction=direction,
                        speed=speed,
                        duration=args.duration,
                        apply_config_direction=args.apply_config_direction,
                    )
                    item = {
                        "label": label,
                        "observe": f"Only the {side} motor should rotate in {_direction_label(direction)}, then stop.",
                    }
                    item.update(result)
                    results.append(item)
                    print(json.dumps(item))
                    if not result.get("ok"):
                        failures.append(item)
                    time.sleep(max(0.0, args.pause))
        motor.stop()
        final_status = motor.status()
    finally:
        motor.close()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "ok": not failures,
        "code": PiSDErrorCodes.OK if not failures else PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED,
        "hardware_output_enabled": real_output,
        "apply_config_direction": bool(args.apply_config_direction),
        "speeds": args.speeds,
        "directions": [_direction_label(d) for d in args.directions],
        "sides": args.sides,
        "results": results,
        "failures": failures,
        "final_status": final_status,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(output_path), "code": summary["code"], "ok": summary["ok"]}, indent=2))

    if abs(final_status.get("last_left", 0.0)) > 1e-6 or abs(final_status.get("last_right", 0.0)) > 1e-6:
        print(f"{PiSDErrorCodes.TEST_MOTOR_STOP_FAILED}: motor status did not stop cleanly.", file=sys.stderr)
        return 1
    if failures:
        print(f"{PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED}: one or more channel tests failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
