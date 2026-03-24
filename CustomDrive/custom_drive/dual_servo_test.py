from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config" / "dual_servo_test.json"


@dataclass
class DualServoTestConfig:
    enabled: bool = True
    backend: str = "pca9685"
    channels: int = 16
    i2c_address: int = 0x40
    frequency_hz: int = 50
    channel_a: int = 0
    channel_b: int = 1
    same_direction: bool = True
    channel_a_multiplier: float = 1.5
    test_min_angle: float = 40.0
    test_mid_angle: float = 90.0
    test_max_angle: float = 115.0
    step_delay_s: float = 0.7
    settle_delay_s: float = 0.4
    cycles: int = 3


def _parse_i2c_address(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        base = 16 if value.lower().startswith("0x") else 10
        return int(value, base)
    raise ValueError(f"Unsupported i2c_address value: {value!r}")


def _clamp_angle(value: float) -> float:
    return max(0.0, min(180.0, float(value)))


def load_config(path: Path = CONFIG_PATH) -> DualServoTestConfig:
    cfg = DualServoTestConfig()
    if not path.exists():
        return cfg

    raw = json.loads(path.read_text(encoding="utf-8"))
    for key in cfg.__dataclass_fields__:
        if key in raw:
            setattr(cfg, key, raw[key])

    cfg.i2c_address = _parse_i2c_address(cfg.i2c_address)
    cfg.channels = max(1, int(cfg.channels))
    cfg.channel_a = max(0, int(cfg.channel_a))
    cfg.channel_b = max(0, int(cfg.channel_b))
    cfg.frequency_hz = max(40, int(cfg.frequency_hz))
    cfg.cycles = max(1, int(cfg.cycles))
    cfg.step_delay_s = max(0.05, float(cfg.step_delay_s))
    cfg.settle_delay_s = max(0.0, float(cfg.settle_delay_s))
    cfg.test_min_angle = _clamp_angle(cfg.test_min_angle)
    cfg.test_mid_angle = _clamp_angle(cfg.test_mid_angle)
    cfg.test_max_angle = _clamp_angle(cfg.test_max_angle)
    cfg.same_direction = bool(cfg.same_direction)
    cfg.channel_a_multiplier = max(0.0, float(cfg.channel_a_multiplier))
    return cfg


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone dual PCA9685 servo test for CustomDrive")
    parser.add_argument("--mode", choices=["info", "set", "sweep", "release"], default="sweep")
    parser.add_argument("--channel-a", type=int, help="First servo channel index on the PCA9685")
    parser.add_argument("--channel-b", type=int, help="Second servo channel index on the PCA9685")
    parser.add_argument("--angle", type=float, help="Angle for --mode set")
    parser.add_argument("--min-angle", type=float, help="Minimum test angle for sweep")
    parser.add_argument("--mid-angle", type=float, help="Mid test angle for sweep")
    parser.add_argument("--max-angle", type=float, help="Maximum test angle for sweep")
    parser.add_argument("--cycles", type=int, help="Number of sweep cycles")
    parser.add_argument("--step-delay", type=float, help="Delay between test positions in seconds")
    parser.add_argument("--i2c-address", help="PCA9685 I2C address, e.g. 0x40")
    parser.add_argument("--frequency", type=int, help="PCA9685 PWM frequency in Hz")
    parser.add_argument("--channel-a-multiplier", type=float, help="Multiplier applied to channel A from the requested angle for channel B")
    parser.add_argument("--same-direction", dest="same_direction", action="store_true", help="Drive both servos to the same angle")
    parser.add_argument("--opposite-direction", dest="same_direction", action="store_false", help="Drive the second servo to the mirrored angle")
    parser.set_defaults(same_direction=None)
    return parser


def apply_cli_overrides(cfg: DualServoTestConfig, args: argparse.Namespace) -> DualServoTestConfig:
    if args.channel_a is not None:
        cfg.channel_a = max(0, int(args.channel_a))
    if args.channel_b is not None:
        cfg.channel_b = max(0, int(args.channel_b))
    if args.angle is not None:
        cfg.test_mid_angle = _clamp_angle(args.angle)
    if args.min_angle is not None:
        cfg.test_min_angle = _clamp_angle(args.min_angle)
    if args.mid_angle is not None:
        cfg.test_mid_angle = _clamp_angle(args.mid_angle)
    if args.max_angle is not None:
        cfg.test_max_angle = _clamp_angle(args.max_angle)
    if args.cycles is not None:
        cfg.cycles = max(1, int(args.cycles))
    if args.step_delay is not None:
        cfg.step_delay_s = max(0.05, float(args.step_delay))
    if args.i2c_address is not None:
        cfg.i2c_address = _parse_i2c_address(args.i2c_address)
    if args.frequency is not None:
        cfg.frequency_hz = max(40, int(args.frequency))
    if args.channel_a_multiplier is not None:
        cfg.channel_a_multiplier = max(0.0, float(args.channel_a_multiplier))
    if args.same_direction is not None:
        cfg.same_direction = bool(args.same_direction)
    return cfg


def build_servo_kit(cfg: DualServoTestConfig):
    if not cfg.enabled:
        raise RuntimeError(
            "Dual servo test is disabled in config/dual_servo_test.json. Set enabled=true before running the test."
        )
    if cfg.backend.lower() != "pca9685":
        raise RuntimeError(f"Unsupported backend: {cfg.backend!r}. Only 'pca9685' is supported here.")

    try:
        from adafruit_servokit import ServoKit
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'adafruit-circuitpython-servokit'. Install it with:\n"
            "python3 -m pip install --break-system-packages adafruit-circuitpython-servokit"
        ) from exc

    try:
        return ServoKit(channels=cfg.channels, address=cfg.i2c_address, frequency=cfg.frequency_hz)
    except Exception as exc:
        raise RuntimeError(
            "Could not initialise the PCA9685. Check that I2C is enabled, the board is powered, and the address is correct.\n"
            f"Expected I2C address: 0x{cfg.i2c_address:02X}"
        ) from exc


