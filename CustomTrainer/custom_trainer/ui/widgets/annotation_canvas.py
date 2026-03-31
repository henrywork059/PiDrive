from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from custom_trainer.services.yolo_io import PixelBox


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
        self.update()
        self.selection_changed.emit(-1)

    def display_rect(self) -> QRectF:
        if self.pixmap.isNull():
            return QRectF(self.rect())
        scaled = self.pixmap.size().scaled(self.size(), Qt.KeepAspectRatio)
        x = (self.width() - scaled.width()) / 2
        y = (self.height() - scaled.height()) / 2
        return QRectF(x, y, scaled.width(), scaled.height())

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

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.pixmap.isNull():
            return
        pos = event.position()
        self.setFocus(Qt.MouseFocusReason)
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
        if event.button() == Qt.RightButton and self.move_index is not None:
            moved = self.right_drag_moved
            self.move_start_image = None
            self.move_origin_box = None
            self.move_index = None
            self.right_drag_moved = False
            if moved:
                self.boxes_changed.emit()
                self.update()
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
        self.boxes.append(box)
        self.selected_index = len(self.boxes) - 1
        self.selection_changed.emit(self.selected_index)
        self.boxes_changed.emit()
        self.update()

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
        del self.boxes[self.selected_index]
        self.selected_index = None
        self.selection_changed.emit(-1)
        self.boxes_changed.emit()
        self.update()
        return True

    def set_selected_class_id(self, class_id: int) -> bool:
        if self.selected_index is None:
            return False
        self.boxes[self.selected_index].class_id = int(class_id)
        self.boxes_changed.emit()
        self.update()
        return True

    def nudge_selected(self, dx: float, dy: float) -> bool:
        if self.selected_index is None:
            return False
        box = self.boxes[self.selected_index]
        box.x1 = min(max(0.0, box.x1 + dx), float(self.image_width))
        box.x2 = min(max(0.0, box.x2 + dx), float(self.image_width))
        box.y1 = min(max(0.0, box.y1 + dy), float(self.image_height))
        box.y2 = min(max(0.0, box.y2 + dy), float(self.image_height))
        self.boxes_changed.emit()
        self.update()
        return True

    def keyPressEvent(self, event: QKeyEvent) -> None:
        step = 10.0 if event.modifiers() & Qt.ShiftModifier else 1.0
        handled = False

        if event.key() == Qt.Key_A:
            self.request_prev_frame.emit()
            handled = True
        elif event.key() == Qt.Key_D:
            self.request_next_frame.emit()
            handled = True
        elif event.key() == Qt.Key_X:
            self.request_delete_frame.emit()
            handled = True
        elif event.key() == Qt.Key_Backspace or event.key() == Qt.Key_Delete:
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
