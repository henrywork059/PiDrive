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
from pisd.services.camera_service import CameraService  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "standard_validation"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


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
