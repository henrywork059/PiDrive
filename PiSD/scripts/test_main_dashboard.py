#!/usr/bin/env python3
"""Validate the PiSD main dashboard GUI shell.

This script is safe by default. It checks the first actual GUI dashboard shell,
required panel IDs, safety lock tokens, static assets, and Flask routes. It does
not arm or move motors.
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
TEMPLATE = WEB_ROOT / "templates" / "main_dashboard.html"
CSS = WEB_ROOT / "static" / "css" / "main_dashboard.css"
JS = WEB_ROOT / "static" / "js" / "main_dashboard.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "main_dashboard"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"

REQUIRED_TEMPLATE_TOKENS = [
    "PiSD Main Dashboard",
    "mainDashboardInitialStatus",
    "panel-system-status",
    "panel-camera-preview",
    "panel-manual-drive",
    "panel-motor-channel-calibration",
    "panel-safety-stop",
    "panel-error-monitor",
    "panel-action-log",
    "mdMotorArm",
    "mdStopAllTop",
    "mdStopAllCenter",
    "mdStopAllPanel",
    "mdOverlayToggle",
    "mdDriveOverlay",
    "mdOverlayThrottleValue",
    "mdOverlaySteeringValue",
]

REQUIRED_CSS_TOKENS = [
    ".md-shell",
    ".md-panel",
    ".md-panel-preview",
    ".md-big-stop",
    ".md-drive-overlay",
    ".md-overlay-car",
    "container-type: inline-size",
    "@media (max-width: 1100px)",
]

REQUIRED_JS_TOKENS = [
    "apiCall",
    "refreshStatus",
    "stopAll",
    "updateMotorLock",
    "sendManual",
    "sendChannelTest",
    "startLivePreview",
    "updateDriveOverlay",
    "setOverlayEnabled",
    "mdOverlayToggle",
    "/api/status",
    "/api/camera/start",
    "/api/camera/frame.jpg",
    "/video_feed",
    "/api/control/manual",
    "/api/motor/test-channel",
    "/api/control/stop",
    "PISD-MOT-008",
]


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
    parser = argparse.ArgumentParser(description="Validate the PiSD main dashboard GUI shell.")
    parser.add_argument("--hardware", action="store_true", help="Create app in hardware mode. Motors are never armed by this script.")
    parser.add_argument("--static-only", action="store_true", help="Only check files/source; skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": TEMPLATE, "css": CSS, "js": JS}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(
            Result(
                f"main_dashboard.file.{name}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
                f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
                {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
            )
        )
    return results


def check_source_contract() -> Result:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
    except Exception as exc:
        return Result(
            "main_dashboard.source_contract",
            False,
            PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
            f"failed to read dashboard files: {exc}",
            {"exception_type": type(exc).__name__},
        )

    missing = {
        "template": [token for token in REQUIRED_TEMPLATE_TOKENS if token not in template],
        "css": [token for token in REQUIRED_CSS_TOKENS if token not in css],
        "js": [token for token in REQUIRED_JS_TOKENS if token not in js],
    }
    missing = {key: value for key, value in missing.items() if value}
    ok = not missing
    return Result(
        "main_dashboard.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
        "main dashboard source includes required panels, safety lock, STOP actions, and API calls" if ok else "main dashboard source contract failed",
        {"missing": missing},
    )


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("main_dashboard.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]

    client = app.test_client()
    results: list[Result] = []

    response = client.get("/dashboard")
    root_ok = response.status_code == 200 and b"PiSD Main Dashboard" in response.data and b"panel-system-status" in response.data and b"Back to Front Page" in response.data
    results.append(
        Result(
            "main_dashboard.route.dashboard",
            root_ok,
            PiSDErrorCodes.OK if root_ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
            "/dashboard loads the actual main dashboard" if root_ok else f"/dashboard returned HTTP {response.status_code} or missing dashboard markers",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/testing")
    testing_ok = response.status_code == 200 and b"PiSD Testing Server GUI" in response.data
    results.append(
        Result(
            "main_dashboard.route.testing_still_available",
            testing_ok,
            PiSDErrorCodes.OK if testing_ok else PiSDErrorCodes.TEST_GUI_ROUTE_FAILED,
            "/testing remains available" if testing_ok else f"/testing returned HTTP {response.status_code}",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/panel-testing")
    panel_ok = response.status_code == 200 and b"PiSD Panel Testing Lab" in response.data
    results.append(
        Result(
            "main_dashboard.route.panel_testing_still_available",
            panel_ok,
            PiSDErrorCodes.OK if panel_ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
            "/panel-testing remains available" if panel_ok else f"/panel-testing returned HTTP {response.status_code}",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    for path, label, marker in (
        ("/testing/static/css/main_dashboard.css", "main_dashboard.static.css", b".md-drive-overlay"),
        ("/testing/static/js/main_dashboard.js", "main_dashboard.static.js", b"updateDriveOverlay"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(
            Result(
                label,
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )

    # STOP endpoint should work and is the only API action this dashboard test sends.
    response = client.post("/api/control/stop", json={})
    payload = response.get_json(silent=True) or {}
    stop_ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
    results.append(
        Result(
            "main_dashboard.api.stop_safe",
            stop_ok,
            payload.get("code") or PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
            "STOP API remains safe from dashboard test" if stop_ok else f"STOP API returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    for result in check_files():
        emit(result)
        results.append(result)
    result = check_source_contract()
    emit(result)
    results.append(result)
    if not args.static_only:
        for result in check_routes(bool(args.hardware)):
            emit(result)
            results.append(result)

    failed = [item for item in results if not item.ok]
    summary = {
        "ok": not failed,
        "code": PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
        "hardware_requested": bool(args.hardware),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": [item.as_dict() for item in results],
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
