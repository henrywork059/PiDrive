"""Bounded, scene-local annotation undo/redo independent of Qt widgets.

Only committed changes are recorded. Undo/redo never writes YOLO files; the
Marking page retains its existing explicit-save/autosave-on-switch policy.
"""
from __future__ import annotations

from dataclasses import dataclass

from custom_trainer.services.yolo_io import PixelBox


@dataclass(frozen=True)
class BoxSnapshot:
    boxes: tuple[tuple[int, float, float, float, float], ...]
    selected: int | None


def clone_boxes(boxes: list[PixelBox]) -> list[PixelBox]:
    return [PixelBox(int(box.class_id), float(box.x1), float(box.y1),
                     float(box.x2), float(box.y2)) for box in boxes]


def make_snapshot(boxes: list[PixelBox], selected: int | None) -> BoxSnapshot:
    safe_selected = selected if selected is not None and 0 <= selected < len(boxes) else None
    return BoxSnapshot(
        tuple((int(b.class_id), float(b.x1), float(b.y1),
               float(b.x2), float(b.y2)) for b in boxes),
        safe_selected,
    )


def restore_snapshot(snapshot: BoxSnapshot) -> tuple[list[PixelBox], int | None]:
    return ([PixelBox(*values) for values in snapshot.boxes], snapshot.selected)


class BoxHistory:
    def __init__(self, capacity: int = 50):
        self.capacity = max(1, int(capacity))
        self._undo: list[BoxSnapshot] = []
        self._redo: list[BoxSnapshot] = []

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def record(self, before_boxes: list[PixelBox], before_selected: int | None,
               after_boxes: list[PixelBox], after_selected: int | None) -> bool:
        before = make_snapshot(before_boxes, before_selected)
        after = make_snapshot(after_boxes, after_selected)
        if before.boxes == after.boxes:
            return False
        self._undo.append(before)
        del self._undo[:-self.capacity]
        self._redo.clear()
        return True

    def undo(self, current_boxes: list[PixelBox], selected: int | None) -> tuple[list[PixelBox], int | None] | None:
        if not self._undo:
            return None
        self._redo.append(make_snapshot(current_boxes, selected))
        del self._redo[:-self.capacity]
        return restore_snapshot(self._undo.pop())

    def redo(self, current_boxes: list[PixelBox], selected: int | None) -> tuple[list[PixelBox], int | None] | None:
        if not self._redo:
            return None
        self._undo.append(make_snapshot(current_boxes, selected))
        del self._undo[:-self.capacity]
        return restore_snapshot(self._redo.pop())
