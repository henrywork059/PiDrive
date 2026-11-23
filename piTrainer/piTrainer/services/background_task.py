"""One-shot worker and GUI-thread lifecycle for non-cancellable long operations.

Jobs accept a progress callback (step, percentage or None). Worker functions must
consume immutable/snapshotted inputs and must never access Qt widgets.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import QObject, QThread, Signal


class BackgroundTaskWorker(QThread):
    step_changed = Signal(str, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation: Callable, parent=None) -> None:
        super().__init__(parent)
        self._operation = operation

    def _report(self, step: str, percent: int | None = None) -> None:
        value = -1 if percent is None else max(0, min(100, int(percent)))
        self.step_changed.emit(str(step), value)

    def run(self) -> None:
        try:
            result = self._operation(self._report)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)


class BackgroundTaskRunner(QObject):
    """Own one worker until QThread.finished; no unsafe thread termination."""

    def __init__(self, progress_panel, parent=None) -> None:
        super().__init__(parent)
        self.progress_panel = progress_panel
        self.worker: BackgroundTaskWorker | None = None
        self._controls: tuple = ()
        self._active = False
        self._title = ''

    @property
    def active(self) -> bool:
        return self._active

    def start(
        self,
        title: str,
        operation: Callable,
        on_success: Callable,
        on_failure: Callable | None = None,
        controls: Iterable = (),
    ) -> bool:
        if self._active:
            return False
        self._active = True
        self._title = str(title)
        self._controls = tuple(controls)
        for control in self._controls:
            control.setEnabled(False)
        self.progress_panel.begin(self._title)
        worker = BackgroundTaskWorker(operation, self)
        self.worker = worker
        worker.step_changed.connect(self.progress_panel.set_step)
        worker.succeeded.connect(lambda result: self._success(result, on_success))
        worker.failed.connect(lambda message: self._failure(message, on_failure))
        worker.finished.connect(self._finished)
        worker.start()
        return True

    def _success(self, result, callback: Callable) -> None:
        try:
            message, paths = callback(result)
        except Exception as exc:
            self._failure(str(exc), None)
            return
        self.progress_panel.succeed(str(message), paths)

    def _failure(self, message: str, callback: Callable | None) -> None:
        self.progress_panel.fail(message)
        if callback is not None:
            callback(message)

    def _finished(self) -> None:
        for control in self._controls:
            control.setEnabled(True)
        self._controls = ()
        self._active = False
        # Keep the QThread wrapper until its finished signal has been handled.
        self.worker = None
