from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider

from .theme import theme_color


def _style_value(flat_name: str, enum_name: str, member_name: str):
    value = getattr(QStyle, flat_name, None)
    if value is not None:
        return value
    enum = getattr(QStyle, enum_name)
    return getattr(enum, member_name)


class CenteredFillSlider(QSlider):
    """Horizontal slider that fills outward from a configurable centre value.

    Qt's built-in horizontal slider fill starts at the minimum value. That works
    for speed, but it makes steering look wrong because the neutral steering
    point is the middle of the range. This widget keeps all QSlider interaction
    behaviour and only custom-paints the steering track so left/right corrections
    fill away from zero.
    """

    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, *, center_value: int = 0) -> None:
        super().__init__(orientation)
        self.center_value = int(center_value)
        self.setProperty("role", "centerFillSlider")
        self.setMouseTracking(True)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if self.orientation() != Qt.Horizontal:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        option = QStyleOptionSlider()
        self.initStyleOption(option)
        style = self.style()
        slider_control = _style_value("CC_Slider", "ComplexControl", "CC_Slider")
        groove_control = _style_value("SC_SliderGroove", "SubControl", "SC_SliderGroove")
        handle_control = _style_value("SC_SliderHandle", "SubControl", "SC_SliderHandle")
        groove = style.subControlRect(slider_control, option, groove_control, self)
        handle = style.subControlRect(slider_control, option, handle_control, self)

        track_height = 7.0
        track = QRectF(
            float(groove.left()),
            float(groove.center().y()) - track_height / 2.0,
            float(groove.width()),
            track_height,
        )

        enabled = self.isEnabled()
        track_color = QColor(theme_color("slider_track" if enabled else "bg_input"))
        fill_color = QColor(theme_color("slider_center_fill" if enabled else "scroll_handle"))
        marker_color = QColor(theme_color("slider_center_marker" if enabled else "border"))
        handle_color = QColor(theme_color("slider_handle" if enabled else "text_disabled"))
        handle_border = QColor(theme_color("slider_handle_border" if enabled else "border_subtle"))

        painter.setPen(QPen(QColor(theme_color("border_subtle")), 1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, 3.5, 3.5)

        center_x = self._x_for_value(self.center_value, track)
        value_x = self._x_for_value(self.value(), track)
        fill_left = min(center_x, value_x)
        fill_width = abs(value_x - center_x)
        if fill_width >= 1.0:
            fill_rect = QRectF(fill_left, track.top(), fill_width, track.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill_color)
            painter.drawRoundedRect(fill_rect, 3.5, 3.5)

        painter.setPen(QPen(marker_color, 2))
        painter.drawLine(int(round(center_x)), int(track.top()) - 4, int(round(center_x)), int(track.bottom()) + 4)

        radius = max(8.0, min(13.0, float(handle.height()) / 2.0))
        handle_rect = QRectF(
            float(handle.center().x()) - radius,
            float(track.center().y()) - radius,
            radius * 2.0,
            radius * 2.0,
        )
        painter.setPen(QPen(handle_border, 2))
        painter.setBrush(handle_color)
        painter.drawEllipse(handle_rect)
        event.accept()

    def _x_for_value(self, value: int, track: QRectF) -> float:
        minimum = self.minimum()
        maximum = self.maximum()
        if maximum <= minimum:
            return float(track.left())
        safe_value = max(minimum, min(maximum, int(value)))
        ratio = (safe_value - minimum) / float(maximum - minimum)
        return float(track.left()) + ratio * float(track.width())
