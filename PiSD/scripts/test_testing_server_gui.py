#!/usr/bin/env python3
"""Focused tests for the temporary PiSD testing server GUI.

This script is safe by default. It checks the static template/CSS/JS contract
without requiring hardware. When Flask is installed, it also checks the local
Flask routes with the test client. Real motor output is never armed by this
script; in hardware mode it expects the backend to refuse unarmed movement with
PISD-MOT-008.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
WEB_TEMPLATE = WEB_ROOT / "templates" / "testing_server.html"
WEB_CSS = WEB_ROOT / "static" / "css" / "testing_server.css"
WEB_JS = WEB_ROOT / "static" / "js" / "testing_server.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "testing_server_gui"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "ok": bool(self.ok),
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the PiSD testing server GUI files and local routes.")
    parser.add_argument("--hardware", action="store_true", help="Create the Flask app with hardware mode requested.")
    parser.add_argument("--static-only", action="store_true", help="Only check template/CSS/JS files; skip Flask routes.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_static_files() -> list[Result]:
    results: list[Result] = []
    files = {"template": WEB_TEMPLATE, "css": WEB_CSS, "js": WEB_JS}
    for name, path in files.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(
            Result(
                f"gui.file.{name}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
                f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
                {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
            )
        )
    return results


def check_source_contract() -> Result:
    try:
        template = WEB_TEMPLATE.read_text(encoding="utf-8")
        css = WEB_CSS.read_text(encoding="utf-8")
        js = WEB_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return Result("gui.source_contract", False, PiSDErrorCodes.TEST_GUI_ASSET_FAILED, f"failed to read GUI files: {exc}")

    expected = {
        "template": [
            "PiSD Testing Server GUI",
            "globalCode",
            "cameraPreview",
            "cameraSettingsForm",
            "motorSettingsForm",
            "motorChannelForm",
            "runSmokeTestBtn",
            "runSmokeTestBtn2",
            "smokeTestPanel",
            "initialStatusJson",
            "manifestJson",
        ],
        "css": [".code-pill", ".console", ".console.compact"],
        "js": [
            "runSafeSmokeTest",
            "/api/status",
            "/api/test-gui/manifest",
            "/api/camera/start",
            "/api/camera/frame.jpg",
            "/api/camera/apply",
            "/api/motor/apply",
            "/api/motor/test-channel",
            "/api/control/stop",
            "enable_motor_output: false",
            "PISD-MOT-008",
            "PISD-TEST-011",
        ],
    }
    sources = {"template": template, "css": css, "js": js}
    missing = {key: [token for token in tokens if token not in sources[key]] for key, tokens in expected.items()}
    missing = {key: value for key, value in missing.items() if value}
    ok = not missing
    return Result(
        "gui.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "GUI source includes required controls, smoke test, API paths, and safety code" if ok else "GUI source contract failed",
        {"missing": missing},
    )


def json_code(payload: dict[str, Any] | None, fallback: str) -> str:
    if isinstance(payload, dict) and payload.get("code"):
        return str(payload["code"])
    return fallback


def check_routes(hardware: bool) -> list[Result]:
    results: list[Result] = []
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("api.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]

    client = app.test_client()
    response = client.get("/testing")
    ok = response.status_code == 200 and b"PiSD Testing Server GUI" in response.data and b"Run safe smoke test" in response.data
    results.append(
        Result(
            "api.testing_gui.testing",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ROUTE_FAILED,
            "/testing loaded" if ok else f"/testing returned HTTP {response.status_code} or missing content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/")
    root_ok = response.status_code == 200 and b"PiSD Main Dashboard" in response.data
    results.append(
        Result(
            "api.testing_gui.root_separated",
            root_ok,
            PiSDErrorCodes.OK if root_ok else PiSDErrorCodes.TEST_GUI_ROUTE_FAILED,
            "/ now loads the main dashboard while /testing remains the API tester" if root_ok else f"/ returned HTTP {response.status_code} or missing main dashboard marker",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    for path, label, marker in (
        ("/testing/static/css/testing_server.css", "api.static.css", b".code-pill"),
        ("/testing/static/js/testing_server.js", "api.static.js", b"runSafeSmokeTest"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(
            Result(
                label,
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )

    response = client.get("/api/test-gui/manifest")
    payload = response.get_json(silent=True) or {}
    endpoints = {str(item.get("path")) for item in payload.get("endpoints") or [] if isinstance(item, dict)}
    required = {"/api/status", "/api/camera/start", "/api/camera/frame.jpg", "/api/camera/apply", "/api/motor/test-channel", "/api/control/stop"}
    known = payload.get("known_good_camera") or {}
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and required.issubset(endpoints) and known.get("array_color_order") == "rgb"
    results.append(
        Result(
            "api.manifest_contract",
            ok,
            json_code(payload, PiSDErrorCodes.TEST_GUI_API_CONTRACT_FAILED),
            "manifest includes required endpoints and known-good camera config" if ok else "manifest contract failed",
            {"http_status": response.status_code, "missing_endpoints": sorted(required - endpoints), "known_good_camera": known},
        )
    )

    response = client.post("/api/motor/test-channel", json={"side": "wrong", "direction": 1, "speed": 0.1, "duration": 0.05})
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 400 and payload.get("code") == PiSDErrorCodes.MOTOR_TEST_INVALID
    results.append(
        Result(
            "api.motor.invalid_channel_code",
            ok,
            json_code(payload, PiSDErrorCodes.MOTOR_TEST_INVALID),
            "invalid motor channel returns PISD-MOT-007" if ok else f"invalid motor channel returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )

    response = client.get("/missing-route-for-test")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 404 and payload.get("code") == PiSDErrorCodes.API_NOT_FOUND
    results.append(
        Result(
            "api.not_found_code",
            ok,
            json_code(payload, PiSDErrorCodes.API_NOT_FOUND),
            "unknown route returns PISD-API-003" if ok else f"unknown route returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )

    if hardware:
        response = client.post("/api/motor/test-channel", json={"side": "left", "direction": 1, "speed": 0.1, "duration": 0.05})
        payload = response.get_json(silent=True) or {}
        # On non-Pi systems --hardware may fall back to simulation, so accept either a real safety refusal or a safe simulation run.
        ok = (response.status_code == 403 and payload.get("code") == PiSDErrorCodes.MOTOR_TEST_UNARMED) or (
            response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and not payload.get("hardware_output_enabled", True)
        )
        results.append(
            Result(
                "api.motor.unarmed_hardware_safety",
                ok,
                json_code(payload, PiSDErrorCodes.MOTOR_TEST_UNARMED),
                "unarmed motor test refused or safely fell back to simulation" if ok else f"unarmed motor safety check returned HTTP {response.status_code}",
                {"http_status": response.status_code, "hardware_output_enabled": payload.get("hardware_output_enabled")},
            )
        )

    client.post("/api/control/stop")
    client.post("/api/camera/stop")
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_static_files())
    results.append(check_source_contract())
    if not args.static_only:
        results.extend(check_routes(bool(args.hardware)))

    for result in results:
        emit(result)

    failed = [result for result in results if not result.ok]
    summary = {
        "ok": not failed,
        "code": PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_GUI_API_CONTRACT_FAILED,
        "hardware_requested": bool(args.hardware),
        "static_only": bool(args.static_only),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": [result.as_dict() for result in results],
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("-" * 72)
    print(f"{'OK' if not failed else 'FAIL':<4} {summary['code']:<13} summary - passed={summary['passed']} failed={summary['failed']} output={output_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
