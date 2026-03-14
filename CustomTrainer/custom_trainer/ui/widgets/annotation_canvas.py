from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from custom_trainer.utils.yolo_io import PixelBox


class AnnotationCanvas(QWidget):
    boxes_changed = Signal()
    selection_changed = Signal(int)

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
        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)

    def set_scene(self, image_path: Path, boxes: list[PixelBox]) -> None:
        self.image_path = image_path
        self.pixmap = QPixmap(str(image_path))
        self.image_width = self.pixmap.width()
        self.image_height = self.pixmap.height()
        self.boxes = list(boxes)
        self.selected_index = None
        self.drag_start = None
        self.drag_end = None
        self.update()

    def set_boxes(self, boxes: list[PixelBox]) -> None:
        self.boxes = list(boxes)
        self.update()

    def display_rect(self) -> QRectF:
        if self.pixmap.isNull():
            return QRectF(0, 0, self.width(), self.height())
        scaled = self.pixmap.size().scaled(self.size(), Qt.KeepAspectRatio)
        x = (self.width() - scaled.width()) / 2
        y = (self.height() - scaled.height()) / 2
        return QRectF(x, y, scaled.width(), scaled.height())

    def widget_to_image(self, point: QPointF) -> QPointF:
        rect = self.display_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return QPointF()
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
        painter.fillRect(self.rect(), QColor('#0f141c'))
        if self.pixmap.isNull():
            painter.setPen(QColor('#8b94a7'))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Load an image folder to start annotating.')
            return
        rect = self.display_rect()
        painter.drawPixmap(rect.toRect(), self.pixmap)

        normal_pen = QPen(QColor('#7CFC00'))
        normal_pen.setWidth(2)
        selected_pen = QPen(QColor('#ffd54a'))
        selected_pen.setWidth(3)
        text_color = QColor('#f7fbff')

        for index, box in enumerate(self.boxes):
            box_rect = self.image_to_widget_rect(box)
            painter.setPen(selected_pen if index == self.selected_index else normal_pen)
            painter.drawRect(box_rect)
            painter.setPen(text_color)
            painter.drawText(box_rect.adjusted(4, 4, -4, -4), str(box.class_id))

        if self.drag_start is not None and self.drag_end is not None:
            painter.setPen(QPen(QColor('#56a7ff'), 2, Qt.DashLine))
            painter.drawRect(QRectF(self.drag_start, self.drag_end).normalized())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.pixmap.isNull():
            return
        pos = event.position()
        if event.button() == Qt.LeftButton and self.display_rect().contains(pos):
            self.drag_start = pos
            self.drag_end = pos
            self.update()
            return
        if event.button() == Qt.RightButton:
            self.select_box_at(pos)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_start is None:
            return
        self.drag_end = event.position()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.drag_start is None or self.drag_end is None:
            return
        start = self.widget_to_image(self.drag_start)
        end = self.widget_to_image(self.drag_end)
        self.drag_start = None
        self.drag_end = None
        if abs(end.x() - start.x()) < 5 or abs(end.y() - start.y()) < 5:
            self.update()
            return
        class_id = self.class_id_getter()
        self.boxes.append(PixelBox(class_id=class_id, x1=start.x(), y1=start.y(), x2=end.x(), y2=end.y()))
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
