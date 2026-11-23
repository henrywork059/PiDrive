"""Crash-safe replacement of existing PiDrive recording metadata files.

Updates are atomic *per JSONL file*. A companion labels.jsonl / records.jsonl
pair is not a multi-file transaction. Caller must propagate errors rather than
reporting a successful edit when a replacement was refused.
"""
from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Iterable


FileSignature = tuple[int, int, int, int]


def file_signature(path: Path) -> FileSignature:
    """Detect external writes and replacements, including equal-length files."""
    st = Path(path).stat()
    return int(st.st_dev), int(st.st_ino), int(st.st_mtime_ns), int(st.st_size)


def _preserve_first_recovery_copy(path: Path, expected_signature: FileSignature) -> None:
    """Keep the untouched pre-edit metadata once, without replacing old backups.

    Stage and fsync the backup before publishing its name using an exclusive
    hard link. The link targets our completed temporary copy, not the live
    JSONL inode, so future recorder appends cannot mutate the recovery copy.
    """
    backup_path = path.with_name(f'{path.name}.pitrainer-original.bak')
    if backup_path.exists():
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='wb', prefix=f'.{path.name}.backup-', suffix='.tmp',
            dir=path.parent, delete=False,
        ) as staged:
            temporary = Path(staged.name)
            with path.open('rb') as original:
                shutil.copyfileobj(original, staged)
            staged.flush()
            os.fsync(staged.fileno())
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        if file_signature(path) != expected_signature:
            raise RuntimeError(f"Metadata changed on disk; reload before editing: {path}")
        try:
            os.link(temporary, backup_path)
        except FileExistsError:
            pass  # Keep an earlier recovery copy; never overwrite it.
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def replace_jsonl_lines(path: Path, lines: Iterable[str], *, expected_signature: FileSignature) -> None:
    """Write a complete same-directory temporary file, fsync, then replace.

    Refuse to overwrite source metadata that changed since it was loaded.
    This check is optimistic, not a lock shared with an external recorder:
    writers modifying a file *after* the check and before os.replace can race.
    """
    path = Path(path)
    original = path.stat()
    if file_signature(path) != expected_signature:
        raise RuntimeError(f"Metadata changed on disk; reload before editing: {path}")

    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', newline='',
            prefix=f'.{path.name}.', suffix='.tmp',
            dir=path.parent, delete=False,
        ) as handle:
            staged_path = Path(handle.name)
            handle.writelines(lines)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(staged_path, stat.S_IMODE(original.st_mode))
        if file_signature(path) != expected_signature:
            raise RuntimeError(f"Metadata changed on disk; reload before editing: {path}")
        _preserve_first_recovery_copy(path, expected_signature)
        if file_signature(path) != expected_signature:
            raise RuntimeError(f"Metadata changed on disk; reload before editing: {path}")
        os.replace(staged_path, path)
        staged_path = None
        # An atomic rename does not guarantee the directory entry is durable
        # across power loss. Sync it where supported (best-effort on Windows).
        if os.name == 'posix' and hasattr(os, 'O_DIRECTORY'):
            try:
                fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                pass  # Content was already atomically committed.
    finally:
        if staged_path is not None:
            try:
                staged_path.unlink(missing_ok=True)
            except OSError:
                pass
