#!/usr/bin/env python3
"""Run the standard PiSD validation checklist.

The output is intentionally simple for field testing. Each tested function prints
one line with OK/FAIL, a PiSD error code, and a short label. A machine-readable
summary is also written under test_outputs/standard_validation/summary.json.

Default mode is safe simulation. Real camera/GPIO adapters are requested only
with --hardware. Real motor movement requires BOTH --hardware and
--enable-motor-output.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app, load_defaults  # noqa: E402
from pisd.core.errors import PiSDErrorCodes, ok_payload, report_payload, ErrorReporter  # noqa: E402
from pisd.core.panel_contracts import get_panel_contracts  # noqa: E402
from pisd.services.camera_service import CameraService  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "standard_validation"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"
WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
WEB_TEMPLATE = WEB_ROOT / "templates" / "testing_server.html"
WEB_CSS = WEB_ROOT / "static" / "css" / "testing_server.css"
WEB_JS = WEB_ROOT / "static" / "js" / "testing_server.js"
PANEL_TEMPLATE = WEB_ROOT / "templates" / "panel_testing.html"
PANEL_CSS = WEB_ROOT / "static" / "css" / "panel_testing.css"
PANEL_JS = WEB_ROOT / "static" / "js" / "panel_testing.js"
MAIN_TEMPLATE = WEB_ROOT / "templates" / "main_dashboard.html"
MAIN_CSS = WEB_ROOT / "static" / "css" / "main_dashboard.css"
MAIN_JS = WEB_ROOT / "static" / "js" / "main_dashboard.js"
FRONT_TEMPLATE = WEB_ROOT / "templates" / "front_page.html"
FRONT_CSS = WEB_ROOT / "static" / "css" / "front_page.css"
FRONT_JS = WEB_ROOT / "static" / "js" / "front_page.js"
SETTINGS_TEMPLATE = WEB_ROOT / "templates" / "settings_tab.html"
SETTINGS_CSS = WEB_ROOT / "static" / "css" / "settings_tab.css"
SETTINGS_JS = WEB_ROOT / "static" / "js" / "settings_tab.js"
MANUAL_TEMPLATE = WEB_ROOT / "templates" / "manual_drive.html"
MANUAL_CSS = WEB_ROOT / "static" / "css" / "manual_drive.css"
MANUAL_JS = WEB_ROOT / "static" / "js" / "manual_drive.js"
PRESENTATION_TEMPLATE = WEB_ROOT / "templates" / "panel_presentation.html"
PRESENTATION_CSS = WEB_ROOT / "static" / "css" / "panel_presentation.css"
PRESENTATION_JS = WEB_ROOT / "static" / "js" / "panel_presentation.js"
PRESENTATION_GLOBAL_CSS = WEB_ROOT / "static" / "css" / "panel_presentation_global.css"
PRESENTATION_GLOBAL_JS = WEB_ROOT / "static" / "js" / "panel_presentation_global.js"
UNIFIED_CSS = WEB_ROOT / "static" / "css" / "unified_layout.css"
LAYOUT_CSS = WEB_ROOT / "static" / "css" / "pisd_layout_system.css"


@dataclass
class CheckResult:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "ok": bool(self.ok),
            "code": str(self.code),
            "message": str(self.message),
            "details": dict(self.details),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standard PiSD OK/FAIL validation checklist.")
    parser.add_argument("--hardware", action="store_true", help="Request real camera/GPIO adapters.")
    parser.add_argument(
        "--enable-motor-output",
        action="store_true",
        help="Actually move motors during channel tests. Requires --hardware. Keep wheels lifted.",
    )
    parser.add_argument("--skip-gui", action="store_true", help="Skip static/browser testing GUI validation checks.")
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip local Flask test-client API checks. Useful on systems without Flask installed.",
    )
    parser.add_argument(
        "--skip-camera",
        action="store_true",
        help="Skip direct camera service and API frame checks.",
    )
    parser.add_argument(
        "--skip-motor",
        action="store_true",
        help="Skip motor service/API checks.",
    )
    parser.add_argument("--motor-speed", type=float, default=0.12, help="Speed used for one-by-one motor channel tests.")
    parser.add_argument("--motor-duration", type=float, default=0.25, help="Seconds for each motor channel test.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def _print_result(result: CheckResult) -> None:
    state = "OK" if result.ok else "FAIL"
    print(f"{state:<4} {result.code:<13} {result.label} - {result.message}")


def _safe_check(label: str, func: Callable[[], CheckResult]) -> CheckResult:
    try:
        result = func()
        _print_result(result)
        return result
    except Exception as exc:
        result = CheckResult(
            label=label,
            ok=False,
            code=PiSDErrorCodes.TEST_STANDARD_VALIDATION_FAILED,
            message=f"Unhandled test exception: {exc}",
            details={"exception_type": type(exc).__name__},
        )
        _print_result(result)
        return result


def _json_code(payload: dict[str, Any] | None, fallback: str) -> str:
    if isinstance(payload, dict) and payload.get("code"):
        return str(payload["code"])
    return fallback


def _check_config_load() -> CheckResult:
    defaults = load_defaults()
    ok = isinstance(defaults, dict) and bool(defaults)
    return CheckResult(
        "config.load_defaults",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.APP_CONFIG_LOAD_FAILED,
        "defaults loaded" if ok else "defaults missing or invalid",
        {"sections": sorted(defaults.keys()) if isinstance(defaults, dict) else []},
    )


def _check_error_schema() -> CheckResult:
    reporter = ErrorReporter("standard-test")
    synthetic = reporter.report("PISD-TEST-000", "Synthetic validation report.")
    ok_data = ok_payload("schema ok")
    err_data = report_payload(False, synthetic)
    ok = ok_data.get("code") == PiSDErrorCodes.OK and err_data.get("code") == "PISD-TEST-000"
    return CheckResult(
        "core.error_reporting_schema",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_API_SCHEMA_FAILED,
        "error payloads include PiSD codes" if ok else "error payload schema failed",
    )


def _check_imports() -> CheckResult:
    # Imports are already executed at module import time; instantiate services to verify wiring.
    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=False)
    motor = MotorService(defaults.get("motor"), hardware_enabled=False)
    try:
        camera_status = camera.status()
        motor_status = motor.status()
        ok = camera_status.get("last_error_code") == PiSDErrorCodes.OK and motor_status.get("last_error_code") == PiSDErrorCodes.OK
        return CheckResult(
            "services.import_and_status",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_IMPORT_FAILED,
            "camera and motor services imported" if ok else "service import/status reported an error",
            {"camera_code": camera_status.get("last_error_code"), "motor_code": motor_status.get("last_error_code")},
        )
    finally:
        motor.close()
        camera.stop()


def _check_camera_service(hardware: bool) -> CheckResult:
    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=hardware)
    try:
        ok, message = camera.start()
        time.sleep(0.25)
        frame = camera.get_jpeg_frame()
        status = camera.status()
        frame_ok = bool(frame and frame.startswith(b"\xff\xd8"))
        success = bool(ok and frame_ok)
        code = PiSDErrorCodes.OK if success else status.get("last_error_code") or PiSDErrorCodes.TEST_CAMERA_FRAME_MISSING
        if ok and not frame_ok:
            code = PiSDErrorCodes.TEST_CAMERA_FRAME_MISSING
        return CheckResult(
            "camera.service_frame",
            success,
            str(code),
            f"frame captured ({len(frame or b'')} bytes)" if success else f"camera frame failed: {message}",
            {
                "hardware_requested": hardware,
                "backend": status.get("backend"),
                "capture_source": status.get("capture_source"),
                "array_color_order": status.get("array_color_order"),
                "frame_seq": status.get("frame_seq"),
            },
        )
    finally:
        camera.stop()


def _check_camera_settings(hardware: bool) -> CheckResult:
    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=hardware)
    try:
        settings = {
            "width": 320,
            "height": 240,
            "fps": 12,
            "preview_quality": 60,
            "capture_source": "request",
            "array_color_order": "rgb",
            "buffer_count": 2,
            "queue": False,
        }
        ok, message, config = camera.apply_settings(settings, restart=True)
        if ok:
            start_ok, start_message = camera.start()
            ok = bool(start_ok)
            message = f"{message} {start_message}"
        time.sleep(0.25)
        frame = camera.get_jpeg_frame()
        status = camera.status()
        frame_ok = bool(frame and frame.startswith(b"\xff\xd8"))
        config_ok = config.get("width") == 320 and config.get("height") == 240 and config.get("array_color_order") == "rgb"
        success = bool(ok and frame_ok and config_ok)
        code = PiSDErrorCodes.OK if success else status.get("last_error_code") or PiSDErrorCodes.TEST_CAMERA_SETTINGS_MATRIX_FAILED
        if ok and not frame_ok:
            code = PiSDErrorCodes.TEST_CAMERA_FRAME_MISSING
        return CheckResult(
            "camera.apply_settings",
            success,
            str(code),
            "camera settings applied and frame captured" if success else f"camera settings check failed: {message}",
            {"applied": settings, "backend": status.get("backend"), "frame_bytes": len(frame or b"")},
        )
    finally:
        camera.stop()


def _check_motor_service(real_output: bool, speed: float, duration: float) -> CheckResult:
    defaults = load_defaults()
    motor = MotorService(defaults.get("motor"), hardware_enabled=real_output)
    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    try:
        for side in ("left", "right"):
            for direction in (1, -1):
                result = motor.test_motor_channel(side, direction=direction, speed=speed, duration=duration)
                results.append({
                    "side": side,
                    "direction": direction,
                    "code": result.get("code"),
                    "ok": result.get("ok"),
                    "hardware_output_enabled": result.get("hardware_output_enabled"),
                })
                if not result.get("ok"):
                    failures.append(result)
        motor.stop()
        status = motor.status()
        stopped = abs(float(status.get("last_left", 0.0))) < 1e-6 and abs(float(status.get("last_right", 0.0))) < 1e-6
        ok = not failures and stopped
        code = PiSDErrorCodes.OK if ok else (PiSDErrorCodes.TEST_MOTOR_STOP_FAILED if not stopped else PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED)
        return CheckResult(
            "motor.service_channels",
            ok,
            code,
            "left/right direction tests completed and stopped" if ok else "one or more motor channel checks failed",
            {"hardware_output_enabled": real_output, "results": results, "final_adapter": status.get("adapter")},
        )
    finally:
        motor.close()



def _check_front_page_static_files() -> CheckResult:
    files = {
        "front_template": FRONT_TEMPLATE,
        "front_css": FRONT_CSS,
        "front_js": FRONT_JS,
        "settings_template": SETTINGS_TEMPLATE,
        "settings_css": SETTINGS_CSS,
        "settings_js": SETTINGS_JS,
        "manual_template": MANUAL_TEMPLATE,
        "manual_css": MANUAL_CSS,
        "manual_js": MANUAL_JS,
        "presentation_template": PRESENTATION_TEMPLATE,
        "presentation_css": PRESENTATION_CSS,
        "presentation_js": PRESENTATION_JS,
        "presentation_global_css": PRESENTATION_GLOBAL_CSS,
        "presentation_global_js": PRESENTATION_GLOBAL_JS,
        "unified_css": UNIFIED_CSS,
        "layout_css": LAYOUT_CSS,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size <= 0]
    ok = not missing
    return CheckResult(
        "front_page.static_files",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
        "front page/settings tab template/CSS/JS files exist" if ok else f"missing or empty files: {', '.join(missing)}",
        {name: str(path.relative_to(PROJECT_ROOT)) for name, path in files.items()},
    )


def _check_front_page_source_contract() -> CheckResult:
    try:
        front = FRONT_TEMPLATE.read_text(encoding="utf-8")
        front_css = FRONT_CSS.read_text(encoding="utf-8")
        front_js = FRONT_JS.read_text(encoding="utf-8")
        settings = SETTINGS_TEMPLATE.read_text(encoding="utf-8")
        settings_js = SETTINGS_JS.read_text(encoding="utf-8")
        unified_css = UNIFIED_CSS.read_text(encoding="utf-8")
        layout_css = LAYOUT_CSS.read_text(encoding="utf-8")
    except Exception as exc:
        return CheckResult(
            "front_page.source_contract",
            False,
            PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
            f"failed to read front page/settings files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required = {
        "front": ["PiSD Front Page", "frontModeSettings", "frontModeTesting", "href=\"/settings\"", "href=\"/testing\"", "frontPageInitialStatus"],
        "front_css": [".fp-mode-grid", ".fp-mode-card"],
        "front_js": ["frontApi", "/api/status", "/api/control/stop"],
        "settings": ["PiSD Settings", "Back to Front Page", "settingsMainPanel", "stCameraForm", "stMotorForm", "settingsInitialStatus"],
        "settings_js": ["settingsApi", "/api/settings/apply", "/api/settings", "/api/control/stop", "pisd.runtimeSettings.v2"],
        "unified_css": ["PiSD 0.3.2 unified visual recovery layer", ".mdrv-shell", "#settingsPanelPresentationPanel"],
        "layout_css": ["PiSD Responsive Layout System 0.3.7", "body.manual-drive-page .mdrv-shell", "status status", "preview drive", "body.settings-page .st-grid"],
    }
    sources = {"front": front, "front_css": front_css, "front_js": front_js, "settings": settings, "settings_js": settings_js, "unified_css": unified_css, "layout_css": layout_css}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    ok = not missing
    return CheckResult(
        "front_page.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
        "front page and settings tab source contract passed" if ok else "front page/settings source contract missing tokens",
        {"missing": missing},
    )


def _check_main_dashboard_static_files() -> CheckResult:
    files = {
        "template": MAIN_TEMPLATE,
        "css": MAIN_CSS,
        "js": MAIN_JS,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size <= 0]
    ok = not missing
    return CheckResult(
        "main_dashboard.static_files",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
        "main dashboard template/CSS/JS files exist" if ok else f"missing or empty files: {', '.join(missing)}",
        {name: str(path.relative_to(PROJECT_ROOT)) for name, path in files.items()},
    )


def _check_main_dashboard_source_contract() -> CheckResult:
    try:
        template = MAIN_TEMPLATE.read_text(encoding="utf-8")
        css = MAIN_CSS.read_text(encoding="utf-8")
        js = MAIN_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return CheckResult(
            "main_dashboard.source_contract",
            False,
            PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
            f"failed to read main dashboard files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required_template_tokens = [
        "PiSD Main Dashboard",
        "Back to Front Page",
        'href="/"',
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
    ]
    required_js_tokens = [
        "apiCall",
        "refreshStatus",
        "stopAll",
        "updateMotorLock",
        "sendManual",
        "sendChannelTest",
        "/api/status",
        "/api/camera/start",
        "/api/camera/frame.jpg",
        "/video_feed",
        "/api/control/manual",
        "/api/motor/test-channel",
        "/api/control/stop",
        "PISD-MOT-008",
    ]
    required_css_tokens = [".md-shell", ".md-panel", ".md-big-stop", "container-type: inline-size", "@media (max-width: 1100px)"]
    missing = {
        "template": [token for token in required_template_tokens if token not in template],
        "js": [token for token in required_js_tokens if token not in js],
        "css": [token for token in required_css_tokens if token not in css],
    }
    ok = not any(missing.values())
    return CheckResult(
        "main_dashboard.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
        "main dashboard source contains required panels, safety lock, STOP actions, and API calls" if ok else "main dashboard source contract is missing required tokens",
        {key: value for key, value in missing.items() if value},
    )


def _check_manual_drive_static_files() -> CheckResult:
    files = {
        "template": MANUAL_TEMPLATE,
        "css": MANUAL_CSS,
        "js": MANUAL_JS,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size <= 0]
    ok = not missing
    return CheckResult(
        "manual_drive.static_files",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "manual drive template/CSS/JS files exist" if ok else f"missing or empty files: {', '.join(missing)}",
        {name: str(path.relative_to(PROJECT_ROOT)) for name, path in files.items()},
    )


def _check_manual_drive_source_contract() -> CheckResult:
    try:
        template = MANUAL_TEMPLATE.read_text(encoding="utf-8")
        css = MANUAL_CSS.read_text(encoding="utf-8")
        js = MANUAL_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return CheckResult(
            "manual_drive.source_contract",
            False,
            PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
            f"failed to read manual drive files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required = {
        "template": ["PiSD Manual Drive", "Back to Front Page", "manualDriveCameraPanel", "manualDriveStatusPanel", "manualDrivePadPanel", "manualDriveStopPanel", "manualDriveInitialStatus"],
        "css": [".mdrv-shell", ".mdrv-panel", ".mdrv-pad", ".mdrv-big-stop"],
        "js": ["manualDriveInitialStatus", "pisd.manualDrive.v1", "/api/camera/start", "/video_feed", "/api/control/manual", "/api/control/stop", "PISD-MOT-008"],
    }
    sources = {"template": template, "css": css, "js": js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    ok = not missing
    return CheckResult(
        "manual_drive.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
        "manual drive page source contract passed" if ok else "manual drive page source contract missing tokens",
        {"missing": missing},
    )


def _check_testing_gui_static_files() -> CheckResult:
    files = {
        "template": WEB_TEMPLATE,
        "css": WEB_CSS,
        "js": WEB_JS,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size <= 0]
    ok = not missing
    return CheckResult(
        "gui.static_files",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "testing GUI template/CSS/JS files exist" if ok else f"missing or empty files: {', '.join(missing)}",
        {name: str(path.relative_to(PROJECT_ROOT)) for name, path in files.items()},
    )


def _check_testing_gui_source_contract() -> CheckResult:
    try:
        template = WEB_TEMPLATE.read_text(encoding="utf-8")
        css = WEB_CSS.read_text(encoding="utf-8")
        js = WEB_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return CheckResult(
            "gui.source_contract",
            False,
            PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
            f"failed to read testing GUI files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required_template_tokens = [
        "PiSD Testing Server GUI",
        "initialStatusJson",
        "manifestJson",
        "globalCode",
        "cameraPreview",
        "startLivePreviewBtn",
        "fpsTestPanel",
        "runMaxFpsBtn",
        "cameraSettingsForm",
        "motorSettingsForm",
        "motorChannelForm",
        "smokeTestPanel",
        "runSmokeTestBtn",
        "runSmokeTestBtn2",
    ]
    required_js_tokens = [
        "runSafeSmokeTest",
        "/api/status",
        "/api/test-gui/manifest",
        "/api/camera/start",
        "/api/camera/frame.jpg",
        "/video_feed",
        "/api/camera/fps-stats",
        "/api/camera/apply",
        "/api/motor/apply",
        "/api/motor/test-channel",
        "/api/control/stop",
        "enable_motor_output: false",
        "PISD-MOT-008",
        "PISD-TEST-011",
        "PISD-TEST-017",
    ]
    required_css_tokens = [".code-pill", ".console", ".console.compact"]
    missing = {
        "template": [token for token in required_template_tokens if token not in template],
        "js": [token for token in required_js_tokens if token not in js],
        "css": [token for token in required_css_tokens if token not in css],
    }
    ok = not any(missing.values())
    return CheckResult(
        "gui.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "testing GUI source contains required IDs, API calls, safety checks, and code display" if ok else "testing GUI source contract is missing required tokens",
        {key: value for key, value in missing.items() if value},
    )



def _check_panel_testing_static_files() -> CheckResult:
    files = {
        "template": PANEL_TEMPLATE,
        "css": PANEL_CSS,
        "js": PANEL_JS,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size <= 0]
    ok = not missing
    return CheckResult(
        "panel_gui.static_files",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
        "panel testing GUI template/CSS/JS files exist" if ok else f"missing or empty files: {', '.join(missing)}",
        {name: str(path.relative_to(PROJECT_ROOT)) for name, path in files.items()},
    )


def _check_panel_testing_source_contract() -> CheckResult:
    try:
        template = PANEL_TEMPLATE.read_text(encoding="utf-8")
        css = PANEL_CSS.read_text(encoding="utf-8")
        js = PANEL_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return CheckResult(
            "panel_gui.source_contract",
            False,
            PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
            f"failed to read panel GUI files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required_template_tokens = [
        "PiSD Panel Testing Lab",
        "ptPanelGrid",
        "ptPanelReport",
        "ptTheme",
        "ptLayoutMode",
        "ptViewportPreset",
        "ptPanelSizePreset",
        "ptFontScale",
        "ptMinPanelWidth",
        "ptPreviewAspect",
        "ptRunPanelApiChecks",
        "ptSavePreset",
        "ptLoadPreset",
        "ptExportPreset",
        "ptImportPreset",
    ]
    required_js_tokens = [
        "PANEL_BLUEPRINTS",
        "system-status-panel",
        "camera-preview-panel",
        "camera-settings-panel",
        "motor-settings-panel",
        "motor-channel-panel",
        "manual-drive-panel",
        "safety-stop-panel",
        "error-monitor-panel",
        "api-inspector-panel",
        "validation-panel",
        "recording-panel",
        "model-runtime-panel",
        "applyPanelSizePreset",
        "runAllPanelChecks",
        "runAllPanelApiChecks",
        "runPanelApiTest",
        "showContract",
        "showLastResponse",
        "showExpected",
        "savePreset",
        "loadPreset",
        "exportPreset",
        "importPresetFile",
        "PISD-TEST-012",
        "PISD-TEST-013",
        "PISD-TEST-014",
    ]
    required_css_tokens = ["--pt-min-panel-width", "--pt-preview-aspect", ".pt-panel-grid", ".pt-contract-strip", ".pt-code-inline", "container-type: inline-size", "@media (max-width: 850px)"]
    missing = {
        "template": [token for token in required_template_tokens if token not in template],
        "js": [token for token in required_js_tokens if token not in js],
        "css": [token for token in required_css_tokens if token not in css],
    }
    ok = not any(missing.values())
    return CheckResult(
        "panel_gui.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
        "panel testing GUI source contains registry loading, style controls, presets, API contract actions, and responsive rules" if ok else "panel testing GUI source contract is missing required tokens",
        {key: value for key, value in missing.items() if value},
    )


def _check_panel_presentation_static_files() -> CheckResult:
    files = {
        "template": PRESENTATION_TEMPLATE,
        "css": PRESENTATION_CSS,
        "js": PRESENTATION_JS,
        "global_css": PRESENTATION_GLOBAL_CSS,
        "global_js": PRESENTATION_GLOBAL_JS,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size <= 0]
    ok = not missing
    return CheckResult(
        "panel_presentation.static_files",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
        "panel presentation template/CSS/JS files exist" if ok else f"missing or empty files: {', '.join(missing)}",
        {name: str(path.relative_to(PROJECT_ROOT)) for name, path in files.items()},
    )


def _check_panel_presentation_source_contract() -> CheckResult:
    try:
        template = PRESENTATION_TEMPLATE.read_text(encoding="utf-8")
        css = PRESENTATION_CSS.read_text(encoding="utf-8")
        js = PRESENTATION_JS.read_text(encoding="utf-8")
        global_css = PRESENTATION_GLOBAL_CSS.read_text(encoding="utf-8")
        global_js = PRESENTATION_GLOBAL_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return CheckResult(
            "panel_presentation.source_contract",
            False,
            PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
            f"failed to read panel presentation files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required = {
        "template": ["PiSD Panel Presentation Settings", "ppTheme", "ppLayoutMode", "ppDensity", "ppPreviewFit", "ppPanelPadding", "ppPanelHeaderMode", "ppButtonScale", "ppConsoleHeight", "ppCardAccent", "ppAutoSave", "ppSave", "ppExport", "Back to Front Page"],
        "css": [".pp-shell", ".pp-control-grid", ".pp-panel-grid"],
        "js": ["PiSDPanelPresentation", "ppSave", "ppReset", "autoSaveEnabled", "PISD-TEST-018"],
        "global_css": ["--pisd-ui-gap", "--pisd-ui-radius", "--pisd-ui-button-scale", "--pisd-ui-console-height", ".fp-mode-grid", ".md-shell", ".mdrv-shell"],
        "global_js": ["pisd.panelPresentation.v1", "PiSDPanelPresentation", "localStorage"],
    }
    sources = {"template": template, "css": css, "js": js, "global_css": global_css, "global_js": global_js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    ok = not missing
    return CheckResult(
        "panel_presentation.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
        "panel presentation source contract passed" if ok else "panel presentation source contract missing tokens",
        {"missing": missing},
    )


def _check_responsive_layout_source_contract() -> CheckResult:
    try:
        layout_css = LAYOUT_CSS.read_text(encoding="utf-8")
        manual = MANUAL_TEMPLATE.read_text(encoding="utf-8")
        templates = [FRONT_TEMPLATE, MANUAL_TEMPLATE, SETTINGS_TEMPLATE, WEB_TEMPLATE, MAIN_TEMPLATE, PRESENTATION_TEMPLATE, PANEL_TEMPLATE]
    except Exception as exc:
        return CheckResult(
            "responsive_layout.source_contract",
            False,
            PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED,
            f"failed to read responsive layout files: {exc}",
            {"exception_type": type(exc).__name__},
        )
    required_css = ["PiSD Responsive Layout System 0.3.7", "status status", "preview drive", "body.manual-drive-page .mdrv-shell", "body.settings-page .st-grid", "@media (max-width: 759px)"]
    missing_css = [token for token in required_css if token not in layout_css]
    order_positions = [manual.find(token) for token in ("manualDriveStatusPanel", "manualDriveCameraPanel", "manualDrivePadPanel", "manualDriveStopPanel")]
    manual_order_ok = all(pos >= 0 for pos in order_positions) and order_positions == sorted(order_positions)
    bad_templates = []
    for template in templates:
        source = template.read_text(encoding="utf-8")
        order = [source.find("css/unified_layout.css"), source.find("css/pisd_design_system.css"), source.find("css/pisd_layout_system.css")]
        if any(pos < 0 for pos in order) or not (order[0] < order[1] < order[2]):
            bad_templates.append(str(template.relative_to(PROJECT_ROOT)))
    ok = not missing_css and manual_order_ok and not bad_templates
    return CheckResult(
        "responsive_layout.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED,
        "responsive layout system loaded last and Manual Drive semantic order is fixed" if ok else "responsive layout source contract failed",
        {"missing_css": missing_css, "manual_order_ok": manual_order_ok, "bad_templates": bad_templates},
    )

def _check_api_status(client) -> CheckResult:
    response = client.get("/api/status")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
    return CheckResult(
        "api.status",
        ok,
        _json_code(payload, PiSDErrorCodes.API_SERVICE_EXCEPTION),
        "status endpoint returned OK" if ok else f"status endpoint returned HTTP {response.status_code}",
        {"http_status": response.status_code},
    )


def _check_api_camera(client) -> list[CheckResult]:
    results: list[CheckResult] = []
    response = client.post("/api/camera/start")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("ok") is True
    results.append(
        CheckResult(
            "api.camera.start",
            ok,
            _json_code(payload, PiSDErrorCodes.API_SERVICE_EXCEPTION),
            "camera start endpoint OK" if ok else f"camera start returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )
    time.sleep(0.25)
    response = client.get("/api/camera/frame.jpg")
    frame_ok = response.status_code == 200 and response.data.startswith(b"\xff\xd8")
    results.append(
        CheckResult(
            "api.camera.frame",
            frame_ok,
            PiSDErrorCodes.OK if frame_ok else PiSDErrorCodes.TEST_CAMERA_FRAME_MISSING,
            f"camera frame endpoint returned JPEG ({len(response.data)} bytes)" if frame_ok else f"camera frame returned HTTP {response.status_code}",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )
    response = client.post(
        "/api/camera/apply",
        json={"width": 320, "height": 240, "capture_source": "request", "array_color_order": "rgb", "preview_quality": 60},
    )
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("ok") is True and (payload.get("config") or {}).get("array_color_order") == "rgb"
    results.append(
        CheckResult(
            "api.camera.apply_settings",
            ok,
            _json_code(payload, PiSDErrorCodes.API_SERVICE_EXCEPTION),
            "camera settings endpoint OK" if ok else f"camera apply returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )
    return results


def _check_api_motor(client, hardware: bool, enable_motor_output: bool, speed: float, duration: float) -> list[CheckResult]:
    results: list[CheckResult] = []
    response = client.get("/api/motor/config")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
    results.append(
        CheckResult(
            "api.motor.config",
            ok,
            _json_code(payload, PiSDErrorCodes.API_SERVICE_EXCEPTION),
            "motor config endpoint OK" if ok else f"motor config returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )

    if hardware and not enable_motor_output:
        response = client.post(
            "/api/motor/test-channel",
            json={"side": "left", "direction": 1, "speed": speed, "duration": duration},
        )
        payload = response.get_json(silent=True) or {}
        ok = response.status_code == 403 and payload.get("code") == PiSDErrorCodes.MOTOR_TEST_UNARMED
        results.append(
            CheckResult(
                "api.motor.test_channel_safety_refusal",
                ok,
                _json_code(payload, PiSDErrorCodes.MOTOR_TEST_UNARMED),
                "unarmed real motor test refused safely" if ok else f"expected safety refusal, got HTTP {response.status_code}",
                {"http_status": response.status_code},
            )
        )
        return results

    failures = 0
    channel_details: list[dict[str, Any]] = []
    for side in ("left", "right"):
        for direction in (1, -1):
            response = client.post(
                "/api/motor/test-channel",
                json={
                    "side": side,
                    "direction": direction,
                    "speed": speed,
                    "duration": duration,
                    "enable_motor_output": bool(enable_motor_output),
                },
            )
            payload = response.get_json(silent=True) or {}
            item_ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
            channel_details.append({
                "side": side,
                "direction": direction,
                "http_status": response.status_code,
                "code": payload.get("code"),
                "ok": item_ok,
            })
            if not item_ok:
                failures += 1
    ok = failures == 0
    results.append(
        CheckResult(
            "api.motor.test_channel",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED,
            "motor channel API tests completed" if ok else f"{failures} motor channel API checks failed",
            {"hardware_output_enabled": bool(enable_motor_output), "channels": channel_details},
        )
    )
    return results


def _check_api_stop_and_errors(client) -> list[CheckResult]:
    results: list[CheckResult] = []
    response = client.post("/api/control/stop")
    payload = response.get_json(silent=True) or {}
    motor_status = payload.get("motor") or {}
    stopped = abs(float(motor_status.get("last_left", 0.0))) < 1e-6 and abs(float(motor_status.get("last_right", 0.0))) < 1e-6
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and stopped
    results.append(
        CheckResult(
            "api.control.stop",
            ok,
            _json_code(payload, PiSDErrorCodes.TEST_MOTOR_STOP_FAILED),
            "stop endpoint reset outputs" if ok else f"stop endpoint failed or outputs not zero, HTTP {response.status_code}",
            {"http_status": response.status_code, "last_left": motor_status.get("last_left"), "last_right": motor_status.get("last_right")},
        )
    )

    response = client.post("/api/motor/apply", data="not-json", content_type="application/json")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 400 and payload.get("code") == PiSDErrorCodes.API_INVALID_JSON
    results.append(
        CheckResult(
            "api.invalid_json_error_code",
            ok,
            _json_code(payload, PiSDErrorCodes.API_INVALID_JSON),
            "invalid JSON returned PISD-API-001" if ok else f"invalid JSON check failed, HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )
    return results




def _check_api_main_dashboard_gui(client) -> list[CheckResult]:
    results: list[CheckResult] = []
    response = client.get("/")
    front_ok = response.status_code == 200 and b"PiSD Front Page" in response.data and b"frontModeSettings" in response.data and b"frontModeTesting" in response.data and b"frontModeManualDrive" in response.data
    results.append(
        CheckResult(
            "api.front_page.root_page",
            front_ok,
            PiSDErrorCodes.OK if front_ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
            "/ front page loaded" if front_ok else f"/ returned HTTP {response.status_code} or missing front page content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/settings")
    settings_ok = response.status_code == 200 and b"PiSD Settings Tab" in response.data and b"Back to Front Page" in response.data
    results.append(
        CheckResult(
            "api.front_page.settings_tab",
            settings_ok,
            PiSDErrorCodes.OK if settings_ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
            "/settings tab loaded" if settings_ok else f"/settings returned HTTP {response.status_code} or missing content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/manual-drive")
    manual_ok = response.status_code == 200 and b"PiSD Manual Drive" in response.data and b"manualDrivePadPanel" in response.data and b"Back to Front Page" in response.data
    results.append(
        CheckResult(
            "api.manual_drive.page",
            manual_ok,
            PiSDErrorCodes.OK if manual_ok else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED,
            "/manual-drive page loaded" if manual_ok else f"/manual-drive returned HTTP {response.status_code} or missing expected content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/dashboard")
    page_ok = response.status_code == 200 and b"PiSD Main Dashboard" in response.data and b"panel-system-status" in response.data and b"Back to Front Page" in response.data
    results.append(
        CheckResult(
            "api.main_dashboard.dashboard_page",
            page_ok,
            PiSDErrorCodes.OK if page_ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
            "/dashboard main dashboard page loaded" if page_ok else f"/dashboard returned HTTP {response.status_code} or missing expected content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    response = client.get("/panel-presentation")
    presentation_ok = response.status_code == 200 and b"PiSD Panel Presentation Settings" in response.data and b"Back to Front Page" in response.data
    results.append(
        CheckResult(
            "api.panel_presentation.page",
            presentation_ok,
            PiSDErrorCodes.OK if presentation_ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
            "/panel-presentation loaded" if presentation_ok else f"/panel-presentation returned HTTP {response.status_code} or missing expected content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )
    for path, label, marker in (
        ("/testing/static/css/front_page.css", "api.front_page.static_css", b".fp-mode-grid"),
        ("/testing/static/js/front_page.js", "api.front_page.static_js", b"frontApi"),
        ("/testing/static/css/settings_tab.css", "api.settings_tab.static_css", b".st-grid"),
        ("/testing/static/js/settings_tab.js", "api.settings_tab.static_js", b"settingsApi"),
        ("/testing/static/css/manual_drive.css", "api.manual_drive.static_css", b".mdrv-shell"),
        ("/testing/static/js/manual_drive.js", "api.manual_drive.static_js", b"manualDriveInitialStatus"),
        ("/testing/static/css/main_dashboard.css", "api.main_dashboard.static_css", b".md-shell"),
        ("/testing/static/js/main_dashboard.js", "api.main_dashboard.static_js", b"updateMotorLock"),
        ("/testing/static/css/panel_presentation_global.css", "api.panel_presentation.global_css", b"--pisd-ui-gap"),
        ("/testing/static/js/panel_presentation_global.js", "api.panel_presentation.global_js", b"PiSDPanelPresentation"),
        ("/testing/static/css/unified_layout.css", "api.panel_presentation.unified_css", b"PiSD 0.3.2 unified visual recovery layer"),
        ("/testing/static/css/pisd_layout_system.css", "api.panel_presentation.layout_css", b"PiSD Responsive Layout System 0.3.7"),
        ("/testing/static/css/panel_presentation.css", "api.panel_presentation.static_css", b".pp-shell"),
        ("/testing/static/js/panel_presentation.js", "api.panel_presentation.static_js", b"ppSave"),
    ):
        response = client.get(path)
        asset_ok = response.status_code == 200 and marker in response.data
        results.append(
            CheckResult(
                label,
                asset_ok,
                PiSDErrorCodes.OK if asset_ok else PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED,
                f"{path} asset loaded" if asset_ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )
    response = client.post("/api/control/stop", json={})
    payload = response.get_json(silent=True) or {}
    stop_ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK
    results.append(
        CheckResult(
            "api.main_dashboard.stop_safe",
            stop_ok,
            _json_code(payload, PiSDErrorCodes.TEST_MAIN_DASHBOARD_CONTRACT_FAILED),
            "dashboard STOP API call returned OK" if stop_ok else f"dashboard STOP API returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )
    return results


def _check_api_testing_gui(client) -> list[CheckResult]:
    results: list[CheckResult] = []

    response = client.get("/testing")
    page_ok = response.status_code == 200 and b"PiSD Testing Server GUI" in response.data and b"Run safe smoke test" in response.data
    results.append(
        CheckResult(
            "api.testing_gui.page",
            page_ok,
            PiSDErrorCodes.OK if page_ok else PiSDErrorCodes.TEST_GUI_ROUTE_FAILED,
            "/testing GUI page loaded" if page_ok else f"/testing returned HTTP {response.status_code} or missing expected content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    static_checks = [
        ("/testing/static/css/testing_server.css", "api.testing_gui.static_css", b".code-pill"),
        ("/testing/static/js/testing_server.js", "api.testing_gui.static_js", b"runSafeSmokeTest"),
    ]
    for path, label, marker in static_checks:
        response = client.get(path)
        asset_ok = response.status_code == 200 and marker in response.data
        results.append(
            CheckResult(
                label,
                asset_ok,
                PiSDErrorCodes.OK if asset_ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
                f"{path} asset loaded" if asset_ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )

    response = client.get("/api/test-gui/manifest")
    payload = response.get_json(silent=True) or {}
    required_paths = {
        "/api/status",
        "/api/errors",
        "/api/camera/start",
        "/api/camera/stop",
        "/api/camera/config",
        "/api/camera/capabilities",
        "/api/camera/apply",
        "/api/camera/frame.jpg",
        "/video_feed",
        "/api/camera/fps-stats",
        "/api/motor/config",
        "/api/motor/apply",
        "/api/motor/test-channel",
        "/api/control/manual",
        "/api/control/stop",
    }
    manifest_paths = {str(item.get("path")) for item in payload.get("endpoints") or [] if isinstance(item, dict)}
    known_good = payload.get("known_good_camera") or {}
    manifest_ok = (
        response.status_code == 200
        and payload.get("code") == PiSDErrorCodes.OK
        and required_paths.issubset(manifest_paths)
        and known_good.get("capture_source") == "request"
        and known_good.get("array_color_order") == "rgb"
    )
    results.append(
        CheckResult(
            "api.testing_gui.manifest_contract",
            manifest_ok,
            _json_code(payload, PiSDErrorCodes.TEST_GUI_API_CONTRACT_FAILED),
            "testing GUI manifest includes required endpoints and known-good camera references" if manifest_ok else "testing GUI manifest contract failed",
            {"http_status": response.status_code, "missing_paths": sorted(required_paths - manifest_paths), "known_good_camera": known_good},
        )
    )

    response = client.post("/api/motor/test-channel", json={"side": "wrong", "direction": 1, "speed": 0.1, "duration": 0.05})
    payload = response.get_json(silent=True) or {}
    invalid_motor_ok = response.status_code == 400 and payload.get("code") == PiSDErrorCodes.MOTOR_TEST_INVALID
    results.append(
        CheckResult(
            "api.motor.test_channel_invalid_side",
            invalid_motor_ok,
            _json_code(payload, PiSDErrorCodes.MOTOR_TEST_INVALID),
            "invalid motor side returned PISD-MOT-007" if invalid_motor_ok else f"invalid motor side returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )

    response = client.get("/api/does-not-exist")
    payload = response.get_json(silent=True) or {}
    not_found_ok = response.status_code == 404 and payload.get("code") == PiSDErrorCodes.API_NOT_FOUND
    results.append(
        CheckResult(
            "api.not_found_error_code",
            not_found_ok,
            _json_code(payload, PiSDErrorCodes.API_NOT_FOUND),
            "unknown route returned PISD-API-003" if not_found_ok else f"unknown route returned HTTP {response.status_code}",
            {"http_status": response.status_code},
        )
    )
    return results



def _check_api_panel_testing_gui(client) -> list[CheckResult]:
    results: list[CheckResult] = []
    response = client.get("/panel-testing")
    page_ok = response.status_code == 200 and b"PiSD Panel Testing Lab" in response.data and b"ptPanelGrid" in response.data
    results.append(
        CheckResult(
            "api.panel_gui.page",
            page_ok,
            PiSDErrorCodes.OK if page_ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
            "/panel-testing page loaded" if page_ok else f"/panel-testing returned HTTP {response.status_code} or missing expected content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    for path, label, marker in (
        ("/testing/static/css/panel_testing.css", "api.panel_gui.static_css", b".pt-panel-grid"),
        ("/testing/static/js/panel_testing.js", "api.panel_gui.static_js", b"PANEL_BLUEPRINTS"),
    ):
        response = client.get(path)
        asset_ok = response.status_code == 200 and marker in response.data
        results.append(
            CheckResult(
                label,
                asset_ok,
                PiSDErrorCodes.OK if asset_ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
                f"{path} asset loaded" if asset_ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )

    response = client.get("/api/panel-testing/manifest")
    payload = response.get_json(silent=True) or {}
    panel_payload = payload.get("panels") or []
    panels = {str(item.get("id")) for item in panel_payload if isinstance(item, dict)}
    required_panels = {
        "system-status-panel",
        "camera-preview-panel",
        "camera-settings-panel",
        "motor-settings-panel",
        "motor-channel-panel",
        "manual-drive-panel",
        "safety-stop-panel",
        "error-monitor-panel",
        "api-inspector-panel",
        "validation-panel",
        "recording-panel",
        "model-runtime-panel",
    }
    style_controls = set(payload.get("style_controls") or [])
    required_controls = {"theme", "layout_mode", "viewport_preset", "panel_size_preset", "density", "font_scale", "panel_gap", "corner_radius", "minimum_panel_width", "preview_aspect"}
    contracts_ok = all(isinstance(item.get("safe_test"), dict) and isinstance(item.get("endpoints"), list) for item in panel_payload if isinstance(item, dict))
    manifest_ok = (
        response.status_code == 200
        and payload.get("code") == PiSDErrorCodes.OK
        and required_panels.issubset(panels)
        and required_controls.issubset(style_controls)
        and contracts_ok
    )
    results.append(
        CheckResult(
            "api.panel_gui.manifest_contract",
            manifest_ok,
            _json_code(payload, PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED),
            "panel testing manifest lists planned panels, style controls, and API contracts" if manifest_ok else "panel testing manifest contract failed",
            {"http_status": response.status_code, "missing_panels": sorted(required_panels - panels), "missing_controls": sorted(required_controls - style_controls), "contracts_ok": contracts_ok},
        )
    )

    response = client.get("/api/panel-testing/contracts")
    payload = response.get_json(silent=True) or {}
    contracts_route_ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and len(payload.get("panels") or []) >= len(required_panels)
    results.append(
        CheckResult(
            "api.panel_gui.contracts_route",
            contracts_route_ok,
            _json_code(payload, PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED),
            "panel testing contracts route loaded" if contracts_route_ok else f"panel contracts route returned HTTP {response.status_code}",
            {"http_status": response.status_code, "panel_count": len(payload.get("panels") or [])},
        )
    )
    return results



def _check_panel_api_contract_data() -> CheckResult:
    contracts = get_panel_contracts()
    required_panels = {
        "system-status-panel", "camera-preview-panel", "camera-settings-panel", "motor-settings-panel",
        "motor-channel-panel", "manual-drive-panel", "safety-stop-panel", "error-monitor-panel",
        "api-inspector-panel", "validation-panel", "recording-panel", "model-runtime-panel",
    }
    panel_ids = {str(item.get("id")) for item in contracts}
    incomplete = [
        item.get("id")
        for item in contracts
        if not item.get("id") or not item.get("title") or not isinstance(item.get("endpoints"), list) or not isinstance(item.get("safe_test"), dict)
    ]
    missing = sorted(required_panels - panel_ids)
    ok = not missing and not incomplete
    return CheckResult(
        "panel_api.contract_data",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
        "panel API contract data complete" if ok else "panel API contract data missing required entries",
        {"contract_count": len(contracts), "missing_panels": missing, "incomplete": incomplete},
    )

def _run_api_checks(args: argparse.Namespace) -> list[CheckResult]:
    try:
        app = create_app(hardware_enabled=bool(args.hardware))
    except RuntimeError as exc:
        return [
            CheckResult(
                "api.create_app",
                False,
                PiSDErrorCodes.APP_DEPENDENCY_MISSING,
                f"API app could not be created: {exc}",
            )
        ]

    client = app.test_client()
    results: list[CheckResult] = []
    if not args.skip_gui:
        results.extend(_check_api_main_dashboard_gui(client))
        results.extend(_check_api_testing_gui(client))
        results.extend(_check_api_panel_testing_gui(client))
    results.append(_check_api_status(client))
    if not args.skip_camera:
        results.extend(_check_api_camera(client))
    if not args.skip_motor:
        results.extend(_check_api_motor(client, bool(args.hardware), bool(args.enable_motor_output), args.motor_speed, args.motor_duration))
    results.extend(_check_api_stop_and_errors(client))
    # Stop camera after local API checks.
    client.post("/api/camera/stop")
    return results


def main() -> int:
    args = parse_args()
    if args.enable_motor_output and not args.hardware:
        print("FAIL PISD-TEST-008 --enable-motor-output requires --hardware", file=sys.stderr)
        return 2
    if args.enable_motor_output:
        print("SAFETY: real motor output is enabled. Keep wheels lifted and motor power reachable.")

    checks: list[CheckResult] = []
    checks.append(_safe_check("config.load_defaults", _check_config_load))
    checks.append(_safe_check("core.error_reporting_schema", _check_error_schema))
    checks.append(_safe_check("services.import_and_status", _check_imports))

    if not args.skip_gui:
        checks.append(_safe_check("front_page.static_files", _check_front_page_static_files))
        checks.append(_safe_check("front_page.source_contract", _check_front_page_source_contract))
        checks.append(_safe_check("main_dashboard.static_files", _check_main_dashboard_static_files))
        checks.append(_safe_check("main_dashboard.source_contract", _check_main_dashboard_source_contract))
        checks.append(_safe_check("manual_drive.static_files", _check_manual_drive_static_files))
        checks.append(_safe_check("manual_drive.source_contract", _check_manual_drive_source_contract))
        checks.append(_safe_check("gui.static_files", _check_testing_gui_static_files))
        checks.append(_safe_check("gui.source_contract", _check_testing_gui_source_contract))
        checks.append(_safe_check("panel_gui.static_files", _check_panel_testing_static_files))
        checks.append(_safe_check("panel_gui.source_contract", _check_panel_testing_source_contract))
        checks.append(_safe_check("panel_api.contract_data", _check_panel_api_contract_data))
        checks.append(_safe_check("panel_presentation.static_files", _check_panel_presentation_static_files))
        checks.append(_safe_check("panel_presentation.source_contract", _check_panel_presentation_source_contract))
        checks.append(_safe_check("responsive_layout.source_contract", _check_responsive_layout_source_contract))

    if not args.skip_camera:
        checks.append(_safe_check("camera.service_frame", lambda: _check_camera_service(bool(args.hardware))))
        checks.append(_safe_check("camera.apply_settings", lambda: _check_camera_settings(bool(args.hardware))))

    if not args.skip_motor:
        real_output = bool(args.hardware and args.enable_motor_output)
        checks.append(_safe_check("motor.service_channels", lambda: _check_motor_service(real_output, args.motor_speed, args.motor_duration)))

    if args.skip_api:
        skipped = CheckResult("api.local_test_client", True, PiSDErrorCodes.OK, "skipped by --skip-api", {"skipped": True})
        _print_result(skipped)
        checks.append(skipped)
    else:
        for result in _run_api_checks(args):
            _print_result(result)
            checks.append(result)

    passed = sum(1 for item in checks if item.ok)
    failed = [item for item in checks if not item.ok]
    summary_code = PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_STANDARD_VALIDATION_FAILED
    summary = {
        "ok": not failed,
        "code": summary_code,
        "hardware_requested": bool(args.hardware),
        "motor_output_enabled": bool(args.hardware and args.enable_motor_output),
        "passed": passed,
        "failed": len(failed),
        "results": [item.as_dict() for item in checks],
    }

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("-" * 72)
    final_state = "OK" if not failed else "FAIL"
    print(f"{final_state:<4} {summary_code:<13} summary - passed={passed} failed={len(failed)} output={output_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
