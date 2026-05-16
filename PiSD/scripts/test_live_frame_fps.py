#!/usr/bin/env python3
"""Measure PiSD live-frame HTTP FPS.

Run PiSD.py in another terminal first. This script can measure either repeated
snapshot pulls from /api/camera/frame.jpg or the MJPEG /video_feed stream.
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

from pisd.core.errors import PiSDErrorCodes  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "live_frame_fps"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure PiSD HTTP live-frame FPS.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5050", help="PiSD server base URL.")
    parser.add_argument("--seconds", type=float, default=5.0, help="Measurement duration.")
    parser.add_argument("--mode", choices=["snapshot", "mjpeg"], default="mjpeg", help="Endpoint mode to measure.")
    parser.add_argument("--apply-fast-preview", action="store_true", help="Apply fast array/RGB preview preset before measuring.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(ok: bool, code: str, label: str, message: str) -> None:
    print(f"{'OK' if ok else 'FAIL':<4} {code:<13} {label} - {message}")


def url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def main() -> int:
    args = parse_args()
    try:
        import requests  # type: ignore
    except Exception as exc:
        emit(False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, "requests.import", str(exc))
        return 1

    results: list[dict[str, Any]] = []
    try:
        response = requests.post(url(args.base_url, "/api/camera/start"), json={}, timeout=5)
        payload = response.json()
        ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
        emit(ok, payload.get("code", PiSDErrorCodes.API_SERVICE_EXCEPTION), "api.camera.start", f"HTTP {response.status_code}")
        results.append({"label": "api.camera.start", "ok": ok, "status": response.status_code, "payload": payload})

        if args.apply_fast_preview:
            preset = {
                "width": 426,
                "height": 240,
                "fps": 30,
                "preview_quality": 50,
                "capture_source": "array",
                "array_color_order": "rgb",
                "buffer_count": 4,
                "queue": True,
            }
            response = requests.post(url(args.base_url, "/api/camera/apply"), json=preset, timeout=10)
            payload = response.json()
            ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
            emit(ok, payload.get("code", PiSDErrorCodes.API_SERVICE_EXCEPTION), "api.camera.apply_fast_preview", f"HTTP {response.status_code}")
            results.append({"label": "api.camera.apply_fast_preview", "ok": ok, "status": response.status_code, "payload": payload})

        before = requests.get(url(args.base_url, "/api/camera/fps-stats"), timeout=5).json()
        start = time.monotonic()
        frames = 0
        bytes_seen = 0
        failed = 0
        if args.mode == "snapshot":
            while time.monotonic() - start < max(1.0, float(args.seconds)):
                r = requests.get(url(args.base_url, f"/api/camera/frame.jpg?t={time.time_ns()}"), timeout=3)
                if r.status_code == 200 and r.content:
                    frames += 1
                    bytes_seen += len(r.content)
                else:
                    failed += 1
        else:
            boundary = b"--frame"
            with requests.get(url(args.base_url, "/video_feed"), stream=True, timeout=(5, max(5, int(args.seconds) + 5))) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        bytes_seen += len(chunk)
                        frames += chunk.count(boundary)
                    if time.monotonic() - start >= max(1.0, float(args.seconds)):
                        break
        elapsed = max(0.001, time.monotonic() - start)
        after = requests.get(url(args.base_url, "/api/camera/fps-stats"), timeout=5).json()
        measured = frames / elapsed
        ok = frames > 0 and failed == 0
        code = PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_CAMERA_FPS_FAILED
        emit(ok, code, f"http.{args.mode}_fps", f"frames={frames} fps={measured:.2f} bytes={bytes_seen} failed={failed}")
        results.append(
            {
                "label": f"http.{args.mode}_fps",
                "ok": ok,
                "code": code,
                "frames": frames,
                "elapsed": elapsed,
                "measured_http_fps": measured,
                "bytes": bytes_seen,
                "failed": failed,
                "before": before,
                "after": after,
            }
        )
    except Exception as exc:
        code = PiSDErrorCodes.TEST_CAMERA_FPS_FAILED
        emit(False, code, "http.live_frame_fps", str(exc))
        results.append({"label": "http.live_frame_fps", "ok": False, "code": code, "message": str(exc)})

    failed = [item for item in results if not item.get("ok")]
    summary: dict[str, Any] = {
        "ok": not failed,
        "code": PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_CAMERA_FPS_FAILED,
        "base_url": args.base_url,
        "mode": args.mode,
        "seconds": args.seconds,
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
