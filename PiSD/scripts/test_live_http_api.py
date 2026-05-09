#!/usr/bin/env python3
"""Test a running PiSD server through HTTP requests.

Start PiSD in another terminal first, for example:
    python PiSD.py --host 0.0.0.0 --port 5050 --hardware

Motor movement calls are disabled unless --enable-motor-output is provided.
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

from pisd.core.errors import PiSDErrorCodes  # noqa: E402

try:
    import requests
except Exception as exc:  # pragma: no cover
    print(f"{PiSDErrorCodes.APP_DEPENDENCY_MISSING}: requests is not installed: {exc}", file=sys.stderr)
    print("Run: python -m pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD API endpoints over a running HTTP server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5050", help="PiSD server base URL.")
    parser.add_argument("--timeout", type=float, default=4.0, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--enable-motor-output",
        action="store_true",
        help="Send a small manual motor command to the running server. Use only when safe.",
    )
    return parser.parse_args()


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _json_with_code(response, path: str) -> dict:
    payload = response.json()
    if "code" not in payload:
        raise RuntimeError(f"{path} JSON response is missing a PiSD code field")
    return payload


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")
    results = []

    status = requests.get(_url(base, "/api/status"), timeout=args.timeout)
    status.raise_for_status()
    results.append({"endpoint": "GET /api/status", "status": status.status_code, "json": _json_with_code(status, "/api/status")})

    cam_start = requests.post(_url(base, "/api/camera/start"), timeout=args.timeout)
    cam_start.raise_for_status()
    results.append({"endpoint": "POST /api/camera/start", "status": cam_start.status_code, "json": _json_with_code(cam_start, "/api/camera/start")})
    time.sleep(0.5)

    frame = requests.get(_url(base, "/api/camera/frame.jpg"), timeout=args.timeout)
    frame.raise_for_status()
    if not frame.content.startswith(b"\xff\xd8"):
        raise RuntimeError("/api/camera/frame.jpg did not return JPEG bytes")
    results.append({"endpoint": "GET /api/camera/frame.jpg", "status": frame.status_code, "bytes": len(frame.content)})

    motor_config = requests.get(_url(base, "/api/motor/config"), timeout=args.timeout)
    motor_config.raise_for_status()
    results.append({"endpoint": "GET /api/motor/config", "status": motor_config.status_code, "json": _json_with_code(motor_config, "/api/motor/config")})

    invalid = requests.post(_url(base, "/api/motor/apply"), data="not-json", headers={"Content-Type": "application/json"}, timeout=args.timeout)
    if invalid.status_code != 400:
        raise RuntimeError("Invalid JSON check did not return HTTP 400")
    invalid_payload = _json_with_code(invalid, "/api/motor/apply")
    if invalid_payload.get("code") != PiSDErrorCodes.API_INVALID_JSON:
        raise RuntimeError("Invalid JSON check did not return PISD-API-001")
    results.append({"endpoint": "POST /api/motor/apply invalid JSON", "status": invalid.status_code, "json": invalid_payload})

    if args.enable_motor_output:
        manual = requests.post(
            _url(base, "/api/control/manual"),
            json={"steering": 0.0, "throttle": 0.15},
            timeout=args.timeout,
        )
        manual.raise_for_status()
        results.append({"endpoint": "POST /api/control/manual", "status": manual.status_code, "json": _json_with_code(manual, "/api/control/manual")})
        time.sleep(0.2)
    else:
        results.append({"endpoint": "POST /api/control/manual", "skipped": "add --enable-motor-output to send movement command"})

    stop = requests.post(_url(base, "/api/control/stop"), timeout=args.timeout)
    stop.raise_for_status()
    results.append({"endpoint": "POST /api/control/stop", "status": stop.status_code, "json": _json_with_code(stop, "/api/control/stop")})

    print(json.dumps({"ok": True, "base_url": base, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
