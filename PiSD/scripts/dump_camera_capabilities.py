#!/usr/bin/env python3
"""Dump Picamera2/PiSD camera capability information.

Use this before tuning a new camera. It prints the Picamera2 camera_controls,
camera_properties, sensor modes, and the PiSD-supported setting keys.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import load_defaults  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.camera_service import CameraService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dump PiSD/Picamera2 camera capabilities.")
    parser.add_argument("--hardware", action="store_true", help="Open/query real Picamera2 hardware.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    defaults = load_defaults()
    camera = CameraService(defaults.get("camera", {}), hardware_enabled=args.hardware)
    capabilities = camera.get_capabilities()
    payload = {"code": capabilities.get("code", PiSDErrorCodes.OK), "capabilities": capabilities}
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    return 0 if payload["code"] == PiSDErrorCodes.OK else 1


if __name__ == "__main__":
    raise SystemExit(main())
