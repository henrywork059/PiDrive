#!/usr/bin/env python3
"""Validate the reset PiSD Motor Tuning page.

Patch 0.8.7 intentionally removes all rendered tuning panels so the page can be
rebuilt from a clean layout. Backend motor tuning APIs are still checked when the
optional Flask/runtime dependencies are available and --static-only is not used.
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

from pisd.core.errors import PiSDErrorCodes  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
TEMPLATE = WEB_ROOT / "templates" / "motor_tuning.html"
CSS = WEB_ROOT / "static" / "css" / "motor_tuning.css"
LAYOUT_CSS = WEB_ROOT / "static" / "css" / "pisd_layout_system.css"
JS = WEB_ROOT / "static" / "js" / "motor_tuning.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "motor_tuning_page"
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


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate PiSD Motor Tuning reset page.")
    parser.add_argument("--static-only", action="store_true", help="Skip Flask route and service checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": TEMPLATE, "css": CSS, "layout_css": LAYOUT_CSS, "js": JS}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(Result(
            f"motor_tuning.file.{name}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        ))
    return results


def check_reset_contract() -> list[Result]:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        layout_css = LAYOUT_CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
    except Exception as exc:
        return [Result("motor_tuning.reset_contract", False, PiSDErrorCodes.TEST_GUI_ASSET_FAILED, f"failed to read files: {exc}")]

    required = {
        "template": [
            "PiSD Motor Tuning",
            "Back to Front Page",
            "motorTuningInitialStatus",
            "mtun-empty-state",
            "Motor tuning panels removed",
            "Safety, timed motion, live preview, overlay controls, motor settings, and log panels have been removed",
        ],
        "css": [
            ".mtun-shell",
            ".mtun-hero",
            ".mtun-empty-state",
            "grid-template-columns: minmax(0, 1fr)",
        ],
        "layout_css": [
            "PiSD_0_8_7 Motor Tuning reset",
            "body.motor-tuning-page .mtun-shell",
            "grid-template-columns: minmax(0, 1fr)",
        ],
        "js": ["motorTuningInitialStatus", "mtunGlobalCode", "mtunMotorAdapter"],
    }
    sources = {"template": template, "css": css, "layout_css": layout_css, "js": js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}

    removed_tokens = [
        "mtunSafetyAck",
        "mtunEnableMotor",
        "mtunStraightSpeed",
        "mtunRunStraightForward",
        "mtunTurnDirection",
        "mtunRunTurn",
        "mtunCustomSteering",
        "mtunOverlaySurface",
        "mtunCameraPreview",
        "mtunStartCamera",
        "mtunOverlayTurnRateVisualScale",
        "mtunApplyMotor",
        "mtunApplyOverlay",
        "mtunLog",
        "mtun-panel",
        "overlay_geometry.js",
    ]
    still_present = [token for token in removed_tokens if token in template]

    old_layout_tokens = ["preview safety", "preview motion", "#motorTuningOverlayPanel", "#motorTuningSafetyPanel"]
    old_layout_present = [token for token in old_layout_tokens if token in layout_css]

    results = [Result(
        "motor_tuning.reset_contract",
        not missing,
        PiSDErrorCodes.OK if not missing else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "reset page source contract passed" if not missing else "reset page source missing required tokens",
        {"missing": missing},
    )]
    results.append(Result(
        "motor_tuning.panels_removed",
        not still_present,
        PiSDErrorCodes.OK if not still_present else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "old Motor Tuning panels and control IDs are not rendered" if not still_present else "old Motor Tuning panel/control IDs are still present",
        {"still_present": still_present},
    ))
    results.append(Result(
        "motor_tuning.layout_reset",
        not old_layout_present,
        PiSDErrorCodes.OK if not old_layout_present else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "layout override no longer assigns removed panel grid areas" if not old_layout_present else "layout CSS still references removed tuning panels",
        {"old_layout_present": old_layout_present},
    ))
    return results


def check_timed_drive_simulation() -> list[Result]:
    try:
        from pisd.services.motor_service import MotorService
    except Exception as exc:
        return [Result(
            "motor_tuning.timed_drive_simulation",
            False,
            PiSDErrorCodes.TEST_IMPORT_FAILED,
            f"MotorService import failed: {exc}",
            {"exception_type": type(exc).__name__},
        )]
    motor = MotorService({"steering_mode": "turn_rate"}, hardware_enabled=False)
    try:
        result = motor.run_timed_drive(steering=0.6, throttle=0.18, duration=0.05, label="test_motor_tuning")
        status = motor.status()
        stopped = abs(float(status.get("last_left", 0.0))) < 1e-9 and abs(float(status.get("last_right", 0.0))) < 1e-9
        ok = bool(result.get("ok")) and stopped and result.get("left_intended", 0) > result.get("right_intended", 0)
        return [Result(
            "motor_tuning.timed_drive_simulation",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED,
            "timed drive backend remains available and stops" if ok else "timed drive backend did not map/stop as expected",
            {"result": result, "last_left": status.get("last_left"), "last_right": status.get("last_right")},
        )]
    finally:
        motor.close()


def check_routes() -> list[Result]:
    try:
        from pisd.app import create_app
    except Exception as exc:
        return [Result(
            "motor_tuning.route.import",
            False,
            PiSDErrorCodes.TEST_IMPORT_FAILED,
            f"Flask app import failed: {exc}",
            {"exception_type": type(exc).__name__},
        )]
    app = create_app(hardware_enabled=False)
    client = app.test_client()
    results: list[Result] = []
    response = client.get("/motor-tuning")
    ok = response.status_code == 200 and b"PiSD Motor Tuning" in response.data and b"Motor tuning panels removed" in response.data and b"mtunRunTurn" not in response.data
    results.append(Result(
        "motor_tuning.route.page",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "/motor-tuning reset page renders" if ok else f"/motor-tuning reset page failed status={response.status_code}",
        {"status": response.status_code},
    ))
    response = client.post("/api/motor/tune-run", json={"steering": 0.5, "throttle": 0.12, "duration": 0.05, "label": "route_test"})
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and payload.get("tuning", {}).get("ok") is True
    results.append(Result(
        "motor_tuning.route.tune_run",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_API_SCHEMA_FAILED,
        "/api/motor/tune-run remains available in simulation" if ok else "/api/motor/tune-run failed",
        {"status": response.status_code, "payload_code": payload.get("code")},
    ))
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.extend(check_reset_contract())
    if not args.static_only:
        results.extend(check_timed_drive_simulation())
        results.extend(check_routes())
    for result in results:
        emit(result)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
