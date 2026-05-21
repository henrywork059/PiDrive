from __future__ import annotations

from collections.abc import Iterable
from typing import Sequence

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


SectionSpec = tuple[str, QWidget, bool] | tuple[str, QWidget, bool, str]
TabSpec = tuple[str, QWidget] | tuple[str, QWidget, str]





def make_page_banner(step: str, title: str, summary: str, next_step: str = '') -> QFrame:
    """Create a consistent page header that explains the current workflow stage."""
    banner = QFrame()
    banner.setObjectName('pageBanner')
    banner.setProperty('role', 'pageBanner')
    banner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    title_label = QLabel(f"{step}  {title}".strip())
    title_label.setObjectName('pageBannerTitle')
    title_label.setProperty('role', 'pageBannerTitle')
    title_label.setWordWrap(False)

    summary_label = QLabel(summary)
    summary_label.setObjectName('pageBannerSummary')
    summary_label.setProperty('role', 'pageBannerSummary')
    summary_label.setWordWrap(True)
    summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    text_layout = QVBoxLayout()
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(3)
    text_layout.addWidget(title_label)
    text_layout.addWidget(summary_label)

    layout = QHBoxLayout(banner)
    layout.setContentsMargins(14, 11, 14, 11)
    layout.setSpacing(14)
    layout.addLayout(text_layout, 1)

    if next_step:
        next_label = QLabel(next_step)
        next_label.setObjectName('pageBannerNext')
        next_label.setProperty('role', 'pageBannerNext')
        next_label.setWordWrap(True)
        next_label.setMinimumWidth(230)
        next_label.setMaximumWidth(380)
        layout.addWidget(next_label, 0, Qt.AlignRight | Qt.AlignVCenter)

    return banner

def style_next_step_button(button: QPushButton, text: str | None = None) -> QPushButton:
    """Make the forward workflow action obvious, wide, and gently animated.

    The animation is intentionally slow/subtle: it only toggles a stylesheet
    property so the button breathes instead of flashing harshly.
    """
    if text is not None:
        button.setText(text)
    button.setProperty('role', 'nextStep')
    button.setProperty('pulse', False)
    button.setMinimumHeight(42)
    button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    button.setCursor(Qt.PointingHandCursor)
    if not button.toolTip():
        button.setToolTip('Recommended next step in the workflow.')

    timer = QTimer(button)
    timer.setInterval(1450)

    def toggle_pulse() -> None:
        button.setProperty('pulse', not bool(button.property('pulse')))
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    timer.timeout.connect(toggle_pulse)
    timer.start()
    button._next_step_pulse_timer = timer  # keep a Python reference for PySide
    return button

def make_hint_label(text: str, *, object_name: str = 'quickHint') -> QLabel:
    """Create a consistent wrapped helper label for dense workflow panels."""
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setProperty('role', 'hint')
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


def standardize_form_layout(form: QFormLayout) -> QFormLayout:
    """Apply the same readable form behaviour across all dense config panels."""
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.setFormAlignment(Qt.AlignTop)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(9)
    return form


class CollapsibleSection(QWidget):
    """Reusable disclosure section for dense control sidebars.

    It keeps advanced controls available without forcing every field to be visible
    at once. The header remains visible, so users can recognise the available
    action without needing to remember where it lives.
    """

    def __init__(self, title: str, content: QWidget, expanded: bool = True, tooltip: str = '') -> None:
        super().__init__()
        self.setObjectName('collapsibleSection')
        self.content = content

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName('collapsibleSectionHeader')
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setAutoRaise(False)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.toggle_button.setToolTip(tooltip)
        self.toggle_button.clicked.connect(self.set_expanded)

        self.content_frame = QFrame()
        self.content_frame.setObjectName('collapsibleSectionBody')
        self.content_frame.setFrameShape(QFrame.NoFrame)
        body_layout = QVBoxLayout(self.content_frame)
        body_layout.setContentsMargins(10, 9, 10, 11)
        body_layout.setSpacing(9)
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
    """Vertical stack of collapsible controls for one workflow/sidebar tab."""

    def __init__(
        self,
        sections: Iterable[SectionSpec],
        *,
        intro: str | None = None,
        margins: tuple[int, int, int, int] = (10, 10, 10, 10),
    ) -> None:
        super().__init__()
        self.setObjectName('controlStack')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*margins)
        layout.setSpacing(11)
        if intro:
            intro_label = make_hint_label(intro, object_name='sidebarIntro')
            intro_label.setProperty('role', 'intro')
            layout.addWidget(intro_label)
        for section in sections:
            title, widget, expanded, *rest = section
            tooltip = str(rest[0]) if rest else ''
            layout.addWidget(CollapsibleSection(title, widget, expanded=expanded, tooltip=tooltip))
        layout.addStretch(1)


def make_scroll_area(widget: QWidget, *, object_name: str = 'pageScrollArea') -> QScrollArea:
    """Wrap a panel/sidebar so it remains usable when the dock is short."""
    scroll = QScrollArea()
    scroll.setObjectName(object_name)
    scroll.setProperty('role', 'workflowScroll')
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setWidget(widget)
    return scroll


def make_workflow_tabs(
    tabs: Iterable[TabSpec],
    *,
    object_name: str = 'workflowTabs',
    tab_position: QTabWidget.TabPosition = QTabWidget.North,
) -> QTabWidget:
    """Create a compact task-family tab widget for workflow controls."""
    tab_widget = QTabWidget()
    tab_widget.setObjectName(object_name)
    tab_widget.setProperty('role', 'workflowTabs')
    tab_widget.setDocumentMode(True)
    tab_widget.setMovable(False)
    tab_widget.setUsesScrollButtons(True)
    tab_widget.setElideMode(Qt.ElideRight)
    tab_widget.setTabPosition(tab_position)
    for entry in tabs:
        title, widget, *rest = entry
        index = tab_widget.addTab(widget, title)
        if rest:
            tab_widget.setTabToolTip(index, str(rest[0]))
    return tab_widget


def make_scrollable_stack(
    sections: Iterable[SectionSpec],
    *,
    object_name: str = 'workflowScrollArea',
    intro: str | None = None,
    margins: tuple[int, int, int, int] = (10, 10, 10, 10),
) -> QScrollArea:
    """Convenience helper for one scrollable stack of collapsible sections."""
    return make_scroll_area(ControlStack(sections, intro=intro, margins=margins), object_name=object_name)
