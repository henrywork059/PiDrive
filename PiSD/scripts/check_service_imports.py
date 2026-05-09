#!/usr/bin/env python3
"""Check PiSD service imports and default wiring.

This script does not open the camera or move motors. It verifies that the
PiSD service modules, default config, and Flask app factory can be imported.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _optional_import(module_name: str) -> dict[str, Any]:
    try:
        __import__(module_name)
        return {"available": True, "error": ""}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check PiSD service imports and app wiring.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if Flask app creation is unavailable.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from pisd import __version__
    from pisd.app import create_app, load_defaults
    from pisd.core.errors import PiSDErrorCodes
    from pisd.services.camera_service import CameraService
    from pisd.services.motor_service import MotorService

    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=False)
    motor = MotorService(defaults.get("motor"), hardware_enabled=False)
    app_created = False
    app_error = ""
    try:
        app = create_app(hardware_enabled=False)
        app_created = app is not None
    except RuntimeError as exc:
        app_error = str(exc)

    optional_modules = {
        "flask": _optional_import("flask"),
        "requests": _optional_import("requests"),
        "numpy": _optional_import("numpy"),
        "cv2": _optional_import("cv2"),
        "PIL": _optional_import("PIL"),
        "picamera2": _optional_import("picamera2"),
        "RPi.GPIO": _optional_import("RPi.GPIO"),
    }

    report = {
        "app": "PiSD",
        "code": PiSDErrorCodes.OK,
        "version": __version__,
        "project_root": str(PROJECT_ROOT),
        "defaults_loaded": bool(defaults),
        "flask_app_created": app_created,
        "flask_app_error": app_error,
        "camera_status": camera.status(),
        "motor_status": motor.status(),
        "optional_modules": optional_modules,
    }

    motor.close()
    camera.stop()
    print(json.dumps(report, indent=2))

    if args.strict and not app_created:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
