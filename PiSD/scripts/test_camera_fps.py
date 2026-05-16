#!/usr/bin/env python3
"""Measure direct PiSD camera-service FPS.

Safe by default: simulation mode unless --hardware is passed. This test exercises
CameraService directly, not HTTP, and prints simple OK/FAIL lines with PiSD codes.
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

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "camera_fps"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure direct PiSD camera-service FPS.")
    parser.add_argument("--hardware", action="store_true", help="Use real Picamera2 hardware.")
    parser.add_argument("--seconds", type=float, default=5.0, help="Measurement duration.")
    parser.add_argument("--fps", type=int, default=30, help="Target camera FPS.")
    parser.add_argument("--width", type=int, default=426, help="Preview width.")
    parser.add_argument("--height", type=int, default=240, help="Preview height.")
    parser.add_argument("--quality", type=int, default=50, help="JPEG quality.")
    parser.add_argument("--capture-source", choices=["request", "array"], default="array", help="Capture source to measure.")
    parser.add_argument("--array-color-order", default="rgb", help="Array colour order for capture_source=array.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(ok: bool, code: str, label: str, message: str) -> None:
    print(f"{'OK' if ok else 'FAIL':<4} {code:<13} {label} - {message}")


def main() -> int:
    args = parse_args()
    defaults = load_defaults()
    config: dict[str, Any] = dict(defaults.get("camera") or {})
    config.update(
        {
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "preview_quality": args.quality,
            "capture_source": args.capture_source,
            "array_color_order": args.array_color_order,
            "buffer_count": max(3, int(config.get("buffer_count", 3))),
            "queue": True,
        }
    )
    camera = CameraService(config, hardware_enabled=bool(args.hardware))
    started = False
    results: list[dict[str, Any]] = []
    try:
        ok, message = camera.start()
        started = ok
        emit(ok, PiSDErrorCodes.OK if ok else camera.last_error_code, "camera.start", message)
        if not ok:
            results.append({"label": "camera.start", "ok": False, "code": camera.last_error_code, "message": message})
            raise RuntimeError(message)
        first_seq = int(camera.status().get("frame_seq", 0))
        deadline = time.monotonic() + max(1.0, float(args.seconds))
        last_seq = first_seq
        received = 0
        while time.monotonic() < deadline:
            frame, seq, _timestamp, _bytes = camera.wait_for_jpeg_frame(last_seq=last_seq, timeout=1.0)
            if frame is not None and seq != last_seq:
                received += 1
                last_seq = seq
        stats = camera.get_fps_stats()
        measured = float(stats.get("measured_capture_fps") or 0.0)
        ok = received > 0 and measured > 0.0 and int(stats.get("last_frame_bytes") or 0) > 0
        code = PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_CAMERA_FPS_FAILED
        emit(ok, code, "camera.direct_fps", f"received={received} measured={measured:.2f} target={args.fps} encode_ms={stats.get('average_encode_ms')}")
        results.append({"label": "camera.direct_fps", "ok": ok, "code": code, "received": received, "stats": stats})
    except Exception as exc:
        code = PiSDErrorCodes.TEST_CAMERA_FPS_FAILED
        emit(False, code, "camera.direct_fps", str(exc))
        results.append({"label": "camera.direct_fps", "ok": False, "code": code, "message": str(exc)})
    finally:
        if started:
            ok, message = camera.stop()
            emit(ok, PiSDErrorCodes.OK if ok else camera.last_error_code, "camera.stop", message)

    failed = [item for item in results if not item.get("ok")]
    summary = {
        "ok": not failed,
        "code": PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_CAMERA_FPS_FAILED,
        "hardware_requested": bool(args.hardware),
        "config": config,
        "results": results,
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    emit(not failed, summary["code"], "summary", f"output={output}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
