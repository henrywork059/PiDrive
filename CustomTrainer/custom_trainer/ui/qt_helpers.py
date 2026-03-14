from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QObject, Signal, Slot


class CommandWorker(QObject):
    line = Signal(str)
    finished = Signal(int)

    def __init__(self, command: Sequence[str], cwd: Path | None = None) -> None:
        super().__init__()
        self.command = list(command)
        self.cwd = cwd

    @Slot()
    def run(self) -> None:
        self.line.emit('$ ' + ' '.join(self.command))
        try:
            process = subprocess.Popen(
                self.command,
                cwd=str(self.cwd) if self.cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.line.emit(line.rstrip())
            process.wait()
            code = int(process.returncode or 0)
        except Exception as exc:  # pragma: no cover - defensive runtime path
            self.line.emit(f'[error] {exc}')
            code = -1
        self.line.emit(f'[exit code] {code}')
        self.finished.emit(code)
