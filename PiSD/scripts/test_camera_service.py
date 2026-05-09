#!/usr/bin/env python3
"""Smoke-test the PiSD camera service.

Default mode is simulation. Add --hardware on a Raspberry Pi when the camera is
connected and Picamera2 is installed. The script captures at least one JPEG and
writes it to test_outputs/ by default.
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
from pisd.services.camera_service import CameraService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD camera service frame capture.")
    parser.add_argument("--hardware", action="store_true", help="Request real Picamera2 hardware path.")
    parser.add_argument("--seconds", type=float, default=3.0, help="Maximum time to wait for frames.")
    parser.add_argument("--min-frames", type=int, default=2, help="Minimum frame sequence count expected.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "test_outputs" / "camera_service_frame.jpg"),
        help="Path to save the latest JPEG frame.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=args.hardware)

    ok, message = camera.start()
    print(f"start_ok={ok} message={message}")
    deadline = time.time() + max(0.5, args.seconds)
    latest = None
    while time.time() < deadline:
        latest = camera.get_jpeg_frame()
        status = camera.status()
        if latest and int(status.get("frame_seq", 0)) >= args.min_frames:
            break
        time.sleep(0.1)

    status = camera.status()
    if latest:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(latest)
        print(f"saved_frame={output}")
    print(json.dumps(status, indent=2))
    camera.stop()

    if not latest:
        print(f"{PiSDErrorCodes.TEST_CAMERA_FRAME_MISSING}: no JPEG frame was produced.", file=sys.stderr)
        return 1
    if int(status.get("frame_seq", 0)) < args.min_frames:
        print(f"{PiSDErrorCodes.TEST_CAMERA_FRAME_MISSING}: frame sequence did not reach the expected minimum.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
