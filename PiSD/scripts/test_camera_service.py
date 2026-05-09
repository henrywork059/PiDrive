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


def _parse_colour_gains(value: str) -> tuple[float, float]:
    try:
        red_text, blue_text = value.split(",", 1)
        return max(0.0, float(red_text)), max(0.0, float(blue_text))
    except Exception as exc:
        raise argparse.ArgumentTypeError("Use R,B format, for example 1.5,1.2") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD camera service frame capture.")
    parser.add_argument("--hardware", action="store_true", help="Request real Picamera2 hardware path.")
    parser.add_argument("--seconds", type=float, default=3.0, help="Maximum time to wait for frames.")
    parser.add_argument("--min-frames", type=int, default=2, help="Minimum frame sequence count expected.")
    parser.add_argument("--format", default="", help="Override Picamera2 main stream format, e.g. BGR888 or RGB888.")
    parser.add_argument(
        "--capture-source",
        choices=["request", "array"],
        default="",
        help="Use Picamera2 request/PIL JPEG path or raw array/OpenCV path.",
    )
    parser.add_argument(
        "--array-color-order",
        choices=["auto", "bgr", "rgb", "bgra", "rgba", "swap_rb", "none"],
        default="",
        help="Colour interpretation for the raw array path.",
    )
    parser.add_argument("--awb-off", action="store_true", help="Turn auto white balance off after the camera has settled.")
    parser.add_argument("--awb-mode", default="", help="AWB mode name such as daylight, cloudy, indoor, fluorescent.")
    parser.add_argument("--colour-gains", type=_parse_colour_gains, help="Manual AWB gains as R,B; also disables AWB.")
    parser.add_argument("--saturation", type=float, help="Override saturation control.")
    parser.add_argument("--contrast", type=float, help="Override contrast control.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "test_outputs" / "camera_service_frame.jpg"),
        help="Path to save the latest JPEG frame.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    defaults = load_defaults()
    camera_config = dict(defaults.get("camera", {}))
    if args.format:
        camera_config["format"] = args.format
    if args.capture_source:
        camera_config["capture_source"] = args.capture_source
    if args.array_color_order:
        camera_config["array_color_order"] = args.array_color_order
    if args.awb_mode:
        camera_config["awb_mode"] = args.awb_mode
    if args.awb_off:
        camera_config["auto_white_balance"] = False
    if args.colour_gains is not None:
        red_gain, blue_gain = args.colour_gains
        camera_config["auto_white_balance"] = False
        camera_config["colour_gains_red"] = red_gain
        camera_config["colour_gains_blue"] = blue_gain
    if args.saturation is not None:
        camera_config["saturation"] = args.saturation
    if args.contrast is not None:
        camera_config["contrast"] = args.contrast

    camera = CameraService(camera_config, hardware_enabled=args.hardware)

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
