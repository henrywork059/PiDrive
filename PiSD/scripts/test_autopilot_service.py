#!/usr/bin/env python3
"""Validate the retired scripted AutopilotService shim.

PiSD 0.5.2 replaced scripted Autopilot with AI Mode. This test makes sure
old imports cannot accidentally start movement and that stale callers receive
an explicit AI Mode replacement response.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.autopilot_service import AutopilotService  # noqa: E402

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
        return {
            "label": self.label,
            "ok": bool(self.ok),
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def main() -> int:
    auto = AutopilotService()
    results: list[Result] = []

    status = auto.status()
    status_ok = (
        status.get("deprecated") is True
        and status.get("replaced_by") == "ai_mode"
        and status.get("route") == "/ai-mode"
        and status.get("running") is False
        and status.get("profiles") == []
    )
    results.append(Result(
        "autopilot.deprecated_status",
        status_ok,
        PiSDErrorCodes.OK if status_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "scripted Autopilot reports retired AI Mode shim status" if status_ok else "scripted Autopilot status did not report retired shim",
        {"status": status},
    ))

    start_payload = auto.start({"mode": "straight_slow", "safety_ack": True, "enable_motor_output": True})
    start_ok = (
        start_payload.get("ok") is False
        and start_payload.get("code") == PiSDErrorCodes.AI_MODEL_NOT_LOADED
        and start_payload.get("ai_mode_route") == "/ai-mode"
        and "removed" in str(start_payload.get("message", "")).lower()
    )
    results.append(Result(
        "autopilot.start_blocked",
        start_ok,
        PiSDErrorCodes.OK if start_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "scripted Autopilot start is blocked and points to AI Mode" if start_ok else "scripted Autopilot start did not return the expected AI Mode block",
        {"payload": start_payload},
    ))

    stop_payload = auto.stop("test_stop")
    stopped_status = stop_payload.get("autopilot") or {}
    stop_ok = stop_payload.get("ok") is True and stopped_status.get("running") is False and stopped_status.get("deprecated") is True
    results.append(Result(
        "autopilot.stop_safe_noop",
        stop_ok,
        PiSDErrorCodes.OK if stop_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "scripted Autopilot stop is a safe no-op" if stop_ok else "scripted Autopilot stop did not return a safe no-op payload",
        {"payload": stop_payload},
    ))

    for result in results:
        emit(result)
    ok_all = all(r.ok for r in results)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps({"ok": ok_all, "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    print(json.dumps({
        "summary": str(SUMMARY_PATH),
        "code": PiSDErrorCodes.OK if ok_all else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "failed": sum(1 for r in results if not r.ok),
    }, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
