from __future__ import annotations

import os
from typing import Any

from .demo_runtime import DemoMissionRuntime


def _make_sim_runtime(requested: str, max_cycles: int, reason: str = '') -> Any:
    runtime = DemoMissionRuntime(max_cycles=max_cycles)
    runtime.mode_requested = requested
    runtime.fallback_reason = reason
    return runtime



def create_runtime(mode: str | None = None, max_cycles: int = 2):
    requested = str(mode or os.environ.get('CUSTOMDRIVE_MODE', 'sim')).strip().lower()
    if requested != 'live':
        return _make_sim_runtime(requested, max_cycles)

    try:
        from .live_runtime import LiveMissionRuntime
    except Exception as exc:
        return _make_sim_runtime(
            requested,
            max_cycles,
            reason=f'Live runtime import failed, using sim instead: {exc}',
        )

    try:
        runtime = LiveMissionRuntime(max_cycles=max_cycles)
        runtime.mode_requested = requested
        runtime.fallback_reason = ''
        return runtime
    except Exception as exc:
        return _make_sim_runtime(
            requested,
            max_cycles,
            reason=f'Live runtime failed, using sim instead: {exc}',
        )
