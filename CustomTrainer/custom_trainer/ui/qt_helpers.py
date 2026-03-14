from __future__ import annotations

import locale
import os
import subprocess
import threading
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QObject, Signal, Slot


_PREFERRED_ENCODINGS = tuple(
    dict.fromkeys(
        filter(
            None,
            (
                'utf-8',
                locale.getpreferredencoding(False),
                getattr(locale, 'getencoding', lambda: None)(),
                'cp950',
                'mbcs',
            ),
        )
    )
)


def _decode_output(raw: bytes) -> str:
    for encoding in _PREFERRED_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


class CommandWorker(QObject):
    line = Signal(str)
    finished = Signal(int)

    def __init__(self, command: Sequence[str], cwd: Path | None = None) -> None:
        super().__init__()
        self.command = list(command)
        self.cwd = cwd
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()
        self._stop_requested = False

    @Slot()
    def run(self) -> None:
        self.line.emit('$ ' + ' '.join(self.command))
        try:
            env = os.environ.copy()
            env.setdefault('PYTHONUTF8', '1')
            env.setdefault('PYTHONIOENCODING', 'utf-8')
            process = subprocess.Popen(
                self.command,
                cwd=str(self.cwd) if self.cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
                env=env,
            )
            with self._lock:
                self._process = process
            assert process.stdout is not None
            while True:
                raw_line = process.stdout.readline()
                if not raw_line:
                    break
                self.line.emit(_decode_output(raw_line).rstrip())
            process.wait()
            code = int(process.returncode or 0)
        except Exception as exc:
            self.line.emit(f'[error] {exc}')
            code = -1
        finally:
            with self._lock:
                self._process = None
        if self._stop_requested:
            self.line.emit('[stopped] Stop requested by user.')
        self.line.emit(f'[exit code] {code}')
        self.finished.emit(code)

    @Slot()
    def request_stop(self) -> None:
        with self._lock:
            process = self._process
            self._stop_requested = True
        if process is None:
            return
        self.line.emit('[stop] Terminating running process...')
        try:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.line.emit('[stop] Process did not exit in time. Killing it...')
                process.kill()
        except Exception as exc:
            self.line.emit(f'[stop-error] {exc}')
