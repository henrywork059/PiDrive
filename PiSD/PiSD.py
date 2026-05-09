#!/usr/bin/env python3
"""PiSD main launcher.

PiSD is a clean sandbox for rebuilding and testing PiServer-style GUI and
runtime functions without modifying the existing PiServer component.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app, load_defaults  # noqa: E402
from pisd.core.errors import ErrorReporter, PiSDErrorCodes  # noqa: E402
from pisd.services.camera_service import CameraService  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PiSD hardware-service sandbox.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Use 0.0.0.0 on Pi LAN.")
    parser.add_argument("--port", type=int, default=5050, help="Port to bind.")
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Enable Raspberry Pi hardware adapters when Picamera2/RPi.GPIO are available. Default is safe simulation.",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Print service status JSON and exit without starting Flask.",
    )
    return parser.parse_args(argv)


def build_status_for_cli(hardware_enabled: bool) -> dict:
    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=hardware_enabled)
    motor = MotorService(defaults.get("motor"), hardware_enabled=hardware_enabled)
    try:
        return {
            "app": "PiSD",
            "code": PiSDErrorCodes.OK,
            "mode": "hardware" if hardware_enabled else "simulation",
            "camera": camera.status(),
            "motor": motor.status(),
        }
    finally:
        motor.close()
        camera.stop()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.status_only:
        print(json.dumps(build_status_for_cli(args.hardware), indent=2))
        return 0

    try:
        app = create_app(hardware_enabled=args.hardware)
    except RuntimeError as exc:
        reporter = ErrorReporter("launcher")
        report = reporter.report(PiSDErrorCodes.APP_STARTUP_FAILED, f"PiSD startup failed: {exc}", exc=exc)
        print(f"[PiSD] {report.code}: {report.message}", file=sys.stderr)
        print("[PiSD] You can still check service wiring with: python PiSD.py --status-only")
        return 2

    mode = "hardware-enabled" if args.hardware else "simulation-safe"
    print(f"[PiSD] Starting {mode} web sandbox at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
