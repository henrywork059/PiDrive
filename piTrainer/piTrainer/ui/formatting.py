from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .theme import THEME_COLORS

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QBoxLayout,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QWidget,
)


FORMAT_VERSION = "0_7_0_stable_v7_baseline"


@dataclass(frozen=True)
class DensityProfile:
    """Single source of truth for visual density metrics.

    Add or tune font, padding, tab, input, and scrollbar values here rather than
    scattering presentation numbers across pages and panels.
    """

    base_font: int
    banner_title: int
    button_min: int
    next_min: int
    input_min: int
    main_tab_min: int
    workflow_tab_min: int
    scrollbar: int
    banner_margin: tuple[int, int, int, int]
    banner_spacing: int
    page_margin: tuple[int, int, int, int]
    page_spacing: int
    panel_margin: tuple[int, int, int, int]
    panel_spacing: int
    section_body_margin: tuple[int, int, int, int]
    section_spacing: int
    stack_margin: tuple[int, int, int, int]
    stack_spacing: int
    form_h_spacing: int
    form_v_spacing: int
    splitter_handle_width: int
    workflow_min_width: int
    panel_min_width: int
    workflow_frame_min_width: int
    panel_frame_min_width: int


DENSITY_PROFILES: Mapping[str, DensityProfile] = {
    "compact": DensityProfile(
        base_font=12,
        banner_title=16,
        button_min=24,
        next_min=36,
        input_min=24,
        main_tab_min=104,
        workflow_tab_min=72,
        scrollbar=7,
        banner_margin=(9, 5, 9, 5),
        banner_spacing=4,
        page_margin=(6, 5, 6, 6),
        page_spacing=6,
        panel_margin=(6, 5, 6, 6),
        panel_spacing=5,
        section_body_margin=(6, 5, 6, 6),
        section_spacing=5,
        stack_margin=(6, 6, 6, 6),
        stack_spacing=6,
        form_h_spacing=8,
        form_v_spacing=5,
        splitter_handle_width=5,
        workflow_min_width=240,
        panel_min_width=200,
        workflow_frame_min_width=96,
        panel_frame_min_width=110,
    ),
    "comfortable": DensityProfile(
        base_font=13,
        banner_title=17,
        button_min=26,
        next_min=38,
        input_min=25,
        main_tab_min=118,
        workflow_tab_min=78,
        scrollbar=8,
        banner_margin=(10, 6, 10, 6),
        banner_spacing=5,
        page_margin=(8, 7, 8, 8),
        page_spacing=7,
        panel_margin=(7, 6, 7, 7),
        panel_spacing=6,
        section_body_margin=(7, 6, 7, 8),
        section_spacing=6,
        stack_margin=(7, 7, 7, 7),
        stack_spacing=8,
        form_h_spacing=9,
        form_v_spacing=6,
        splitter_handle_width=5,
        workflow_min_width=260,
        panel_min_width=220,
        workflow_frame_min_width=110,
        panel_frame_min_width=130,
    ),
    "spacious": DensityProfile(
        base_font=13,
        banner_title=18,
        button_min=28,
        next_min=40,
        input_min=26,
        main_tab_min=132,
        workflow_tab_min=86,
        scrollbar=8,
        banner_margin=(11, 6, 11, 6),
        banner_spacing=5,
        page_margin=(10, 8, 10, 10),
        page_spacing=8,
        panel_margin=(8, 7, 8, 8),
        panel_spacing=7,
        section_body_margin=(8, 7, 8, 9),
        section_spacing=7,
        stack_margin=(8, 8, 8, 8),
        stack_spacing=9,
        form_h_spacing=10,
        form_v_spacing=7,
        splitter_handle_width=6,
        workflow_min_width=280,
        panel_min_width=235,
        workflow_frame_min_width=120,
        panel_frame_min_width=150,
    ),
}


SPLITTER_PRESETS: Mapping[str, Mapping[str, Sequence[int]]] = {
    "three_panel_workspace": {
        "sizes": (320, 600, 620),
        "stretch": (1, 2, 2),
        "minimums": (260, 300, 300),
    },
    "two_panel_workspace": {
        "sizes": (320, 1040),
        "stretch": (1, 3),
        "minimums": (260, 420),
    },
    "train_three_panel_workspace": {
        "sizes": (320, 620, 480),
        "stretch": (1, 2, 2),
        "minimums": (260, 320, 300),
    },
    "validation_three_panel_workspace": {
        "sizes": (320, 560, 520),
        "stretch": (1, 2, 2),
        "minimums": (260, 300, 300),
    },
    "preview_over_plot": {
        "sizes": (640, 230),
        "stretch": (5, 2),
        "minimums": (220, 120),
    },
    "preview_over_results": {
        "sizes": (640, 260),
        "stretch": (5, 2),
        "minimums": (220, 140),
    },
}


BUTTON_ROLES = {"primary", "secondary", "danger", "nextStep", "amber"}


def get_density_profile(density: str = "comfortable") -> DensityProfile:
    return DENSITY_PROFILES.get(density, DENSITY_PROFILES["comfortable"])


def density_for_width(width: int) -> str:
    width = max(1, int(width))
    if width < 1180:
        return "compact"
    if width > 1680:
        return "spacious"
    return "comfortable"


def stylesheet_tokens(density: str = "comfortable") -> dict[str, str]:
    profile = get_density_profile(density)
    tokens = {
        "BASE_FONT": str(profile.base_font),
        "BANNER_TITLE": str(profile.banner_title),
        "BUTTON_MIN": str(profile.button_min),
        "NEXT_MIN": str(profile.next_min),
        "INPUT_MIN": str(profile.input_min),
        "MAIN_TAB_MIN": str(profile.main_tab_min),
        "WORKFLOW_TAB_MIN": str(profile.workflow_tab_min),
        "SCROLLBAR": str(profile.scrollbar),
    }
    tokens.update({f"COLOR_{name.upper()}": value for name, value in THEME_COLORS.items()})
    return tokens


