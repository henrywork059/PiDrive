from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config" / "servo_test.json"


@dataclass
class ServoTestConfig:
    enabled: bool = True
    backend: str = "pca9685"
    channels: int = 16
    i2c_address: int = 0x40
    frequency_hz: int = 50
    channel: int = 0
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


def load_config(path: Path = CONFIG_PATH) -> ServoTestConfig:
    cfg = ServoTestConfig()
    if not path.exists():
        return cfg

    raw = json.loads(path.read_text(encoding="utf-8"))
    for key in cfg.__dataclass_fields__:
        if key in raw:
            setattr(cfg, key, raw[key])

    cfg.i2c_address = _parse_i2c_address(cfg.i2c_address)
    cfg.channels = max(1, int(cfg.channels))
    cfg.channel = max(0, int(cfg.channel))
    cfg.frequency_hz = max(40, int(cfg.frequency_hz))
    cfg.cycles = max(1, int(cfg.cycles))
    cfg.step_delay_s = max(0.05, float(cfg.step_delay_s))
    cfg.settle_delay_s = max(0.0, float(cfg.settle_delay_s))
    cfg.test_min_angle = _clamp_angle(cfg.test_min_angle)
    cfg.test_mid_angle = _clamp_angle(cfg.test_mid_angle)
    cfg.test_max_angle = _clamp_angle(cfg.test_max_angle)
    return cfg


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone PCA9685 servo test for CustomDrive")
    parser.add_argument("--mode", choices=["info", "set", "sweep", "release"], default="sweep")
    parser.add_argument("--channel", type=int, help="Servo channel index on the PCA9685")
    parser.add_argument("--angle", type=float, help="Angle for --mode set")
    parser.add_argument("--min-angle", type=float, help="Minimum test angle for sweep")
    parser.add_argument("--mid-angle", type=float, help="Mid test angle for sweep")
    parser.add_argument("--max-angle", type=float, help="Maximum test angle for sweep")
    parser.add_argument("--cycles", type=int, help="Number of sweep cycles")
    parser.add_argument("--step-delay", type=float, help="Delay between test positions in seconds")
    parser.add_argument("--i2c-address", help="PCA9685 I2C address, e.g. 0x40")
    parser.add_argument("--frequency", type=int, help="PCA9685 PWM frequency in Hz")
    return parser


def apply_cli_overrides(cfg: ServoTestConfig, args: argparse.Namespace) -> ServoTestConfig:
    if args.channel is not None:
        cfg.channel = max(0, int(args.channel))
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
    return cfg


def build_servo_kit(cfg: ServoTestConfig):
    if not cfg.enabled:
        raise RuntimeError(
            "Servo test is disabled in config/servo_test.json. Set enabled=true before running the test."
        )
    if cfg.backend.lower() != "pca9685":
        raise RuntimeError(f"Unsupported backend: {cfg.backend!r}. Only 'pca9685' is supported here.")

    try:
        from adafruit_servokit import ServoKit
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'adafruit-circuitpython-servokit'. Install it with:\n"
            "python -m pip install adafruit-circuitpython-servokit"
        ) from exc

    try:
        return ServoKit(channels=cfg.channels, address=cfg.i2c_address, frequency=cfg.frequency_hz)
    except Exception as exc:
        raise RuntimeError(
            "Could not initialise the PCA9685. Check that I2C is enabled, the board is powered, and the address is correct.\n"
            f"Expected I2C address: 0x{cfg.i2c_address:02X}"
        ) from exc


def move_to_angle(servo, channel: int, angle: float, settle_delay_s: float = 0.0) -> None:
    angle = _clamp_angle(angle)
    print(f"[servo] channel={channel} -> angle={angle:.1f}")
    servo[channel].angle = angle
    if settle_delay_s > 0:
        time.sleep(settle_delay_s)


def release_servo(servo, channel: int) -> None:
    print(f"[servo] channel={channel} -> released (PWM disabled)")
    servo[channel].angle = None


def run_info_mode(cfg: ServoTestConfig) -> int:
    print("Servo test configuration")
    print(f"  config file : {CONFIG_PATH}")
    print(f"  backend     : {cfg.backend}")
    print(f"  channels    : {cfg.channels}")
    print(f"  i2c address : 0x{cfg.i2c_address:02X} ({cfg.i2c_address})")
    print(f"  frequency   : {cfg.frequency_hz} Hz")
    print(f"  channel     : {cfg.channel}")
    print(f"  sweep       : {cfg.test_min_angle:.1f} -> {cfg.test_mid_angle:.1f} -> {cfg.test_max_angle:.1f}")
    print(f"  step delay  : {cfg.step_delay_s:.2f} s")
    print(f"  cycles      : {cfg.cycles}")
    print()
    print("Suggested checks:")
    print("  1. sudo raspi-config  # enable I2C")
    print("  2. sudo i2cdetect -y 1  # look for 40")
    print("  3. python -m pip install adafruit-circuitpython-servokit")
    return 0


def run_set_mode(cfg: ServoTestConfig) -> int:
    kit = build_servo_kit(cfg)
    move_to_angle(kit.servo, cfg.channel, cfg.test_mid_angle, cfg.settle_delay_s)
    print("Done.")
    return 0


def run_release_mode(cfg: ServoTestConfig) -> int:
    kit = build_servo_kit(cfg)
    release_servo(kit.servo, cfg.channel)
    print("Done.")
    return 0


def run_sweep_mode(cfg: ServoTestConfig) -> int:
    kit = build_servo_kit(cfg)
    sequence = [cfg.test_min_angle, cfg.test_mid_angle, cfg.test_max_angle, cfg.test_mid_angle]
    print("Starting servo sweep test...")
    print(f"Using channel {cfg.channel} at PCA9685 address 0x{cfg.i2c_address:02X}")
    for cycle_idx in range(1, cfg.cycles + 1):
        print(f"Cycle {cycle_idx}/{cfg.cycles}")
        for angle in sequence:
            move_to_angle(kit.servo, cfg.channel, angle, cfg.settle_delay_s)
            time.sleep(cfg.step_delay_s)
    print("Sweep complete. Releasing servo output.")
    release_servo(kit.servo, cfg.channel)
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
        print("Servo test failed:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