def _angle_pair(cfg: DualServoTestConfig, angle: float) -> tuple[float, float]:
    requested_angle = _clamp_angle(angle)
    angle_b = requested_angle
    if cfg.same_direction:
        angle_a = _clamp_angle(requested_angle * cfg.channel_a_multiplier)
    else:
        angle_a = _clamp_angle((180.0 - requested_angle) * cfg.channel_a_multiplier)
    return angle_a, angle_b


def move_to_angle_pair(servo, cfg: DualServoTestConfig, angle: float, settle_delay_s: float = 0.0) -> None:
    angle_a, angle_b = _angle_pair(cfg, angle)
    direction_label = "same" if cfg.same_direction else "opposite"
    print(
        f"[dual-servo] ch{cfg.channel_a} -> {angle_a:.1f} | ch{cfg.channel_b} -> {angle_b:.1f} "
        f"({direction_label} direction mode, {cfg.channel_a_multiplier:.3f}x scale on ch{cfg.channel_a})"
    )
    servo[cfg.channel_a].angle = angle_a
    servo[cfg.channel_b].angle = angle_b
    if settle_delay_s > 0:
        time.sleep(settle_delay_s)


def release_pair(servo, cfg: DualServoTestConfig) -> None:
    print(f"[dual-servo] released channels {cfg.channel_a} and {cfg.channel_b} (PWM disabled)")
    servo[cfg.channel_a].angle = None
    servo[cfg.channel_b].angle = None


def run_info_mode(cfg: DualServoTestConfig) -> int:
    print("Dual servo test configuration")
    print(f"  config file     : {CONFIG_PATH}")
    print(f"  backend         : {cfg.backend}")
    print(f"  channels        : {cfg.channels}")
    print(f"  i2c address     : 0x{cfg.i2c_address:02X} ({cfg.i2c_address})")
    print(f"  frequency       : {cfg.frequency_hz} Hz")
    print(f"  channel pair    : {cfg.channel_a} and {cfg.channel_b}")
    print(f"  direction mode  : {'same' if cfg.same_direction else 'opposite'}")
    print(f"  channel A scale : {cfg.channel_a_multiplier:.3f}x of channel B request")
    print(f"  sweep           : {cfg.test_min_angle:.1f} -> {cfg.test_mid_angle:.1f} -> {cfg.test_max_angle:.1f}")
    print(f"  step delay      : {cfg.step_delay_s:.2f} s")
    print(f"  cycles          : {cfg.cycles}")
    print()
    print("Suggested checks:")
    print("  1. sudo raspi-config  # enable I2C")
    print("  2. sudo i2cdetect -y 1  # look for 40")
    print("  3. python3 -m pip install --break-system-packages adafruit-circuitpython-servokit")
    return 0


def run_set_mode(cfg: DualServoTestConfig) -> int:
    kit = build_servo_kit(cfg)
    move_to_angle_pair(kit.servo, cfg, cfg.test_mid_angle, cfg.settle_delay_s)
    print("Done.")
    return 0


def run_release_mode(cfg: DualServoTestConfig) -> int:
    kit = build_servo_kit(cfg)
    release_pair(kit.servo, cfg)
    print("Done.")
    return 0


def run_sweep_mode(cfg: DualServoTestConfig) -> int:
    kit = build_servo_kit(cfg)
    sequence = [cfg.test_min_angle, cfg.test_mid_angle, cfg.test_max_angle, cfg.test_mid_angle]
    print("Starting dual servo sweep test...")
    print(
        f"Using channels {cfg.channel_a} and {cfg.channel_b} at PCA9685 address 0x{cfg.i2c_address:02X} "
        f"in {'same' if cfg.same_direction else 'opposite'} direction mode with "
        f"{cfg.channel_a_multiplier:.3f}x scale on channel {cfg.channel_a}"
    )
    for cycle_idx in range(1, cfg.cycles + 1):
        print(f"Cycle {cycle_idx}/{cfg.cycles}")
        for angle in sequence:
            move_to_angle_pair(kit.servo, cfg, angle, cfg.settle_delay_s)
            time.sleep(cfg.step_delay_s)
    print("Sweep complete. Releasing servo outputs.")
    release_pair(kit.servo, cfg)
    return 0


MODE_RUNNERS = {
    "info": run_info_mode,
    "set": run_set_mode,
    "sweep": run_sweep_mode,
    "release": run_release_mode,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        cfg = apply_cli_overrides(load_config(), args)
        runner = MODE_RUNNERS[args.mode]
        return runner(cfg)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        return 130
    except Exception as exc:
        print("Dual servo test failed:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