def splitter_args(name: str) -> dict[str, list[int]]:
    preset = SPLITTER_PRESETS[name]
    return {key: [int(value) for value in values] for key, values in preset.items()}


def set_box_layout_format(layout: QBoxLayout, *, role: str = "panel", density: str = "comfortable") -> None:
    profile = get_density_profile(density)
    if role == "page":
        layout.setContentsMargins(*profile.page_margin)
        layout.setSpacing(profile.page_spacing)
    elif role == "sectionBody":
        layout.setContentsMargins(*profile.section_body_margin)
        layout.setSpacing(profile.section_spacing)
    elif role == "stack":
        layout.setContentsMargins(*profile.stack_margin)
        layout.setSpacing(profile.stack_spacing)
    elif role == "zero":
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
    else:
        layout.setContentsMargins(*profile.panel_margin)
        layout.setSpacing(profile.panel_spacing)


def standardize_form_layout(form: QFormLayout, *, density: str = "comfortable") -> QFormLayout:
    profile = get_density_profile(density)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.setFormAlignment(Qt.AlignTop)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    form.setHorizontalSpacing(profile.form_h_spacing)
    form.setVerticalSpacing(profile.form_v_spacing)
    return form


def apply_splitter_format(splitter: QSplitter, *, density: str = "comfortable") -> None:
    splitter.setProperty("role", "pageSplitter")
    splitter.setHandleWidth(get_density_profile(density).splitter_handle_width)
    splitter.setOpaqueResize(True)
    splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


def panel_content_min_width(panel_id: str = "", *, density: str = "comfortable") -> int:
    """Return the width at which content should start horizontal scrolling.

    Splitter panels themselves are allowed to become narrower than this so the
    user can drag proportions freely. The content inside the panel keeps this
    readable soft width and is exposed through a horizontal scrollbar only when
    the visible panel is smaller.
    """
    profile = get_density_profile(density)
    return profile.workflow_min_width if panel_id == "workflow_controls" else profile.panel_min_width


def apply_panel_frame_format(frame: QFrame, *, panel_id: str = "", density: str = "comfortable") -> None:
    profile = get_density_profile(density)
    frame.setProperty("role", "splitterPanel")
    frame.setFrameShape(QFrame.StyledPanel)
    frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    # Keep the frame itself easy to reduce with the splitter. The child content
    # keeps its readable minimum inside a scroll area, so reducing a panel below
    # its content width produces a horizontal scrollbar instead of clipping text.
    frame.setMinimumWidth(
        profile.workflow_frame_min_width if panel_id == "workflow_controls" else profile.panel_frame_min_width
    )


def apply_layout_tree_format(root: QWidget, *, density: str = "comfortable") -> None:
    """Apply standard spacing to layouts whose container has a known format role."""
    widgets = [root, *root.findChildren(QWidget)]
    for widget in widgets:
        layout = widget.layout()
        if layout is None:
            continue
        role = str(widget.property("role") or "")
        name = widget.objectName()
        if isinstance(layout, QFormLayout):
            standardize_form_layout(layout, density=density)
        elif isinstance(layout, QBoxLayout):
            if role == "pageShell":
                set_box_layout_format(layout, role="page", density=density)
            elif role == "splitterPanel" or role == "formGroup":
                set_box_layout_format(layout, role="panel", density=density)
            elif name == "controlStack":
                set_box_layout_format(layout, role="stack", density=density)
            elif name == "collapsibleSectionBody":
                set_box_layout_format(layout, role="sectionBody", density=density)


def apply_standard_widget_format(root: QWidget, *, density: str = "comfortable") -> None:
    """Apply uniform presentation roles to the whole programme widget tree.

    This keeps the final appearance controlled by this file + styles.py, not by
    one-off page/panel tweaks. Existing explicit roles such as nextStep, primary,
    secondary, and danger are preserved.
    """
    # Top-level and nested tabs.
    for tab in root.findChildren(QTabWidget):
        if not tab.property("role"):
            tab.setProperty("role", "contentTabs")
        tab.setUsesScrollButtons(True)
        tab.setElideMode(Qt.ElideRight)

    # Generic grouped panels.
    for group in root.findChildren(QGroupBox):
        if not group.property("role"):
            group.setProperty("role", "formGroup")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    # Make ordinary buttons uniform unless a panel intentionally marked them.
    for button in root.findChildren(QPushButton):
        role = button.property("role")
        if not role:
            button.setProperty("role", "secondary")
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if button.property("role") == "nextStep":
            button.setMinimumHeight(get_density_profile(density).next_min)

    # Every scrollable widget should reveal overflow when a splitter panel is
    # squeezed below the content's soft readable width. Scroll bars stay hidden
    # until they are actually needed.
    for scroll_area in root.findChildren(QAbstractScrollArea):
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    # Consistent readable tables and lists.
    for table in root.findChildren(QTableWidget):
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.verticalHeader().setVisible(False)

    for list_widget in root.findChildren(QListWidget):
        list_widget.setAlternatingRowColors(True)
        list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # Standard label roles. Do not overwrite explicit labels.
    for label in root.findChildren(QLabel):
        if label.objectName() in {"splitterPanelTitle", "pageBannerTitle", "pageBannerSummary", "pageBannerNext"}:
            continue
        if label.property("role") in {"muted", "hint", "intro", "statValue", "summaryLine", "summaryBlock", "panelSubtitle"}:
            continue
        if label.wordWrap():
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    apply_layout_tree_format(root, density=density)
