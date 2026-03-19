from __future__ import annotations

import os

from .demo_runtime import DemoMissionRuntime
from .live_runtime import LiveMissionRuntime


def create_runtime(mode: str | None = None, max_cycles: int = 2):
    requested = str(mode or os.environ.get("CUSTOMDRIVE_MODE", "sim")).strip().lower()
    if requested == "live":
        try:
            runtime = LiveMissionRuntime(max_cycles=max_cycles)
            runtime.mode_requested = requested
            runtime.fallback_reason = ""
            return runtime
        except Exception as exc:
            runtime = DemoMissionRuntime(max_cycles=max_cycles)
            runtime.mode_requested = requested
            runtime.fallback_reason = f"Live runtime failed, using sim instead: {exc}"
            return runtime
    runtime = DemoMissionRuntime(max_cycles=max_cycles)
    runtime.mode_requested = requested
    runtime.fallback_reason = ""
    return runtime
