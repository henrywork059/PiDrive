#!/usr/bin/env python3
"""Smoke-test the PiSD camera service.

Default mode is simulation. Add --hardware on a Raspberry Pi when the camera is
connected and Picamera2 is installed. This script can override the main camera
settings one at a time so the service/API path can be tested before a GUI exists.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

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


def _parse_scaler_crop(value: str) -> list[int]:
    try:
        values = [int(float(piece.strip())) for piece in value.split(",")]
    except Exception as exc:
        raise argparse.ArgumentTypeError("Use x,y,width,height format, for example 0,0,1280,720") from exc
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0 or values[0] < 0 or values[1] < 0:
        raise argparse.ArgumentTypeError("Use x,y,width,height with positive width/height")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD camera service frame capture and settings.")
    parser.add_argument("--hardware", action="store_true", help="Request real Picamera2 hardware path.")
    parser.add_argument("--seconds", type=float, default=3.0, help="Maximum time to wait for frames.")
    parser.add_argument("--min-frames", type=int, default=2, help="Minimum frame sequence count expected.")
    parser.add_argument("--width", type=int, help="Preview/capture width.")
    parser.add_argument("--height", type=int, help="Preview/capture height.")
    parser.add_argument("--fps", type=int, help="Target frames per second.")
    parser.add_argument("--format", default="", help="Override Picamera2 main stream format, e.g. BGR888 or RGB888.")
    parser.add_argument("--preview-quality", "--jpeg-quality", dest="preview_quality", type=int, help="JPEG quality 20-95.")
    parser.add_argument("--buffer-count", type=int, help="Picamera2 buffer_count for the video configuration.")
    parser.add_argument("--queue", action="store_true", help="Allow Picamera2 to queue/return the latest completed frame.")
    parser.add_argument("--no-queue", action="store_true", help="Disable Picamera2 queue mode; useful for fresher control tests.")
    parser.add_argument("--hflip", action="store_true", help="Apply horizontal flip at camera configuration time.")
    parser.add_argument("--vflip", action="store_true", help="Apply vertical flip at camera configuration time.")
    parser.add_argument(
        "--capture-source",
        choices=["request", "array"],
        default="",
        help="Use Picamera2 request/PIL JPEG path or raw array/OpenCV path. Request is the visual reference.",
    )
    parser.add_argument(
        "--array-color-order",
        choices=["auto", "bgr", "rgb", "bgra", "rgba", "swap_rb", "none"],
        default="",
        help="Colour interpretation for the raw array path. Array path is diagnostic/CV only.",
    )
    parser.add_argument("--manual-exposure", action="store_true", help="Disable auto exposure and apply exposure/gain.")
    parser.add_argument("--auto-exposure", action="store_true", help="Force auto exposure on.")
    parser.add_argument("--exposure-us", type=int, help="Manual exposure time in microseconds.")
    parser.add_argument("--analogue-gain", type=float, help="Manual analogue gain.")
    parser.add_argument("--exposure-compensation", type=float, help="Auto exposure compensation value.")
    parser.add_argument("--ae-metering-mode", default="", help="centre-weighted, spot, matrix, or custom.")
    parser.add_argument("--ae-exposure-mode", default="", help="normal, short, long, or custom.")
    parser.add_argument("--ae-constraint-mode", default="", help="normal, highlight, shadows, or custom.")
    parser.add_argument("--awb-off", action="store_true", help="Turn auto white balance off.")
    parser.add_argument("--awb-on", action="store_true", help="Force auto white balance on.")
    parser.add_argument("--awb-mode", default="", help="auto, daylight, cloudy, indoor, fluorescent, tungsten, incandescent.")
    parser.add_argument("--colour-gains", type=_parse_colour_gains, help="Manual AWB gains as R,B; also disables AWB.")
    parser.add_argument("--awb-settle-seconds", type=float, help="Delay after camera start before first checks.")
    parser.add_argument("--brightness", type=float, help="Brightness control, normally -1.0 to 1.0.")
    parser.add_argument("--contrast", type=float, help="Contrast control.")
    parser.add_argument("--saturation", type=float, help="Saturation control.")
    parser.add_argument("--sharpness", type=float, help="Sharpness control.")
    parser.add_argument("--noise-reduction-mode", default="", help="off, fast, high-quality, minimal, or zsl.")
    parser.add_argument("--scaler-crop", type=_parse_scaler_crop, help="Optional scaler crop as x,y,width,height.")
    parser.add_argument("--show-capabilities", action="store_true", help="Print camera capabilities before capture.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "test_outputs" / "camera_service_frame.jpg"),
        help="Path to save the latest JPEG frame.",
    )
    return parser.parse_args()


def apply_args_to_config(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if args.width is not None:
        config["width"] = args.width
    if args.height is not None:
        config["height"] = args.height
    if args.fps is not None:
        config["fps"] = args.fps
    if args.format:
        config["format"] = args.format
    if args.preview_quality is not None:
        config["preview_quality"] = args.preview_quality
    if args.buffer_count is not None:
        config["buffer_count"] = args.buffer_count
    if args.queue:
        config["queue"] = True
    if args.no_queue:
        config["queue"] = False
    if args.hflip:
        config["hflip"] = True
    if args.vflip:
        config["vflip"] = True
    if args.capture_source:
        config["capture_source"] = args.capture_source
    if args.array_color_order:
        config["array_color_order"] = args.array_color_order
    if args.manual_exposure:
        config["auto_exposure"] = False
    if args.auto_exposure:
        config["auto_exposure"] = True
    if args.exposure_us is not None:
        config["exposure_us"] = args.exposure_us
    if args.analogue_gain is not None:
        config["analogue_gain"] = args.analogue_gain
    if args.exposure_compensation is not None:
        config["exposure_compensation"] = args.exposure_compensation
    if args.ae_metering_mode:
        config["ae_metering_mode"] = args.ae_metering_mode
    if args.ae_exposure_mode:
        config["ae_exposure_mode"] = args.ae_exposure_mode
    if args.ae_constraint_mode:
        config["ae_constraint_mode"] = args.ae_constraint_mode
    if args.awb_on:
        config["auto_white_balance"] = True
    if args.awb_off:
        config["auto_white_balance"] = False
    if args.awb_mode:
        config["awb_mode"] = args.awb_mode
    if args.colour_gains is not None:
        red_gain, blue_gain = args.colour_gains
        config["auto_white_balance"] = False
        config["colour_gains_red"] = red_gain
        config["colour_gains_blue"] = blue_gain
    if args.awb_settle_seconds is not None:
        config["awb_settle_seconds"] = args.awb_settle_seconds
    if args.brightness is not None:
        config["brightness"] = args.brightness
    if args.contrast is not None:
        config["contrast"] = args.contrast
    if args.saturation is not None:
        config["saturation"] = args.saturation
    if args.sharpness is not None:
        config["sharpness"] = args.sharpness
    if args.noise_reduction_mode:
        config["noise_reduction_mode"] = args.noise_reduction_mode
    if args.scaler_crop is not None:
        config["scaler_crop"] = args.scaler_crop
    return config


def main() -> int:
    args = parse_args()
    defaults = load_defaults()
    camera_config = apply_args_to_config(dict(defaults.get("camera", {})), args)
    camera = CameraService(camera_config, hardware_enabled=args.hardware)

    if args.show_capabilities:
        print(json.dumps({"capabilities": camera.get_capabilities()}, indent=2))

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
    if status.get("last_error"):
        print(f"warning_code={status.get('last_error_code')} warning={status.get('last_error')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
