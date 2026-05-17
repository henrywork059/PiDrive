#!/usr/bin/env python3
"""Validate the bounded AutopilotService in simulation mode."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import load_defaults  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.autopilot_service import AutopilotService  # noqa: E402
from pisd.services.motor_service import MotorService  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "autopilot_service"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "ok": bool(self.ok), "code": self.code, "message": self.message, "details": dict(self.details)}


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def main() -> int:
    defaults = load_defaults()
    motor = MotorService(defaults.get("motor"), hardware_enabled=False)
    auto = AutopilotService(motor, {"mode": "straight_slow", "max_throttle": 0.12, "max_run_seconds": 1.0, "tick_hz": 5}, hardware_enabled=False)
    results: list[Result] = []
    ok, message, status, report = auto.start({"mode": "straight_slow", "max_throttle": 0.12, "max_run_seconds": 1.0})
    results.append(Result("autopilot.refuses_unarmed_start", not ok and report and report.code == PiSDErrorCodes.AUTOPILOT_NOT_ARMED, PiSDErrorCodes.OK if (not ok and report and report.code == PiSDErrorCodes.AUTOPILOT_NOT_ARMED) else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "unarmed start refused" if not ok else "unarmed start was not refused", {"message": message, "status": status.get("running")}))
    ok, message, status, report = auto.start({"mode": "straight_slow", "max_throttle": 0.12, "max_run_seconds": 1.0, "tick_hz": 5, "safety_ack": True, "enable_motor_output": True})
    results.append(Result("autopilot.starts_when_armed", ok and status.get("running") is True, PiSDErrorCodes.OK if ok and status.get("running") is True else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "armed start accepted" if ok else message, {"status": status}))
    time.sleep(0.25)
    running_status = auto.status()
    moving = abs(float(running_status.get("last_command", {}).get("throttle", 0))) > 0.01
    results.append(Result("autopilot.emits_command", moving, PiSDErrorCodes.OK if moving else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "autopilot emitted throttle command" if moving else "no throttle command emitted", {"status": running_status}))
    stopped = auto.stop("test_stop")
    motor_status = motor.status()
    stopped_ok = not stopped.get("running") and abs(float(motor_status.get("last_left", 1))) < 1e-6 and abs(float(motor_status.get("last_right", 1))) < 1e-6
    results.append(Result("autopilot.stop_zeros_motors", stopped_ok, PiSDErrorCodes.OK if stopped_ok else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "stop returned motors to zero" if stopped_ok else "stop did not clear motor outputs", {"autopilot": stopped, "motor": motor_status}))
    motor.close()
    for result in results:
        emit(result)
    ok_all = all(r.ok for r in results)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps({"ok": ok_all, "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(SUMMARY_PATH), "code": PiSDErrorCodes.OK if ok_all else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "failed": sum(1 for r in results if not r.ok)}, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
