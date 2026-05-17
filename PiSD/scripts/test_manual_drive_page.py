#!/usr/bin/env python3
"""Validate PiSD Manual Drive page source and routes.

This test does not move motors. It checks that the user-facing manual drive page
has the camera preview, important status, drive pad safety lock, STOP controls,
and API calls needed for easy car control.
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
TEMPLATE = WEB_ROOT / "templates" / "manual_drive.html"
CSS = WEB_ROOT / "static" / "css" / "manual_drive.css"
JS = WEB_ROOT / "static" / "js" / "manual_drive.js"
GLOBAL_CSS = WEB_ROOT / "static" / "css" / "panel_presentation_global.css"
DESIGN_SYSTEM_CSS = WEB_ROOT / "static" / "css" / "pisd_design_system.css"
GLOBAL_JS = WEB_ROOT / "static" / "js" / "panel_presentation_global.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "manual_drive_page"
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
    parser = argparse.ArgumentParser(description="Validate PiSD Manual Drive page.")
    parser.add_argument("--hardware", action="store_true", help="Create Flask app in hardware mode. No movement commands are sent.")
    parser.add_argument("--static-only", action="store_true", help="Only check source files, skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": TEMPLATE, "css": CSS, "js": JS, "global_css": GLOBAL_CSS, "design_system_css": DESIGN_SYSTEM_CSS, "global_js": GLOBAL_JS}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(Result(
            f"manual_drive.file.{name}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        ))
    return results


def check_source_contract() -> list[Result]:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        global_css = (WEB_ROOT / "static" / "css" / "unified_layout.css").read_text(encoding="utf-8")
        layout_css = (WEB_ROOT / "static" / "css" / "pisd_layout_system.css").read_text(encoding="utf-8")
        design_css = DESIGN_SYSTEM_CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
    except Exception as exc:
        return [Result("manual_drive.source_contract", False, PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED, f"failed to read files: {exc}")]

    required_template = [
        "PiSD Manual Drive",
        "manual-drive-page",
        "Back to Front Page",
        "manualDriveCameraPanel",
        "manualDriveStatusPanel",
        "manualDrivePadPanel",
        "manualDriveStopPanel",
        "mdrvPreview",
        "mdrvArm",
        "mdrvStopBig",
        "mdrvCaptureFrame",
        "mdrvRecordToggle",
        "mdrvRecordingState",
        "mdrvRecordingIndicator",
        "mdrvCaptureNotice",
        "mdrvIntentOut",
        "mdrvMotorOut",
        "manualDriveFilesPanel",
        "mdrvFileKind",
        "mdrvFileSelect",
        "mdrvDownloadZip",
        "mdrvDeleteFolder",
        "manualDriveInitialStatus",
        "panel_presentation_global.css",
        "pisd_design_system.css",
        "panel_presentation_global.js",
        'data-panel-role="status"',
        'data-panel-role="preview"',
        "data-panel-h-weight",
    ]
    required_css = [".mdrv-shell", ".mdrv-panel", ".mdrv-status-panel", ".mdrv-preview-frame", ".mdrv-drag-pad", ".mdrv-big-stop", ".mdrv-drag-knob", "width: 28px", ".mdrv-recording-indicator", ".mdrv-capture-notice", "@media (max-width: 1100px)"]
    required_unified_css = [
        "PiSD 0.3.3 manual-drive semantic layout recovery",
        "body.manual-drive-page .mdrv-shell",
    ]
    required_layout_css = [
        "body.manual-drive-page .mdrv-shell",
        "\"status status\"",
        "\"preview drive\"",
        "\"preview files\"",
        "#manualDriveFilesPanel",
    ]
    required_design_css = [
        "PiSD Design System",
        "body.manual-drive-page .mdrv-shell",
        "\"status drive\"",
        "\"preview drive\"",
        "#manualDriveStatusPanel",
        "#manualDriveCameraPanel",
        "#manualDrivePadPanel",
        "#manualDriveFilesPanel",
        "grid-area: status",
        "grid-area: preview",
        "grid-area: drive",
        "presentation consolidation",
        "--pisd-palette-recording",
        "mdrv-recording-indicator",
        "mdrv-capture-notice",
    ]
    required_js = [
        "manualDriveInitialStatus",
        "pisd.manualDrive.v1",
        "pisd.runtimeSettings.v2",
        "/api/status",
        "/api/camera/start",
        "/video_feed",
        "/api/control/manual",
        "/api/control/stop",
        "/api/recording/capture",
        "/api/recording/start",
        "/api/recording/stop",
        "/api/recording/items",
        "/api/recording/download.zip",
        "/api/recording/delete",
        "PISD-MOT-008",
        "showCaptureNotice",
        "updateRecordingIndicator",
        "updateLock",
        "pointerdown",
        "pointermove",
        "startCameraOnly",
        "startLiveCamera",
        "currentPreviewMode",
        "refreshStatus(true)",
        "setShortStatus",
        "renderMotorSignals",
        "renderMotorSignalsFromApiResponse",
        "mdrvIntentOut",
        "mdrvMotorOut",
    ]
    missing = {
        "template": [token for token in required_template if token not in template],
        "css": [token for token in required_css if token not in css],
        "unified_css": [token for token in required_unified_css if token not in global_css],
        "layout_system_css": [token for token in required_layout_css if token not in layout_css],
        "design_system_css": [token for token in required_design_css if token not in design_css],
        "js": [token for token in required_js if token not in js],
    }
    missing = {key: value for key, value in missing.items() if value}
    ok = not missing
    results = [Result(
        "manual_drive.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "manual drive page contains camera preview, compact status, current intent/output signals, smaller drag knob, locked drag pad, STOP, capture/recording indicators, persistence, API calls, and the recovered semantic layout" if ok else "manual drive source contract failed",
        {"missing": missing},
    )]
    status_index = template.find("manualDriveStatusPanel")
    preview_index = template.find("manualDriveCameraPanel")
    order_ok = status_index >= 0 and preview_index >= 0 and status_index < preview_index
    results.append(Result(
        "manual_drive.status_above_preview",
        order_ok,
        PiSDErrorCodes.OK if order_ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "status panel is before the preview panel for PC/iPad layouts" if order_ok else "status panel did not appear before preview panel",
        {"status_index": status_index, "preview_index": preview_index},
    ))

    snapshot_removed_ok = "mdrvSnapshot" not in template
    results.append(Result(
        "manual_drive.snapshot_button_removed",
        snapshot_removed_ok,
        PiSDErrorCodes.OK if snapshot_removed_ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "snapshot view button was removed from the preview panel" if snapshot_removed_ok else "snapshot view button is still present",
        {},
    ))

    signals_ok = all(token in template for token in ("mdrvIntentOut", "mdrvMotorOut")) and "renderMotorSignalsFromApiResponse" in js
    results.append(Result(
        "manual_drive.status_motor_signals",
        signals_ok,
        PiSDErrorCodes.OK if signals_ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "status strip shows intended steering/throttle and actual left/right motor output" if signals_ok else "manual drive motor signal readouts are missing",
        {},
    ))

    css_ok = (
        '"status status"' in layout_css
        and '"preview drive"' in layout_css
        and '"preview files"' in layout_css
        and '#manualDriveCameraPanel' in layout_css
        and '#manualDrivePadPanel' in layout_css
        and '#manualDriveFilesPanel' in layout_css
        and 'grid-area: preview' in layout_css
        and 'grid-area: drive' in layout_css
    )
    results.append(Result(
        "manual_drive.semantic_grid_layout",
        css_ok,
        PiSDErrorCodes.OK if css_ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "camera preview is locked under status in the main column and manual controls are locked to the right control column" if css_ok else "manual drive semantic grid CSS is missing or weak",
        {},
    ))
    return results


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("manual_drive.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]
    client = app.test_client()
    results: list[Result] = []
    for path, label, marker in (
        ("/manual-drive", "manual_drive.route.page", b"PiSD Manual Drive"),
        ("/testing/static/css/manual_drive.css", "manual_drive.static.css", b".mdrv-shell"),
        ("/testing/static/js/manual_drive.js", "manual_drive.static.js", b"manualDriveInitialStatus"),
        ("/testing/static/css/pisd_design_system.css", "manual_drive.static.design_system", b"PiSD Design System"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(Result(
            label,
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
            f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
            {"http_status": response.status_code, "bytes": len(response.data)},
        ))
    api_checks = [
        ("GET", "/api/status", None, "manual_drive.api.status", 200),
        ("POST", "/api/camera/start", {}, "manual_drive.api.camera_start", 200),
        ("GET", "/api/camera/frame.jpg", None, "manual_drive.api.camera_frame", 200),
        ("POST", "/api/control/manual", {"steering": 1.0, "throttle": 0.18, "steer_mix": 1.0}, "manual_drive.api.manual_command", 200),
        ("POST", "/api/control/stop", {}, "manual_drive.api.stop", 200),
        ("GET", "/api/recording/status", None, "manual_drive.api.recording_status", 200),
        ("GET", "/api/recording/items", None, "manual_drive.api.recording_items", 200),
        ("POST", "/api/camera/stop", {}, "manual_drive.api.camera_stop", 200),
    ]
    for method, path, body, label, expected_status in api_checks:
        response = client.get(path) if method == "GET" else client.post(path, json=body)
        payload = response.get_json(silent=True) or {}
        if path.endswith("frame.jpg"):
            ok = response.status_code == expected_status and response.mimetype == "image/jpeg" and len(response.data) > 0
            code = PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED
            message = "camera frame endpoint returned JPEG" if ok else f"camera frame returned HTTP {response.status_code} {response.mimetype}"
        else:
            ok = response.status_code == expected_status and payload.get("code") == PiSDErrorCodes.OK
            code = payload.get("code", PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED)
            message = f"{method} {path} returned OK" if ok else f"{method} {path} returned HTTP {response.status_code} code={code}"
        results.append(Result(label, ok, code, message, {"method": method, "path": path, "http_status": response.status_code}))
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.extend(check_source_contract())
    if not args.static_only:
        results.extend(check_routes(args.hardware))
    for result in results:
        emit(result)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
