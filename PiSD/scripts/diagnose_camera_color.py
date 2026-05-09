#!/usr/bin/env python3
"""Capture a small set of camera colour diagnostics.

This script is intended for the OV5647/Picamera2 colour debugging path. It saves
multiple JPEGs using different PiSD camera-service capture paths so the user can
compare whether the colour problem is caused by AWB/tuning or RGB/BGR array
encoding. Hardware testing showed 01_request_awb_auto and 91_array_rgb are
the correct references for this OV5647 setup.
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
    parser = argparse.ArgumentParser(description="Save PiSD camera colour diagnostic frames.")
    parser.add_argument("--hardware", action="store_true", help="Use the real Picamera2 camera path.")
    parser.add_argument("--seconds", type=float, default=2.5, help="Maximum wait per scenario.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "test_outputs" / "camera_color"))
    parser.add_argument("--format", default="BGR888", help="Picamera2 main stream format to test.")
    parser.add_argument("--include-rgb-format", action="store_true", help="Also test RGB888 request path.")
    parser.add_argument("--include-array-diagnostics", action="store_true", help="Also save array-path diagnostics. On this OV5647 setup, 91_array_rgb is the known-good array reference.")
    return parser.parse_args()


def capture_scenario(base_config: dict, hardware: bool, seconds: float, label: str, updates: dict, output_dir: Path) -> dict:
    config = dict(base_config)
    config.update(updates)
    camera = CameraService(config, hardware_enabled=hardware)
    started, message = camera.start()
    deadline = time.time() + max(0.5, seconds)
    frame = None
    while time.time() < deadline:
        frame = camera.get_jpeg_frame()
        if frame and int(camera.status().get("frame_seq", 0)) >= 2:
            break
        time.sleep(0.1)
    status = camera.status()
    output_path = output_dir / f"{label}.jpg"
    if frame:
        output_path.write_bytes(frame)
    camera.stop()
    return {
        "label": label,
        "ok": bool(started and frame),
        "message": message,
        "output": str(output_path) if frame else "",
        "code": status.get("last_error_code", PiSDErrorCodes.OK),
        "last_error": status.get("last_error", ""),
        "backend": status.get("backend"),
        "capture_source": status.get("last_capture_source"),
        "array_color_order": status.get("last_array_color_order"),
        "metadata": status.get("last_metadata", {}),
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    defaults = load_defaults()
    base_config = dict(defaults.get("camera", {}))
    base_config["format"] = args.format
    base_config["array_color_order"] = "rgb"

    scenarios = [
        (
            "01_request_awb_auto",
            {
                "capture_source": "request",
                "auto_white_balance": True,
                "awb_mode": "auto",
            },
        ),
        (
            "02_request_awb_daylight",
            {
                "capture_source": "request",
                "auto_white_balance": True,
                "awb_mode": "daylight",
            },
        ),
        (
            "03_request_awb_off_lock",
            {
                "capture_source": "request",
                "auto_white_balance": False,
                "awb_settle_seconds": 1.0,
                "colour_gains_red": 0.0,
                "colour_gains_blue": 0.0,
            },
        ),
    ]
    if args.include_array_diagnostics:
        scenarios.extend(
            [
                (
                    "90_array_auto_diagnostic_known_colour_risk",
                    {
                        "capture_source": "array",
                        "array_color_order": "auto",
                        "auto_white_balance": True,
                    },
                ),
                (
                    "91_array_rgb_confirmed_correct",
                    {
                        "capture_source": "array",
                        "array_color_order": "rgb",
                        "auto_white_balance": True,
                    },
                ),
                (
                    "92_array_bgr_diagnostic_known_colour_risk",
                    {
                        "capture_source": "array",
                        "array_color_order": "bgr",
                        "auto_white_balance": True,
                    },
                ),
            ]
        )
    if args.include_rgb_format:
        scenarios.append(
            (
                "06_request_rgb888_awb_auto",
                {
                    "format": "RGB888",
                    "capture_source": "request",
                    "auto_white_balance": True,
                    "awb_mode": "auto",
                },
            )
        )

    results = []
    for label, updates in scenarios:
        print(f"capturing {label} ...")
        results.append(capture_scenario(base_config, args.hardware, args.seconds, label, updates, output_dir))

    summary_path = output_dir / "summary.json"
    note = "01_request_awb_auto is the trusted visual reference. 91_array_rgb_confirmed_correct is the known-good raw array/CV reference for this OV5647 setup."
    summary_path.write_text(json.dumps({"note": note, "results": results}, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "summary": str(summary_path), "note": note, "results": results}, indent=2))

    if not all(item.get("ok") for item in results):
        print(f"{PiSDErrorCodes.TEST_CAMERA_COLOR_DIAGNOSTIC_FAILED}: at least one colour diagnostic frame failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
