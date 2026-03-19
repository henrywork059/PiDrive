from __future__ import annotations

from math import isfinite

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class LinePlotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = 'Training Progress'
        self._metric_name = ''
        self._x_values: list[float] = []
        self._y_values: list[float] = []
        self._summary = 'No training metric loaded yet.'
        self.setMinimumHeight(220)

    def clear(self, summary: str = 'No training metric loaded yet.') -> None:
        self._metric_name = ''
        self._x_values = []
        self._y_values = []
        self._summary = summary
        self.update()

    def set_series(self, *, title: str, metric_name: str, x_values: list[float], y_values: list[float], summary: str) -> None:
        filtered: list[tuple[float, float]] = []
        for x_value, y_value in zip(x_values, y_values):
            if isfinite(x_value) and isfinite(y_value):
                filtered.append((float(x_value), float(y_value)))
        self._title = title or 'Training Progress'
        self._metric_name = metric_name
        self._x_values = [item[0] for item in filtered]
        self._y_values = [item[1] for item in filtered]
        self._summary = summary
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())

        margin_left = 52
        margin_right = 18
        margin_top = 34
        margin_bottom = 44
        plot_rect = QRectF(
            margin_left,
            margin_top,
            max(10.0, self.width() - margin_left - margin_right),
            max(10.0, self.height() - margin_top - margin_bottom),
        )

        painter.setPen(self.palette().mid().color())
        painter.drawRect(plot_rect)

        title_rect = QRectF(12, 8, self.width() - 24, 20)
        painter.setPen(self.palette().text().color())
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self._title)

        summary_rect = QRectF(12, self.height() - 26, self.width() - 24, 18)
        painter.setPen(self.palette().mid().color())
        painter.drawText(summary_rect, Qt.AlignLeft | Qt.AlignVCenter, self._summary)

        if len(self._x_values) < 2 or len(self._y_values) < 2:
            painter.setPen(self.palette().mid().color())
            painter.drawText(plot_rect, Qt.AlignCenter, 'No plotted data yet.')
            return

        x_min = min(self._x_values)
        x_max = max(self._x_values)
        y_min = min(self._y_values)
        y_max = max(self._y_values)
        if x_max <= x_min:
            x_max = x_min + 1.0
        if y_max <= y_min:
            y_pad = max(abs(y_min) * 0.1, 1.0)
            y_min -= y_pad
            y_max += y_pad
        else:
            y_pad = max((y_max - y_min) * 0.08, 1e-6)
            y_min -= y_pad
            y_max += y_pad

        def map_point(x_value: float, y_value: float) -> QPointF:
            x_ratio = (x_value - x_min) / (x_max - x_min)
            y_ratio = (y_value - y_min) / (y_max - y_min)
            return QPointF(
                plot_rect.left() + x_ratio * plot_rect.width(),
                plot_rect.bottom() - y_ratio * plot_rect.height(),
            )

        grid_pen = QPen(self.palette().mid().color())
        grid_pen.setStyle(Qt.DashLine)
        painter.setPen(grid_pen)
        grid_lines = 4
        for index in range(grid_lines + 1):
            ratio = index / grid_lines
            y = plot_rect.top() + ratio * plot_rect.height()
            painter.drawLine(plot_rect.left(), y, plot_rect.right(), y)
            value = y_max - ratio * (y_max - y_min)
            painter.drawText(6, int(y + 4), f'{value:.3f}')

        axis_pen = QPen(self.palette().text().color())
        painter.setPen(axis_pen)
        painter.drawText(int(plot_rect.left()), self.height() - 30, f'{x_min:.0f}')
        painter.drawText(int(plot_rect.right()) - 18, self.height() - 30, f'{x_max:.0f}')
        if self._metric_name:
            painter.drawText(int(plot_rect.left()), int(plot_rect.top()) - 8, self._metric_name)

        path = QPainterPath()
        first_point = map_point(self._x_values[0], self._y_values[0])
        path.moveTo(first_point)
        for x_value, y_value in zip(self._x_values[1:], self._y_values[1:]):
            path.lineTo(map_point(x_value, y_value))

        line_pen = QPen(QColor('#56b6f2'))
        line_pen.setWidth(2)
        painter.setPen(line_pen)
        painter.drawPath(path)

        point_pen = QPen(QColor('#c9d1d9'))
        point_pen.setWidth(1)
        painter.setPen(point_pen)
        for x_value, y_value in zip(self._x_values, self._y_values):
            point = map_point(x_value, y_value)
            painter.drawEllipse(point, 2.5, 2.5)
