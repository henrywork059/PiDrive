"""Conservative, non-destructive free-space guard for PiDrive recordings.

No sessions are ever deleted automatically.  Configuration uses optional
per-component environment overrides, so existing runtime.json remains intact.
"""
from __future__ import annotations

import errno
import os
import shutil
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

_MIB = 1024 * 1024


class RecordingStorageError(OSError):
    """New recording writes are blocked until storage is healthy."""


def _threshold_mib(env_name: str, default: int) -> int:
    try:
        value = int(os.environ.get(env_name, str(default)))
        return max(1, min(1024 * 1024, value))
    except (TypeError, ValueError, OverflowError):
        return default


class RecordingStorageGuard:
    def __init__(self, root: Path | str, *, prefix: str):
        self.root = Path(root)
        self.critical_bytes = _threshold_mib(prefix + '_RECORDING_MIN_FREE_MB', 256) * _MIB
        self.warning_bytes = max(self.critical_bytes, _threshold_mib(prefix + '_RECORDING_WARN_FREE_MB', 512) * _MIB)
        self._lock = threading.RLock()
        self._recent_errors: deque[dict[str, str]] = deque(maxlen=5)
        self._session_cache: tuple[str, float, int] | None = None

    def _existing_directory(self) -> Path:
        path = self.root
        while not path.exists() and path.parent != path:
            path = path.parent
        return path

    def check(self, *, estimated_bytes: int = 0) -> dict[str, Any]:
        """Read actual free space (statvfs/disk_usage). Never delete old data."""
        try:
            usage = shutil.disk_usage(self._existing_directory())
            free_bytes, total_bytes = int(usage.free), int(usage.total)
            status = ('critical' if free_bytes < self.critical_bytes + max(0, int(estimated_bytes))
                      else 'warning' if free_bytes < self.warning_bytes else 'ok')
            return {
                'state': status, 'free_bytes': free_bytes, 'total_bytes': total_bytes,
                'warning_bytes': self.warning_bytes, 'critical_bytes': self.critical_bytes,
            }
        except (OSError, ValueError, OverflowError) as exc:
            return {
                'state': 'unavailable', 'free_bytes': None, 'total_bytes': None,
                'warning_bytes': self.warning_bytes, 'critical_bytes': self.critical_bytes,
                'message': f'Unable to check recording storage: {exc}',
            }

    def require_space(self, *, estimated_bytes: int = 0) -> dict[str, Any]:
        result = self.check(estimated_bytes=estimated_bytes)
        if result['state'] in ('critical', 'unavailable'):
            free = result.get('free_bytes')
            if free is None:
                message = result['message']
            else:
                message = (f'Recording stopped: only {free // _MIB} MiB free; '
                           f'requires at least {self.critical_bytes // _MIB} MiB '
                           'plus the pending write. Existing sessions were not deleted.')
            raise RecordingStorageError(errno.ENOSPC, message)
        return result

    def note_error(self, operation: str, error: BaseException) -> None:
        with self._lock:
            self._recent_errors.append({
                'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'operation': str(operation)[:80], 'message': str(error)[:500],
            })

    def recent_errors(self) -> list[dict[str, str]]:
        with self._lock:
            return list(self._recent_errors)

    def session_size(self, session_path: Path | str | None) -> int:
        """Cached metadata/JPEG size check; no recursive scan on every poll."""
        if not session_path:
            return 0
        path = Path(session_path)
        key = str(path)
        now = time.monotonic()
        with self._lock:
            cached = self._session_cache
            if cached is not None and cached[0] == key and now - cached[1] < 2.0:
                return cached[2]
        size = 0
        try:
            for base, _dirs, files in os.walk(path):
                for name in files:
                    try:
                        size += (Path(base) / name).stat().st_size
                    except OSError:
                        continue
        except OSError:
            pass
        with self._lock:
            self._session_cache = (key, now, size)
        return size

    def status(self, session_path: Path | str | None = None) -> dict[str, Any]:
        result = self.check()
        result['recent_write_errors'] = self.recent_errors()
        result['session_size_bytes'] = self.session_size(session_path)
        result['cleanup_policy'] = 'manual_confirmation_only'
        return result
