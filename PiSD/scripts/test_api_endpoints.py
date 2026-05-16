#!/usr/bin/env python3
"""Test PiSD Flask API wiring with Flask's local test client.

This checks the service calls without starting a network server. Default mode is
simulation, so it is safe on a PC and on a Pi.
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

from pisd.app import create_app  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD API endpoints through Flask test client.")
    parser.add_argument("--hardware", action="store_true", help="Request hardware adapters in app factory.")
    return parser.parse_args()


def _expect(response, expected_status: int = 200):
    if response.status_code != expected_status:
        raise AssertionError(f"{response.request.path} returned {response.status_code}, expected {expected_status}")
    if response.content_type.startswith("application/json"):
        payload = response.get_json() or {}
        if "code" not in payload:
            raise AssertionError(f"{response.request.path} JSON response is missing a PiSD code field")
    return response


def main() -> int:
    args = parse_args()
    try:
        app = create_app(hardware_enabled=args.hardware)
    except RuntimeError as exc:
        print(f"{PiSDErrorCodes.APP_DEPENDENCY_MISSING}: {exc}", file=sys.stderr)
        print("Install dependencies first: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    client = app.test_client()

    results = []

    res = _expect(client.get("/api/status"))
    results.append({"endpoint": "GET /api/status", "status": res.status_code, "json": res.get_json()})


    res = _expect(client.get("/"))
    if b"PiSD Front Page" not in res.data or b"frontModeSettings" not in res.data or b"frontModeTesting" not in res.data:
        raise AssertionError("GET / did not return the front page mode selector")
    results.append({"endpoint": "GET /", "status": res.status_code, "bytes": len(res.data)})

    res = _expect(client.get("/settings"))
    if b"PiSD Settings Tab" not in res.data or b"Back to Front Page" not in res.data:
        raise AssertionError("GET /settings did not return the settings tab page")
    results.append({"endpoint": "GET /settings", "status": res.status_code, "bytes": len(res.data)})

    res = _expect(client.get("/dashboard"))
    if b"PiSD Main Dashboard" not in res.data or b"panel-system-status" not in res.data or b"Back to Front Page" not in res.data:
        raise AssertionError("GET /dashboard did not return the main dashboard page")
    results.append({"endpoint": "GET /dashboard", "status": res.status_code, "bytes": len(res.data)})

    res = _expect(client.get("/testing"))
    if b"PiSD Testing Server GUI" not in res.data or b"Run safe smoke test" not in res.data:
        raise AssertionError("GET /testing did not return the testing GUI page with smoke test controls")
    results.append({"endpoint": "GET /testing", "status": res.status_code, "bytes": len(res.data)})

    for path, marker in (("/testing/static/css/front_page.css", b".fp-mode-grid"), ("/testing/static/js/front_page.js", b"frontApi"), ("/testing/static/css/settings_tab.css", b".st-grid"), ("/testing/static/js/settings_tab.js", b"settingsApi"), ("/testing/static/css/main_dashboard.css", b".md-shell"), ("/testing/static/js/main_dashboard.js", b"updateMotorLock"), ("/testing/static/css/testing_server.css", b".code-pill"), ("/testing/static/js/testing_server.js", b"runSafeSmokeTest")):
        res = _expect(client.get(path))
        if marker not in res.data:
            raise AssertionError(f"GET {path} did not contain expected testing GUI asset marker")
        results.append({"endpoint": f"GET {path}", "status": res.status_code, "bytes": len(res.data)})

    res = _expect(client.get("/api/test-gui/manifest"))
    manifest_json = res.get_json() or {}
    manifest_paths = {str(item.get("path")) for item in manifest_json.get("endpoints") or [] if isinstance(item, dict)}
    required_paths = {"/api/status", "/api/camera/start", "/api/camera/frame.jpg", "/api/camera/apply", "/api/motor/test-channel", "/api/control/stop"}
    known_good = manifest_json.get("known_good_camera") or {}
    if manifest_json.get("code") != PiSDErrorCodes.OK or not required_paths.issubset(manifest_paths) or known_good.get("array_color_order") != "rgb":
        raise AssertionError("GET /api/test-gui/manifest did not return required endpoint/camera contract")
    results.append({"endpoint": "GET /api/test-gui/manifest", "status": res.status_code, "json": manifest_json})

    res = _expect(client.post("/api/camera/start"))
    results.append({"endpoint": "POST /api/camera/start", "status": res.status_code, "json": res.get_json()})
    time.sleep(0.4)

    res = client.get("/api/camera/frame.jpg")
    if res.status_code != 200 or not res.data.startswith(b"\xff\xd8"):
        raise AssertionError("GET /api/camera/frame.jpg did not return a JPEG frame")
    results.append({"endpoint": "GET /api/camera/frame.jpg", "status": res.status_code, "bytes": len(res.data)})

    res = _expect(client.get("/api/motor/config"))
    results.append({"endpoint": "GET /api/motor/config", "status": res.status_code, "json": res.get_json()})

    res = _expect(client.get("/api/errors"))
    results.append({"endpoint": "GET /api/errors", "status": res.status_code, "json": res.get_json()})

    res = _expect(client.post("/api/motor/apply", data="not-json", content_type="application/json"), expected_status=400)
    invalid_json = res.get_json() or {}
    if invalid_json.get("code") != PiSDErrorCodes.API_INVALID_JSON:
        raise AssertionError("Invalid JSON response did not use PISD-API-001")
    results.append({"endpoint": "POST /api/motor/apply invalid JSON", "status": res.status_code, "json": invalid_json})

    res = _expect(client.post("/api/motor/test-channel", json={"side": "wrong", "direction": 1, "speed": 0.1, "duration": 0.05}), expected_status=400)
    invalid_channel = res.get_json() or {}
    if invalid_channel.get("code") != PiSDErrorCodes.MOTOR_TEST_INVALID:
        raise AssertionError("Invalid motor channel response did not use PISD-MOT-007")
    results.append({"endpoint": "POST /api/motor/test-channel invalid side", "status": res.status_code, "json": invalid_channel})

    res = _expect(client.get("/api/does-not-exist"), expected_status=404)
    not_found = res.get_json() or {}
    if not_found.get("code") != PiSDErrorCodes.API_NOT_FOUND:
        raise AssertionError("Missing route did not use PISD-API-003")
    results.append({"endpoint": "GET /api/does-not-exist", "status": res.status_code, "json": not_found})

    res = _expect(client.post("/api/motor/test-channel", json={"side": "left", "direction": 1, "speed": 0.05, "duration": 0.05}))
    channel_json = res.get_json() or {}
    results.append({"endpoint": "POST /api/motor/test-channel", "status": res.status_code, "json": channel_json})
    if channel_json.get("code") != PiSDErrorCodes.OK or channel_json.get("side") != "left":
        raise AssertionError("Motor channel test endpoint did not return a valid PiSD response")

    res = _expect(client.post("/api/control/manual", json={"steering": 0.25, "throttle": 0.2}))
    manual_json = res.get_json()
    results.append({"endpoint": "POST /api/control/manual", "status": res.status_code, "json": manual_json})
    if manual_json is None or "left" not in manual_json or "right" not in manual_json:
        raise AssertionError("Manual control response did not include left/right outputs")

    res = _expect(client.post("/api/control/stop"))
    stop_json = res.get_json()
    results.append({"endpoint": "POST /api/control/stop", "status": res.status_code, "json": stop_json})
    motor_status = (stop_json or {}).get("motor", {})
    if abs(motor_status.get("last_left", 0.0)) > 1e-6 or abs(motor_status.get("last_right", 0.0)) > 1e-6:
        raise AssertionError("Stop endpoint did not reset motor outputs to zero")

    res = _expect(client.post("/api/camera/stop"))
    results.append({"endpoint": "POST /api/camera/stop", "status": res.status_code, "json": res.get_json()})

    print(json.dumps({"ok": True, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
