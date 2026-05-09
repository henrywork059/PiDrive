#!/usr/bin/env python3
"""Check PiSD error-code/reporting helpers and service status schema.

This script does not require Flask or real Pi hardware. It verifies that future
service work can expose code/message/recent_errors fields consistently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import load_defaults  # noqa: E402
from pisd.core.errors import ErrorReporter, PiSDErrorCodes, ok_payload, report_payload  # noqa: E402
from pisd.services.camera_service import CameraService  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise AssertionError(f"{code}: {message}")


def main() -> int:
    reporter = ErrorReporter("test")
    report = reporter.report(PiSDErrorCodes.TEST_API_SCHEMA_FAILED, "Synthetic error-reporting check.")
    error_payload = report_payload(False, report)
    success_payload = ok_payload("Schema check OK.")

    require(error_payload.get("code") == PiSDErrorCodes.TEST_API_SCHEMA_FAILED, PiSDErrorCodes.TEST_API_SCHEMA_FAILED, "error payload missing code")
    require(error_payload.get("error", {}).get("component") == "test", PiSDErrorCodes.TEST_API_SCHEMA_FAILED, "error payload missing component")
    require(success_payload.get("code") == PiSDErrorCodes.OK, PiSDErrorCodes.TEST_API_SCHEMA_FAILED, "ok payload missing OK code")

    defaults = load_defaults()
    camera = CameraService(defaults.get("camera"), hardware_enabled=False)
    motor = MotorService(defaults.get("motor"), hardware_enabled=False)
    try:
        camera_status = camera.status()
        motor_status = motor.status()
        for service_name, status in (("camera", camera_status), ("motor", motor_status)):
            require("last_error_code" in status, PiSDErrorCodes.TEST_API_SCHEMA_FAILED, f"{service_name} status missing last_error_code")
            require("recent_errors" in status, PiSDErrorCodes.TEST_API_SCHEMA_FAILED, f"{service_name} status missing recent_errors")
            require(status["last_error_code"], PiSDErrorCodes.TEST_API_SCHEMA_FAILED, f"{service_name} status has empty code")
    finally:
        motor.close()
        camera.stop()

    print(
        json.dumps(
            {
                "ok": True,
                "code": PiSDErrorCodes.OK,
                "checked": ["ErrorReporter", "ok_payload", "report_payload", "camera.status", "motor.status"],
                "synthetic_error": error_payload,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(json.dumps({"ok": False, "code": PiSDErrorCodes.TEST_API_SCHEMA_FAILED, "message": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
