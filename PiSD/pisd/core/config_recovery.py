"""Preserve malformed user configuration before replacing it (F7)."""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path

LOG = logging.getLogger(__name__)


class ConfigRecovery:
    def __init__(self, path: Path):
        self.path = path
        self.warning = ""
        self.backup_name = ""
        self.write_blocked = False

    def status(self):
        return {"warning": self.warning, "backup": self.backup_name,
                "write_blocked": self.write_blocked, "source": self.path.name}

    def read(self):
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError:
            self.write_blocked = True
            self.warning = "Runtime configuration cannot be read; saving is blocked."
            LOG.warning("Cannot read runtime configuration %s; refusing replacement.", self.path)
            raise
        return data

    def preserve(self, raw: bytes):
        # Deterministic name avoids repeated identical copies after a restart.
        # Never overwrite an existing backup, and verify exact bytes before use.
        digest = hashlib.sha256(raw).hexdigest()[:20]
        backup = self.path.with_name(self.path.name + ".corrupt-" + digest + ".bak")
        created = False
        try:
            try:
                fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if backup.is_symlink() or not backup.is_file() or backup.read_bytes() != raw:
                    raise OSError("Existing recovery copy does not match original.")
            else:
                created = True
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
            self.backup_name = backup.name
            self.write_blocked = False
            self.warning = ("Malformed runtime configuration detected. Original bytes preserved in "
                            + backup.name + ". Review this recovery copy before relying on fallback settings.")
            LOG.warning("Malformed configuration %s; recovery copy %s.", self.path, backup)
        except OSError:
            if created:
                try:
                    backup.unlink()
                except OSError:
                    pass
            self.write_blocked = True
            self.warning = "Malformed configuration could not be backed up; saving is blocked."
            LOG.warning("Cannot preserve malformed configuration %s; refusing replacement.", self.path)
            raise

    def write(self, raw: bytes, expected):
        # The store holds its process lock. Also refuse a detected external
        # change instead of overwriting it with the previously checked contents.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=self.path.parent,
                                             prefix=self.path.name + ".", suffix=".tmp",
                                             delete=False) as handle:
                name = handle.name
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            if self.read() != expected:
                self.write_blocked = True
                self.warning = "Runtime configuration changed during save; reload and retry."
                raise OSError("Configuration changed during save.")
            os.replace(name, self.path)
            self.write_blocked = False
        finally:
            if name is not None:
                Path(name).unlink(missing_ok=True)
