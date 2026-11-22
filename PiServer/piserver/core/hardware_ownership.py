"""One-process-at-a-time lease for Raspberry Pi motor and camera hardware.

PiServer and CustomDrive import the *same* PiServer services. Both must agree
on the same lock file. The file is NEVER unlinked: unlinking a live flock file
would allow two different processes to own two different inodes.
"""
from __future__ import annotations

import errno
import os
import stat
import threading
from pathlib import Path


DEFAULT_LOCK_PATH = "/tmp/pidrive-physical-hardware.lock"
_GUARD = threading.RLock()
_FD: int | None = None
_HOLDERS: set[str] = set()
_PID = os.getpid()


class HardwareOwnershipError(RuntimeError):
    """The physical Raspberry Pi hardware is owned by another runtime."""


def _lock_path() -> Path:
    path = Path(os.environ.get("PIDRIVE_HARDWARE_LOCK_FILE", DEFAULT_LOCK_PATH))
    if not path.is_absolute():
        raise HardwareOwnershipError("PIDRIVE_HARDWARE_LOCK_FILE must be an absolute path.")
    return path


def _fresh_process_state() -> None:
    """Child processes must not inherit the parent's lease bookkeeping."""
    global _FD, _HOLDERS, _PID, _GUARD
    # This hook runs after fork in the child. Do not call flock(UN) on the
    # inherited open-file description: doing so would unlock the parent's lease.
    if _FD is not None:
        os.close(_FD)
    _FD = None
    _HOLDERS = set()
    _PID = os.getpid()
    _GUARD = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_fresh_process_state)


class HardwareLease:
    def __init__(self, resource: str):
        self.resource = resource
        self._active = False
        self._pid: int | None = None

    def acquire(self) -> "HardwareLease":
        global _FD, _PID
        if os.name != "posix":
            raise HardwareOwnershipError("Physical hardware ownership needs POSIX advisory file locks.")
        import fcntl

        with _GUARD:
            if self._active:
                return self
            if _PID != os.getpid():
                _fresh_process_state()
            if self.resource in _HOLDERS:
                raise HardwareOwnershipError(
                    f"PiDrive {self.resource} hardware already opened in this process. "
                    "Stop the existing runtime before starting another."
                )
            if _FD is None:
                path = _lock_path()
                flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
                try:
                    fd = os.open(path, flags, 0o600)
                    if not stat.S_ISREG(os.fstat(fd).st_mode):
                        raise HardwareOwnershipError(f"Hardware lock path is not a regular file: {path}")
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    os.ftruncate(fd, 0)
                    os.write(fd, f"PiDrive hardware owner pid={os.getpid()}\n".encode("ascii"))
                    _FD = fd
                except OSError as exc:
                    os.close(fd) if "fd" in locals() else None
                    if exc.errno in (errno.EACCES, errno.EAGAIN):
                        raise HardwareOwnershipError(
                            "Physical camera/motor hardware is already in use by another PiDrive process. "
                            "Stop its server and retry; do not force the motors on."
                        ) from exc
                    raise HardwareOwnershipError(f"Could not obtain hardware lock {path}: {exc}") from exc
                except Exception:
                    os.close(fd)
                    raise
            _HOLDERS.add(self.resource)
            self._active = True
            self._pid = os.getpid()
            return self

    def release(self) -> None:
        global _FD
        import fcntl
        with _GUARD:
            if not self._active or self._pid != os.getpid():
                return
            self._active = False
            self._pid = None
            _HOLDERS.discard(self.resource)
            if not _HOLDERS and _FD is not None:
                fd, _FD = _FD, None
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)


def claim_hardware(resource: str) -> HardwareLease:
    if resource not in {"motor", "camera"}:
        raise ValueError("Hardware resource must be 'motor' or 'camera'.")
    return HardwareLease(resource).acquire()
