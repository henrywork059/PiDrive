from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
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
    """A vertical stack of collapsible controls for one dock/sidebar tab."""

    def __init__(self, sections: Iterable[tuple[str, QWidget, bool]], *, margins: tuple[int, int, int, int] = (8, 8, 8, 8)) -> None:
        super().__init__()
        self.setObjectName('controlStack')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*margins)
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


def make_workflow_tabs(
    tabs: Iterable[tuple[str, QWidget]],
    *,
    object_name: str = 'workflowTabs',
    tab_position: QTabWidget.TabPosition = QTabWidget.North,
) -> QTabWidget:
    """Create a compact tab widget for groups of workflow controls.

    This is used when one long collapsible sidebar is still too tall. Each tab can
    contain its own scroll area / ControlStack so only one task family is visible
    at a time.
    """
    tab_widget = QTabWidget()
    tab_widget.setObjectName(object_name)
    tab_widget.setDocumentMode(True)
    tab_widget.setTabPosition(tab_position)
    for title, widget in tabs:
        tab_widget.addTab(widget, title)
    return tab_widget


def make_scrollable_stack(
    sections: Iterable[tuple[str, QWidget, bool]],
    *,
    object_name: str = 'workflowScrollArea',
    margins: tuple[int, int, int, int] = (8, 8, 8, 8),
) -> QScrollArea:
    """Convenience helper for one scrollable stack of collapsible sections."""
    return make_scroll_area(ControlStack(sections, margins=margins), object_name=object_name)
