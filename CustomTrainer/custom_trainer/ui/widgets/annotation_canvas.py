from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from custom_trainer.services.yolo_io import PixelBox
from custom_trainer.services.annotation_history import BoxHistory, clone_boxes


class AnnotationCanvas(QWidget):
    selection_changed = Signal(int)
    boxes_changed = Signal()
    request_prev_frame = Signal()
    request_next_frame = Signal()
    request_delete_frame = Signal()

    def __init__(self, class_id_getter: Callable[[], int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.class_id_getter = class_id_getter
        self.image_path: Path | None = None
        self.pixmap = QPixmap()
        self.image_width = 0
        self.image_height = 0
        self.boxes: list[PixelBox] = []
        self.selected_index: int | None = None
        self.drag_start: QPointF | None = None
        self.drag_end: QPointF | None = None
        self.move_start_image: QPointF | None = None
        self.move_origin_box: PixelBox | None = None
        self.move_index: int | None = None
        self.right_drag_moved = False
        self.pan_start: QPointF | None = None
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0.0, 0.0)
        self.history = BoxHistory(capacity=50)
        self.setMinimumSize(360, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def minimumSizeHint(self) -> QSize:
        return QSize(360, 240)

    def sizeHint(self) -> QSize:
        return QSize(960, 720)

    @staticmethod
    def color_for_class_id(class_id: int) -> QColor:
        palette = [
            '#4f9cf8', '#ff6b6b', '#ffd166', '#06d6a0', '#c77dff', '#ff9f1c', '#2ec4b6', '#f72585',
            '#90be6d', '#577590', '#e76f51', '#43aa8b', '#4895ef', '#b5179e', '#f4a261', '#8ecae6',
        ]
        if class_id < 0:
            return QColor('#9aa4b2')
        return QColor(palette[class_id % len(palette)])

    def clear_scene(self) -> None:
        self.image_path = None
        self.pixmap = QPixmap()
        self.image_width = 0
        self.image_height = 0
        self.boxes = []
        self.selected_index = None
        self.drag_start = None
        self.drag_end = None
        self.move_start_image = None
        self.move_origin_box = None
        self.move_index = None
        self.right_drag_moved = False
        self.pan_start = None
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0.0, 0.0)
        self.history.clear()
        self.update()
        self.selection_changed.emit(-1)

    def set_scene(self, image_path: Path, boxes: list[PixelBox]) -> None:
        self.image_path = image_path
        self.pixmap = QPixmap(str(image_path))
        self.image_width = self.pixmap.width()
        self.image_height = self.pixmap.height()
        self.boxes = list(boxes)
        self.selected_index = None
        self.drag_start = None
        self.drag_end = None
        self.move_start_image = None
        self.move_origin_box = None
        self.move_index = None
        self.right_drag_moved = False
        self.pan_start = None
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0.0, 0.0)
        self.history.clear()
        self.update()
        self.selection_changed.emit(-1)

    def display_rect(self) -> QRectF:
        if self.pixmap.isNull():
            return QRectF(self.rect())
        scaled = self.pixmap.size().scaled(self.size(), Qt.KeepAspectRatio)
        width = scaled.width() * self.zoom_factor
        height = scaled.height() * self.zoom_factor
        x = (self.width() - width) / 2 + self.pan_offset.x()
        y = (self.height() - height) / 2 + self.pan_offset.y()
        return QRectF(x, y, width, height)

    def _clamp_pan(self) -> None:
        if self.pixmap.isNull() or self.zoom_factor <= 1.0:
            self.pan_offset = QPointF(0.0, 0.0)
            return
        fitted = self.pixmap.size().scaled(self.size(), Qt.KeepAspectRatio)
        half_x = max(0.0, (fitted.width() * self.zoom_factor - fitted.width()) / 2)
        half_y = max(0.0, (fitted.height() * self.zoom_factor - fitted.height()) / 2)
        self.pan_offset = QPointF(
            min(max(self.pan_offset.x(), -half_x), half_x),
            min(max(self.pan_offset.y(), -half_y), half_y),
        )

    def set_zoom(self, value: float, anchor: QPointF | None = None) -> None:
        if self.pixmap.isNull():
            return
        zoom = min(8.0, max(1.0, float(value)))
        if abs(zoom - self.zoom_factor) < 1e-6:
            return
        anchor = anchor or QPointF(self.width() / 2, self.height() / 2)
        old_rect = self.display_rect()
        u = (anchor.x() - old_rect.x()) / max(1.0, old_rect.width())
        v = (anchor.y() - old_rect.y()) / max(1.0, old_rect.height())
        self.zoom_factor = zoom
        new_rect = self.display_rect()
        self.pan_offset += QPointF(
            anchor.x() - (new_rect.x() + u * new_rect.width()),
            anchor.y() - (new_rect.y() + v * new_rect.height()),
        )
        self._clamp_pan()
        self.update()

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom_factor * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom_factor / 1.25)

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)
        self.pan_offset = QPointF(0.0, 0.0)
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.pixmap.isNull() or not (event.modifiers() & Qt.ControlModifier):
            super().wheelEvent(event)
            return
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.set_zoom(self.zoom_factor * (1.2 ** steps), event.position())
        event.accept()

    def resizeEvent(self, event) -> None:
        self._clamp_pan()
        super().resizeEvent(event)

    def widget_to_image(self, point: QPointF) -> QPointF:
        rect = self.display_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return QPointF(0, 0)
        rel_x = (point.x() - rect.x()) / rect.width()
        rel_y = (point.y() - rect.y()) / rect.height()
        rel_x = min(max(rel_x, 0.0), 1.0)
        rel_y = min(max(rel_y, 0.0), 1.0)
        return QPointF(rel_x * max(self.image_width, 1), rel_y * max(self.image_height, 1))

    def image_to_widget_rect(self, box: PixelBox) -> QRectF:
        rect = self.display_rect()
        sx = rect.width() / max(self.image_width, 1)
        sy = rect.height() / max(self.image_height, 1)
        x1, x2 = sorted((box.x1, box.x2))
        y1, y2 = sorted((box.y1, box.y2))
        return QRectF(rect.x() + x1 * sx, rect.y() + y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#0d1118'))
        if self.pixmap.isNull():
            painter.setPen(QColor('#8f9db4'))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Load a sessions folder, then choose a session and image.')
            return
        rect = self.display_rect()
        painter.drawPixmap(rect.toRect(), self.pixmap)

        draw_pen = QPen(QColor('#4f9cf8'))
        draw_pen.setWidth(2)
        draw_pen.setStyle(Qt.DashLine)

        for index, box in enumerate(self.boxes):
            box_rect = self.image_to_widget_rect(box)
            class_color = self.color_for_class_id(box.class_id)
            if index == self.selected_index:
                selected_pen = QPen(QColor('#ffffff'))
                selected_pen.setWidth(4)
                painter.setPen(selected_pen)
                painter.drawRect(box_rect)
            box_pen = QPen(class_color)
            box_pen.setWidth(2)
            painter.setPen(box_pen)
            painter.drawRect(box_rect)

            label_text = str(box.class_id)
            metrics = painter.fontMetrics()
            label_w = metrics.horizontalAdvance(label_text) + 10
            label_h = metrics.height() + 4
            label_y = max(rect.y(), box_rect.y() - label_h)
            label_rect = QRectF(box_rect.x(), label_y, label_w, label_h)
            painter.fillRect(label_rect, class_color)
            painter.setPen(QColor('#0d1118'))
            painter.drawText(label_rect, Qt.AlignCenter, label_text)

        if self.drag_start is not None and self.drag_end is not None:
            painter.setPen(draw_pen)
            painter.drawRect(QRectF(self.drag_start, self.drag_end).normalized())

    def _clone_box(self, box: PixelBox) -> PixelBox:
        return PixelBox(class_id=box.class_id, x1=box.x1, y1=box.y1, x2=box.x2, y2=box.y2)

    def _shift_box_within_bounds(self, box: PixelBox, dx: float, dy: float) -> PixelBox:
        x1 = float(box.x1) + dx
        x2 = float(box.x2) + dx
        y1 = float(box.y1) + dy
        y2 = float(box.y2) + dy

        if x1 < 0.0:
            x2 -= x1
            x1 = 0.0
        if x2 > float(self.image_width):
            overflow = x2 - float(self.image_width)
            x1 -= overflow
            x2 = float(self.image_width)
        if y1 < 0.0:
            y2 -= y1
            y1 = 0.0
        if y2 > float(self.image_height):
            overflow = y2 - float(self.image_height)
            y1 -= overflow
            y2 = float(self.image_height)

        x1 = max(0.0, x1)
        y1 = max(0.0, y1)
        x2 = min(float(self.image_width), x2)
        y2 = min(float(self.image_height), y2)
        return PixelBox(class_id=box.class_id, x1=x1, y1=y1, x2=x2, y2=y2)

    def _commit_edit(self, before: list[PixelBox], selected_before: int | None) -> bool:
        if not self.history.record(before, selected_before, self.boxes, self.selected_index):
            return False
        self.boxes_changed.emit()
        self.update()
        return True

    def undo_edit(self) -> bool:
        restored = self.history.undo(self.boxes, self.selected_index)
        if restored is None:
            return False
        self.boxes, self.selected_index = restored
        self.selection_changed.emit(-1 if self.selected_index is None else self.selected_index)
        self.boxes_changed.emit()
        self.update()
        return True

    def redo_edit(self) -> bool:
        restored = self.history.redo(self.boxes, self.selected_index)
        if restored is None:
            return False
        self.boxes, self.selected_index = restored
        self.selection_changed.emit(-1 if self.selected_index is None else self.selected_index)
        self.boxes_changed.emit()
        self.update()
        return True

    def select_next_box(self, direction: int = 1) -> bool:
        if not self.boxes:
            return False
        if self.selected_index is None:
            self.selected_index = 0 if direction >= 0 else len(self.boxes) - 1
        else:
            self.selected_index = (self.selected_index + direction) % len(self.boxes)
        self.selection_changed.emit(self.selected_index)
        self.update()
        return True

    def replace_boxes(self, boxes: list[PixelBox]) -> bool:
        """Replace quick-deploy suggestions on the current frame without resetting undo."""
        if self.pixmap.isNull():
            return False
        before = clone_boxes(self.boxes)
        selected_before = self.selected_index
        self.boxes = clone_boxes(boxes)
        self.selected_index = None
        self.selection_changed.emit(-1)
        return self._commit_edit(before, selected_before)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.pixmap.isNull():
            return
        pos = event.position()
        self.setFocus(Qt.MouseFocusReason)
        if event.button() == Qt.MiddleButton:
            self.pan_start = pos
            return
        if event.button() == Qt.RightButton:
            self.select_box_at(pos)
            if self.selected_index is not None and self.display_rect().contains(pos):
                self.move_index = self.selected_index
                self.move_start_image = self.widget_to_image(pos)
                self.move_origin_box = self._clone_box(self.boxes[self.selected_index])
                self.right_drag_moved = False
            return
        if event.button() == Qt.LeftButton and self.display_rect().contains(pos):
            self.drag_start = pos
            self.drag_end = pos
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.pan_start is not None:
            delta = event.position() - self.pan_start
            self.pan_start = event.position()
            self.pan_offset += delta
            self._clamp_pan()
            self.update()
            return
        if self.drag_start is not None:
            self.drag_end = event.position()
            self.update()
            return
        if self.move_index is None or self.move_start_image is None or self.move_origin_box is None:
            return
        if self.move_index < 0 or self.move_index >= len(self.boxes):
            return
        current_image_pos = self.widget_to_image(event.position())
        dx = current_image_pos.x() - self.move_start_image.x()
        dy = current_image_pos.y() - self.move_start_image.y()
        self.boxes[self.move_index] = self._shift_box_within_bounds(self.move_origin_box, dx, dy)
        self.right_drag_moved = True
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self.pan_start = None
            return
        if event.button() == Qt.RightButton and self.move_index is not None:
            moved = self.right_drag_moved
            before = clone_boxes(self.boxes)
            if self.move_origin_box is not None and 0 <= self.move_index < len(before):
                before[self.move_index] = self._clone_box(self.move_origin_box)
            self.move_start_image = None
            self.move_origin_box = None
            self.move_index = None
            self.right_drag_moved = False
            if moved:
                self._commit_edit(before, self.selected_index)
            return
        if self.drag_start is None or self.drag_end is None:
            return
        start = self.widget_to_image(self.drag_start)
        end = self.widget_to_image(self.drag_end)
        self.drag_start = None
        self.drag_end = None
        width = abs(end.x() - start.x())
        height = abs(end.y() - start.y())
        if width < 5 or height < 5:
            self.update()
            return
        box = PixelBox(
            class_id=self.class_id_getter(),
            x1=min(start.x(), end.x()),
            y1=min(start.y(), end.y()),
            x2=max(start.x(), end.x()),
            y2=max(start.y(), end.y()),
        )
        before = clone_boxes(self.boxes)
        selected_before = self.selected_index
        self.boxes.append(box)
        self.selected_index = len(self.boxes) - 1
        self.selection_changed.emit(self.selected_index)
        self._commit_edit(before, selected_before)

    def select_box_at(self, pos: QPointF) -> None:
        best_index: int | None = None
        best_area: float | None = None
        for index, box in enumerate(self.boxes):
            rect = self.image_to_widget_rect(box)
            if rect.contains(pos):
                area = rect.width() * rect.height()
                if best_area is None or area < best_area:
                    best_area = area
                    best_index = index
        self.selected_index = best_index
        self.selection_changed.emit(-1 if best_index is None else best_index)
        self.update()

    def delete_selected(self) -> bool:
        if self.selected_index is None:
            return False
        before = clone_boxes(self.boxes)
        selected_before = self.selected_index
        del self.boxes[self.selected_index]
        self.selected_index = None
        self.selection_changed.emit(-1)
        return self._commit_edit(before, selected_before)

    def set_selected_class_id(self, class_id: int) -> bool:
        if self.selected_index is None:
            return False
        before = clone_boxes(self.boxes)
        selected_before = self.selected_index
        self.boxes[self.selected_index].class_id = int(class_id)
        return self._commit_edit(before, selected_before)

    def nudge_selected(self, dx: float, dy: float) -> bool:
        if self.selected_index is None:
            return False
        before = clone_boxes(self.boxes)
        selected_before = self.selected_index
        self.boxes[self.selected_index] = self._shift_box_within_bounds(
            self.boxes[self.selected_index], dx, dy
        )
        return self._commit_edit(before, selected_before)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        step = 10.0 if event.modifiers() & Qt.ShiftModifier else 1.0
        handled = False

        if event.key() == Qt.Key_Backspace or event.key() == Qt.Key_Delete:
            handled = self.delete_selected()
        elif self.selected_index is not None:
            if event.key() == Qt.Key_Left:
                handled = self.nudge_selected(-step, 0.0)
            elif event.key() == Qt.Key_Right:
                handled = self.nudge_selected(step, 0.0)
            elif event.key() == Qt.Key_Up:
                handled = self.nudge_selected(0.0, -step)
            elif event.key() == Qt.Key_Down:
                handled = self.nudge_selected(0.0, step)

        if handled:
            event.accept()
            return
        super().keyPressEvent(event)
