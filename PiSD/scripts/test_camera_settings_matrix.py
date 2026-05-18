#!/usr/bin/env python3
"""Run a matrix of camera setting changes through the PiSD CameraService.

The default matrix uses the request/PIL path. Hardware colour checks showed
03_request_awb_off_lock is the current default for visual capture and 91_array_rgb is correct
for raw array/CV interpretation on this OV5647 setup. Add
--include-array-diagnostics only when intentionally retesting raw-array colour
interpretation.
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD camera setting matrix.")
    parser.add_argument("--hardware", action="store_true", help="Use real Picamera2 hardware.")
    parser.add_argument("--seconds", type=float, default=2.5, help="Wait time per scenario.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "test_outputs" / "camera_settings"))
    parser.add_argument("--include-array-diagnostics", action="store_true", help="Also test raw array capture modes. These may show wrong colour and are not the visual reference.")
    return parser.parse_args()


def capture_one(base_config: dict[str, Any], label: str, updates: dict[str, Any], hardware: bool, seconds: float, output_dir: Path) -> dict[str, Any]:
    config = dict(base_config)
    config.update(updates)
    camera = CameraService(config, hardware_enabled=hardware)
    ok, message = camera.start()
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
        "ok": bool(ok and frame),
        "message": message,
        "output": str(output_path) if frame else "",
        "settings": updates,
        "code": status.get("last_error_code", PiSDErrorCodes.OK),
        "last_error": status.get("last_error", ""),
        "backend": status.get("backend"),
        "capture_source": status.get("last_capture_source"),
        "frame_seq": status.get("frame_seq"),
        "last_metadata": status.get("last_metadata", {}),
        "last_applied_controls": status.get("last_applied_controls", {}),
        "last_video_config": status.get("last_video_config", {}),
        "recent_errors": status.get("recent_errors", []),
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    defaults = load_defaults()
    base_config = dict(defaults.get("camera", {}))
    base_config["capture_source"] = "request"
    base_config["array_color_order"] = "rgb"

    scenarios: list[tuple[str, dict[str, Any]]] = [
        ("01_request_default", {"capture_source": "request", "auto_exposure": True, "auto_white_balance": True}),
        ("02_size_quality_buffer", {"width": 320, "height": 240, "fps": 15, "preview_quality": 55, "buffer_count": 2, "queue": False}),
        ("03_manual_exposure_gain", {"auto_exposure": False, "exposure_us": 8000, "analogue_gain": 1.5}),
        ("04_exposure_compensation_matrix", {"auto_exposure": True, "exposure_compensation": 0.5, "ae_metering_mode": "matrix", "ae_exposure_mode": "normal"}),
        ("05_awb_daylight", {"auto_white_balance": True, "awb_mode": "daylight"}),
        ("06_manual_colour_gains", {"auto_white_balance": False, "colour_gains_red": 1.8, "colour_gains_blue": 1.2}),
        ("07_image_controls", {"brightness": 0.05, "contrast": 1.2, "saturation": 1.2, "sharpness": 1.1}),
        ("08_flip_noise_reduction", {"hflip": True, "vflip": False, "noise_reduction_mode": "fast"}),
    ]
    if args.include_array_diagnostics:
        scenarios.extend(
            [
                ("09_array_auto_diagnostic", {"capture_source": "array", "array_color_order": "auto"}),
                ("10_array_rgb_confirmed_correct", {"capture_source": "array", "array_color_order": "rgb"}),
                ("11_array_bgr_diagnostic", {"capture_source": "array", "array_color_order": "bgr"}),
            ]
        )

    results = []
    for label, updates in scenarios:
        print(f"running {label} ...")
        results.append(capture_one(base_config, label, updates, args.hardware, args.seconds, output_dir))

    payload = {
        "code": PiSDErrorCodes.OK if all(item["ok"] for item in results) else PiSDErrorCodes.TEST_CAMERA_SETTINGS_MATRIX_FAILED,
        "note": "Request/PIL frames are the visual reference. array_color_order=rgb is the known-good raw array/CV setting from the 91 colour test.",
        "output_dir": str(output_dir),
        "results": results,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), **payload}, indent=2))
    return 0 if payload["code"] == PiSDErrorCodes.OK else 1


if __name__ == "__main__":
    raise SystemExit(main())
