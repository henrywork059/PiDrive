from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QTableView


class CyclingPreviewTable(QTableView):
    """Record table that keeps Up/Down navigation cycling through frame rows."""

    def __init__(self, owner: "PreviewPanel") -> None:
        super().__init__()
        self.owner = owner

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt API name
        key = event.key()
        # Let Shift/Ctrl selection shortcuts keep Qt's normal extended-selection behaviour.
        if key in (Qt.Key_Down, Qt.Key_Up) and not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier)):
            step = 1 if key == Qt.Key_Down else -1
            if self.owner.select_adjacent_record(step):
                event.accept()
                return
        super().keyPressEvent(event)
