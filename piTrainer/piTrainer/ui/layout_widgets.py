from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """Small reusable disclosure section for dense control sidebars."""

    def __init__(self, title: str, content: QWidget, expanded: bool = True) -> None:
        super().__init__()
        self.setObjectName('collapsibleSection')
        self.content = content

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName('collapsibleSectionHeader')
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.clicked.connect(self.set_expanded)

        self.content_frame = QFrame()
        self.content_frame.setObjectName('collapsibleSectionBody')
        self.content_frame.setFrameShape(QFrame.NoFrame)
        body_layout = QVBoxLayout(self.content_frame)
        body_layout.setContentsMargins(8, 8, 8, 10)
        body_layout.setSpacing(8)
        body_layout.addWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_frame)

        self.set_expanded(expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.content_frame.setVisible(expanded)


class ControlStack(QWidget):
    """A vertical stack of collapsible controls for one dock sidebar."""

    def __init__(self, sections: Iterable[tuple[str, QWidget, bool]]) -> None:
        super().__init__()
        self.setObjectName('controlStack')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        for title, widget, expanded in sections:
            layout.addWidget(CollapsibleSection(title, widget, expanded=expanded))
        layout.addStretch(1)


def make_scroll_area(widget: QWidget, *, object_name: str = 'pageScrollArea') -> QScrollArea:
    """Wrap a panel/sidebar so it remains usable when the dock is short."""
    scroll = QScrollArea()
    scroll.setObjectName(object_name)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setWidget(widget)
    return scroll
