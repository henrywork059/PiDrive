#!/usr/bin/env python3
"""Validate PiSD Motor Tuning page and timed tuning motor command.

The static checks do not move motors. The service check runs in simulation mode
and verifies that the new timed-drive helper always stops after the requested
short duration.
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
from pisd.services.motor_service import MotorService  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
TEMPLATE = WEB_ROOT / "templates" / "motor_tuning.html"
CSS = WEB_ROOT / "static" / "css" / "motor_tuning.css"
JS = WEB_ROOT / "static" / "js" / "motor_tuning.js"
OVERLAY_JS = WEB_ROOT / "static" / "js" / "overlay_geometry.js"
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
    parser = argparse.ArgumentParser(description="Validate PiSD Motor Tuning page.")
    parser.add_argument("--static-only", action="store_true", help="Skip Flask route and service checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": TEMPLATE, "css": CSS, "js": JS, "overlay_js": OVERLAY_JS}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(Result(
            f"motor_tuning.file.{name}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        ))
    return results


def check_source_contract() -> list[Result]:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
    except Exception as exc:
        return [Result("motor_tuning.source_contract", False, PiSDErrorCodes.TEST_GUI_ASSET_FAILED, f"failed to read files: {exc}")]

    required = {
        "template": [
            "PiSD Motor Tuning",
            "Back to Front Page",
            "motorTuningInitialStatus",
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
            "mtunOverlayCurveResponse",
            "mtunApplyMotor",
            "mtunApplyOverlay",
            "mtunStartDeadzone",
            "mtunStartKickSeconds",
            "Intended motor output",
        ],
        "css": [".mtun-shell", ".mtun-panel", ".mtun-overlay-preview", ".mtun-camera-preview", ".mtun-overlay-edge", "grid-template-columns: repeat(2, minmax(0, 1fr))", "marker-end: url(#mtunOverlayArrow)", "@media (max-width: 1180px)"],
        "js": [
            "motorTuningInitialStatus",
            "/api/motor/tune-run",
            "/api/settings/apply",
            "/api/control/stop",
            "roadGuideGeometry",
            "startLiveCamera",
            "runTimed",
            "saveOverlaySettings",
            "saveMotorSettings",
            "intendedOutputFrom",
            "left_intended",
            "start_deadzone",
            "start_kick_seconds",
        ],
    }
    sources = {"template": template, "css": css, "js": js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    results = [Result(
        "motor_tuning.source_contract",
        not missing,
        PiSDErrorCodes.OK if not missing else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "motor tuning source contract passed" if not missing else "motor tuning source missing required tokens",
        {"missing": missing},
    )]
    hero_index = template.find("mtun-kicker")
    back_index = template.find("Back to Front Page")
    nav_index = template.find("mtun-status-strip")
    compact_preview_ok = "min-height: clamp(160px, 24vh, 300px)" in css and "max-height: min(34vh, 320px)" in css
    equal_columns_ok = "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    manual_overlay_style_ok = all(token in css for token in ("rgba(236, 253, 245, .96)", "marker-end: url(#mtunOverlayArrow)", "drop-shadow(0 0 4px rgba(34, 197, 94, .42))"))
    back_nav_ok = nav_index >= 0 and back_index > nav_index and back_index > hero_index
    results.append(Result(
        "motor_tuning.back_link_in_header_actions",
        back_nav_ok,
        PiSDErrorCodes.OK if back_nav_ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "Back to Front Page is in the header action/status area" if back_nav_ok else "Back link is still placed inside the title block",
        {"hero_index": hero_index, "nav_index": nav_index, "back_index": back_index},
    ))
    results.append(Result(
        "motor_tuning.preview_compact",
        compact_preview_ok,
        PiSDErrorCodes.OK if compact_preview_ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "live camera overlay preview height is capped to a compact calibration size" if compact_preview_ok else "live preview height cap is missing or too large",
        {},
    ))
    results.append(Result(
        "motor_tuning.equal_columns",
        equal_columns_ok,
        PiSDErrorCodes.OK if equal_columns_ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "Motor Tuning shell uses two equal halves on desktop" if equal_columns_ok else "Motor Tuning shell is not using two equal halves",
        {},
    ))
    results.append(Result(
        "motor_tuning.manual_overlay_style",
        manual_overlay_style_ok,
        PiSDErrorCodes.OK if manual_overlay_style_ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "Motor Tuning overlay uses the same green road-edge and blue centre-arrow style as Manual Drive" if manual_overlay_style_ok else "Motor Tuning overlay style does not match Manual Drive",
        {},
    ))
    return results


def check_timed_drive_simulation() -> list[Result]:
    motor = MotorService({"steering_mode": "turn_rate", "start_deadzone": 0.25, "start_kick_seconds": 0.03}, hardware_enabled=False)
    try:
        result = motor.run_timed_drive(steering=0.6, throttle=0.18, duration=0.05, label="test_motor_tuning")
        status = motor.status()
        stopped = abs(float(status.get("last_left", 0.0))) < 1e-9 and abs(float(status.get("last_right", 0.0))) < 1e-9
        ok = bool(result.get("ok")) and stopped and result.get("left_intended", 0) > result.get("right_intended", 0)
        return [Result(
            "motor_tuning.timed_drive_simulation",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_MOTOR_CHANNEL_FAILED,
            "timed drive uses turn-rate mapping and stops" if ok else "timed drive did not map/stop as expected",
            {"result": result, "last_left": status.get("last_left"), "last_right": status.get("last_right")},
        )]
    finally:
        motor.close()


def check_routes() -> list[Result]:
    app = create_app(hardware_enabled=False)
    client = app.test_client()
    results: list[Result] = []
    response = client.get("/motor-tuning")
    ok = response.status_code == 200 and b"PiSD Motor Tuning" in response.data and b"mtunRunTurn" in response.data
    results.append(Result(
        "motor_tuning.route.page",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_GUI_ASSET_FAILED,
        "/motor-tuning renders" if ok else f"/motor-tuning failed status={response.status_code}",
        {"status": response.status_code},
    ))
    response = client.post("/api/motor/tune-run", json={"steering": 0.5, "throttle": 0.12, "duration": 0.05, "label": "route_test"})
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and payload.get("tuning", {}).get("ok") is True
    results.append(Result(
        "motor_tuning.route.tune_run",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_API_SCHEMA_FAILED,
        "/api/motor/tune-run completes in simulation" if ok else "/api/motor/tune-run failed",
        {"status": response.status_code, "payload_code": payload.get("code")},
    ))
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.extend(check_source_contract())
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
