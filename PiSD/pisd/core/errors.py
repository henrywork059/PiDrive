from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

OK_CODE = "PISD-OK-000"


class PiSDErrorCodes:
    """Shared PiSD error-code registry.

    Prefix convention:
    - PISD-APP: launcher/config/app factory errors
    - PISD-API: HTTP/API request or response errors
    - PISD-CAM: camera dependency, setup, capture, and encode errors
    - PISD-MOT: GPIO/motor setup, update, and shutdown errors
    - PISD-TEST: test-script validation errors
    """

    OK = OK_CODE

    APP_CONFIG_LOAD_FAILED = "PISD-APP-001"
    APP_DEPENDENCY_MISSING = "PISD-APP-002"
    APP_STARTUP_FAILED = "PISD-APP-003"

    API_INVALID_JSON = "PISD-API-001"
    API_SERVICE_EXCEPTION = "PISD-API-002"
    API_NOT_FOUND = "PISD-API-003"
    API_UNHANDLED_EXCEPTION = "PISD-API-004"

    CAMERA_PICAMERA2_MISSING = "PISD-CAM-001"
    CAMERA_OPEN_FAILED = "PISD-CAM-002"
    CAMERA_CONTROL_APPLY_FAILED = "PISD-CAM-003"
    CAMERA_CAPTURE_FAILED = "PISD-CAM-004"
    CAMERA_ENCODE_FAILED = "PISD-CAM-005"
    CAMERA_NO_FRAME = "PISD-CAM-006"
    CAMERA_STOP_FAILED = "PISD-CAM-007"
    CAMERA_COLOR_CONTROL_FAILED = "PISD-CAM-008"
    CAMERA_SETTING_INVALID = "PISD-CAM-009"
    CAMERA_CAPABILITY_QUERY_FAILED = "PISD-CAM-010"

    MOTOR_GPIO_MISSING = "PISD-MOT-001"
    MOTOR_GPIO_SETUP_FAILED = "PISD-MOT-002"
    MOTOR_OUTPUT_FAILED = "PISD-MOT-003"
    MOTOR_STOP_FAILED = "PISD-MOT-004"
    MOTOR_CLOSE_FAILED = "PISD-MOT-005"
    MOTOR_CONFIG_INVALID = "PISD-MOT-006"
    MOTOR_TEST_INVALID = "PISD-MOT-007"
    MOTOR_TEST_UNARMED = "PISD-MOT-008"
    MOTOR_TEST_OUTPUT_FAILED = "PISD-MOT-009"

    TEST_IMPORT_FAILED = "PISD-TEST-001"
    TEST_CAMERA_FRAME_MISSING = "PISD-TEST-002"
    TEST_MOTOR_STOP_FAILED = "PISD-TEST-003"
    TEST_API_SCHEMA_FAILED = "PISD-TEST-004"
    TEST_CAMERA_COLOR_DIAGNOSTIC_FAILED = "PISD-TEST-005"
    TEST_CAMERA_SETTINGS_MATRIX_FAILED = "PISD-TEST-006"
    TEST_MOTOR_CHANNEL_FAILED = "PISD-TEST-007"
    TEST_STANDARD_VALIDATION_FAILED = "PISD-TEST-008"
    TEST_GUI_ROUTE_FAILED = "PISD-TEST-009"
    TEST_GUI_ASSET_FAILED = "PISD-TEST-010"
    TEST_GUI_API_CONTRACT_FAILED = "PISD-TEST-011"
    TEST_PANEL_GUI_CONTRACT_FAILED = "PISD-TEST-012"
    TEST_PANEL_CONTRACT_SKIPPED = "PISD-TEST-013"
    TEST_PANEL_API_CONTRACT_FAILED = "PISD-TEST-014"
    TEST_MAIN_DASHBOARD_CONTRACT_FAILED = "PISD-TEST-015"
    TEST_FRONT_PAGE_CONTRACT_FAILED = "PISD-TEST-016"
    TEST_CAMERA_FPS_FAILED = "PISD-TEST-017"
    TEST_PANEL_PRESENTATION_FAILED = "PISD-TEST-018"
    TEST_MANUAL_DRIVE_CONTRACT_FAILED = "PISD-TEST-019"


@dataclass(frozen=True)
class ErrorReport:
    code: str
    message: str
    component: str = "general"
    severity: str = "error"
    context: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    exception_type: str = ""
    traceback: str = ""

    def as_dict(self, include_traceback: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "component": self.component,
            "severity": self.severity,
            "timestamp_utc": self.timestamp_utc,
            "context": dict(self.context),
        }
        if self.exception_type:
            data["exception_type"] = self.exception_type
        if include_traceback and self.traceback:
            data["traceback"] = self.traceback
        return data


class ErrorReporter:
    """Thread-safe bounded error/warning history for services and tests."""

    def __init__(self, component: str, max_history: int = 50):
        self.component = component
        self.max_history = max(1, int(max_history))
        self._history: list[ErrorReport] = []
        self._lock = RLock()

    def report(
        self,
        code: str,
        message: str,
        *,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        exc: BaseException | None = None,
        include_traceback: bool = False,
    ) -> ErrorReport:
        report = ErrorReport(
            code=str(code),
            message=str(message),
            component=self.component,
            severity=str(severity),
            context=dict(context or {}),
            exception_type=type(exc).__name__ if exc is not None else "",
            traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            if exc is not None and include_traceback
            else "",
        )
        with self._lock:
            self._history.append(report)
            if len(self._history) > self.max_history:
                del self._history[: len(self._history) - self.max_history]
        return report

    def latest(self) -> ErrorReport | None:
        with self._lock:
            return self._history[-1] if self._history else None

    def history(self, *, limit: int = 10, include_traceback: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            selected = self._history[-max(1, int(limit)) :]
        return [item.as_dict(include_traceback=include_traceback) for item in selected]

    def clear(self) -> None:
        with self._lock:
            self._history.clear()

    def status_fields(self, *, limit: int = 5) -> dict[str, Any]:
        latest = self.latest()
        return {
            "last_error_code": latest.code if latest else OK_CODE,
            "last_error": latest.message if latest else "",
            "last_error_severity": latest.severity if latest else "ok",
            "recent_errors": self.history(limit=limit),
        }


def ok_payload(message: str = "OK", **fields: Any) -> dict[str, Any]:
    payload = {"ok": True, "code": OK_CODE, "message": message}
    payload.update(fields)
    return payload


def report_payload(ok: bool, report: ErrorReport | None, message: str | None = None, **fields: Any) -> dict[str, Any]:
    if report is None:
        payload = {"ok": bool(ok), "code": OK_CODE if ok else PiSDErrorCodes.API_SERVICE_EXCEPTION, "message": message or "OK"}
    else:
        payload = {
            "ok": bool(ok),
            "code": report.code,
            "message": message or report.message,
            "error": report.as_dict(),
        }
    payload.update(fields)
    return payload
