"""Mission 1 terminal safety reasons and compact, atomic run reports.

A successful servo-position command is never proof that an object was gripped.
Sensor confirmation is intentionally unavailable in the current arm interface.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class MissionAbort(RuntimeError):
    """A fail-closed mission stop that requires an explicit new Start action."""

    REASONS = frozenset({
        'target_lost', 'frame_stale', 'arm_unavailable',
        'grip_unconfirmed', 'retry_exhausted', 'operator_stopped',
    })

    def __init__(self, reason: str, message: str) -> None:
        if reason not in self.REASONS:
            raise ValueError(f'Unknown mission safety reason: {reason}')
        super().__init__(message)
        self.reason = reason


def save_mission_report(report_root: Path, report: dict[str, Any]) -> Path:
    """Commit one compact JSON report; never replace an existing session report."""
    report_root = Path(report_root)
    report_root.mkdir(parents=True, exist_ok=True)
    session_id = str(report.get('session_id') or '')
    if not session_id or not session_id.isascii() or not session_id.isalnum():
        raise ValueError('Mission report requires an ASCII alphanumeric session ID.')
    destination = report_root / f'mission1_{session_id}.json'
    if destination.exists():
        raise FileExistsError(f'Mission report already exists: {destination}')
    payload = (json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    fd, staging = tempfile.mkstemp(prefix='.mission1_', suffix='.tmp', dir=report_root)
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), 0o600) if hasattr(os, 'fchmod') else None
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        # Exclusive hard-link publication avoids replacing an existing report
        # even if another process raced during staging.
        os.link(staging, destination)
        return destination
    finally:
        Path(staging).unlink(missing_ok=True)
