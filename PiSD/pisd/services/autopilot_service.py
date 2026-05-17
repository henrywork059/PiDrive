from __future__ import annotations

from typing import Any

from pisd.core.errors import PiSDErrorCodes, ok_payload, report_payload, ErrorReporter


class AutopilotService:
    """Deprecated scripted autopilot shim.

    PiSD_0_5_2 replaces the earlier scripted Autopilot foundation with AI Mode.
    This compatibility class intentionally exposes no scripted movement profiles,
    so stale imports from a previously applied 0_5_1 patch cannot run the old
    scripted autopilot by accident.
    """

    def __init__(self, *_args: Any, **_kwargs: Any):
        self.errors = ErrorReporter("autopilot_deprecated")

    def status(self) -> dict[str, Any]:
        return {
            "deprecated": True,
            "replaced_by": "ai_mode",
            "route": "/ai-mode",
            "running": False,
            "profiles": [],
            "code": PiSDErrorCodes.OK,
            "message": "Scripted Autopilot has been replaced by AI Mode.",
        }

    def start(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        report = self.errors.report(
            PiSDErrorCodes.AI_MODEL_NOT_LOADED,
            "Scripted Autopilot has been removed. Use AI Mode with a loaded model instead.",
            severity="warning",
        )
        return report_payload(False, report, ai_mode_route="/ai-mode")

    def stop(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return ok_payload("Deprecated scripted Autopilot is not running.", autopilot=self.status())
