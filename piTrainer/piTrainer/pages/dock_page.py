from __future__ import annotations

from collections.abc import Iterable, Sequence

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..ui.formatting import (
    FORMAT_VERSION,
    apply_panel_frame_format,
    apply_splitter_format,
    set_box_layout_format,
)
from ..ui.layout_widgets import CollapsibleSection, make_panel_content_scroll


class ResponsiveSplitter(QSplitter):
    """QSplitter that preserves user proportions while adapting to window size.

    Qt splitters already resize their children, but large minimum sizes can make
    panels feel clipped on smaller windows. This helper stores the current panel
    ratios, reapplies them after resize, and uses soft minimum pixel lengths so
    every visible section keeps a reasonable share of the available space.
    """

    def __init__(
        self,
        orientation: Qt.Orientation,
        *,
        ratios: Sequence[float] | None = None,
        minimum_lengths: Sequence[int] | None = None,
    ) -> None:
        super().__init__(orientation)
        self._ratios = self._normalise_ratios(ratios or [])
        self._minimum_lengths = [max(0, int(value)) for value in (minimum_lengths or [])]
        self._applying_sizes = False
        self.splitterMoved.connect(self.capture_current_ratios)

    @staticmethod
    def _normalise_ratios(values: Sequence[float]) -> list[float]:
        cleaned = [max(0.01, float(value)) for value in values if float(value) > 0]
        total = sum(cleaned)
        if total <= 0:
            return []
        return [value / total for value in cleaned]

    def set_responsive_defaults(
        self,
        *,
        ratios: Sequence[float] | None = None,
        minimum_lengths: Sequence[int] | None = None,
    ) -> None:
        if ratios:
            self._ratios = self._normalise_ratios(ratios)
        if minimum_lengths is not None:
            self._minimum_lengths = [max(0, int(value)) for value in minimum_lengths]
        QTimer.singleShot(0, self.apply_responsive_sizes)

    def restoreState(self, state) -> bool:  # noqa: N802 - Qt API name
        ok = super().restoreState(state)
        QTimer.singleShot(0, self.capture_current_ratios)
        return ok

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        if not self._applying_sizes:
            QTimer.singleShot(0, self.apply_responsive_sizes)

    def _available_length(self) -> int:
        length = self.width() if self.orientation() == Qt.Horizontal else self.height()
        handles = max(0, self.count() - 1) * self.handleWidth()
        return max(0, int(length) - int(handles))

    def _ratios_for_count(self) -> list[float]:
        count = self.count()
        if count <= 0:
            return []
        if len(self._ratios) == count:
            return list(self._ratios)
        if not self._ratios:
            return [1.0 / count] * count
        padded = list(self._ratios[:count])
        while len(padded) < count:
            padded.append(padded[-1] if padded else 1.0)
        return self._normalise_ratios(padded)

    def _minimums_for_count(self) -> list[int]:
        count = self.count()
        defaults = [220] * count if self.orientation() == Qt.Horizontal else [120] * count
        values = list(self._minimum_lengths[:count])
        while len(values) < count:
            values.append(defaults[len(values)] if len(values) < len(defaults) else defaults[-1])
        return values

    def capture_current_ratios(self, *_args) -> None:
        if self._applying_sizes or self.count() <= 0:
            return
        sizes = [max(0, int(value)) for value in self.sizes()]
        total = sum(sizes)
        if total > 0:
            self._ratios = [size / total for size in sizes]

    def apply_responsive_sizes(self) -> None:
        count = self.count()
        total = self._available_length()
        if count <= 0 or total <= 0:
            return
        ratios = self._ratios_for_count()
        minimums = self._minimums_for_count()
        min_sum = sum(minimums)
        if min_sum >= total:
            # When the window is narrow/short, distribute the available pixels by
            # the soft minimums instead of letting one pane collapse to zero.
            weights = self._normalise_ratios(minimums) or ratios
            sizes = [max(40, int(round(total * weight))) for weight in weights]
        else:
            free = total - min_sum
            sizes = [minimums[i] + int(round(free * ratios[i])) for i in range(count)]
        delta = total - sum(sizes)
        if sizes:
            sizes[-1] = max(40, sizes[-1] + delta)
        self._applying_sizes = True
        try:
            self.setSizes(sizes)
        finally:
            self._applying_sizes = False


class DockPage(QMainWindow):
    layout_version = FORMAT_VERSION

    def __init__(self, page_id: str) -> None:
        super().__init__()
        self.page_id = page_id
        self.setObjectName(f"dock_page_{page_id}")
        self._splitters: list[QSplitter] = []
        self.setDockOptions(
            QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
            | QMainWindow.GroupedDragging
        )
        filler = QFrame()
        filler.setObjectName("dockPageFiller")
        filler.setFrameShape(QFrame.NoFrame)
        self.setCentralWidget(filler)

    def set_workspace_widget(
        self,
        widget: QWidget,
        *,
        step: str = '',
        title: str = '',
        summary: str = '',
        next_step: str = '',
        next_callback=None,
        next_tooltip: str = '',
    ) -> None:
        """Set the page's central workspace without the old page banner.

        The page-level top banner is intentionally disabled for now so each
        workflow opens directly into the splitter workspace. The unused banner
        arguments stay in the method signature for page compatibility and for a
        future easy restore if the banner is wanted again.
        """
        _ = (step, title, summary, next_step, next_callback, next_tooltip)
        widget.setObjectName(f"{self.page_id}_workspace_widget")
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(widget)

    def clear_docks(self) -> None:
        self._splitters = []
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()

    def add_panel(self, panel_id: str, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        """Backward-compatible dock helper kept for older/experimental pages."""
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{self.page_id}_{panel_id}_dock")
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(area, dock)
        return dock

    def make_panel_frame(self, panel_id: str, title: str, widget: QWidget, subtitle: str = '') -> QFrame:
        """Wrap a content widget in a titled frame for splitter workspaces."""
        frame = QFrame()
        frame.setObjectName(f"{self.page_id}_{panel_id}_panel")
        apply_panel_frame_format(frame, panel_id=panel_id)

        header = QLabel(title)
        header.setObjectName("splitterPanelTitle")
        header.setProperty("role", "panelTitle")
        header.setWordWrap(False)

        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_scroll = make_panel_content_scroll(
            widget,
            panel_id=panel_id,
            object_name=f"{self.page_id}_{panel_id}_content_scroll",
        )

        layout = QVBoxLayout(frame)
        set_box_layout_format(layout, role="panel")
        layout.addWidget(header)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("splitterPanelSubtitle")
            subtitle_label.setProperty("role", "panelSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        layout.addWidget(content_scroll, 1)
        return frame

    def make_splitter(
        self,
        orientation: Qt.Orientation,
        widgets: Sequence[QWidget],
        *,
        sizes: Sequence[int] | None = None,
        object_name: str,
        stretch: Sequence[int] | None = None,
        minimums: Sequence[int] | None = None,
        children_collapsible: bool = False,
    ) -> QSplitter:
        default_ratios = None
        if sizes:
            total_size = sum(max(1, int(size)) for size in sizes)
            default_ratios = [max(1, int(size)) / total_size for size in sizes]
        splitter = ResponsiveSplitter(orientation, ratios=default_ratios, minimum_lengths=minimums)
        splitter.setObjectName(f"{self.page_id}_{object_name}_splitter")
        apply_splitter_format(splitter)
        splitter.setChildrenCollapsible(children_collapsible)
        for index, widget in enumerate(widgets):
            splitter.addWidget(widget)
            if stretch and index < len(stretch):
                splitter.setStretchFactor(index, int(stretch[index]))
            else:
                splitter.setStretchFactor(index, 1)
        if sizes:
            splitter.setSizes([int(size) for size in sizes])
            splitter.set_responsive_defaults(ratios=default_ratios, minimum_lengths=minimums)
        self._splitters.append(splitter)
        return splitter

    def make_horizontal_splitter(
        self,
        widgets: Sequence[QWidget],
        *,
        sizes: Sequence[int] | None = None,
        object_name: str,
        stretch: Sequence[int] | None = None,
        minimums: Sequence[int] | None = None,
    ) -> QSplitter:
        return self.make_splitter(
            Qt.Horizontal,
            widgets,
            sizes=sizes,
            object_name=object_name,
            stretch=stretch,
            minimums=minimums,
        )

    def make_vertical_splitter(
        self,
        widgets: Sequence[QWidget],
        *,
        sizes: Sequence[int] | None = None,
        object_name: str,
        stretch: Sequence[int] | None = None,
        minimums: Sequence[int] | None = None,
    ) -> QSplitter:
        return self.make_splitter(
            Qt.Vertical,
            widgets,
            sizes=sizes,
            object_name=object_name,
            stretch=stretch,
            minimums=minimums,
        )

    def reveal_widget(self, widget: QWidget | None, *, message: str = '') -> None:
        """Bring a nested action widget into view without triggering it.

        Used by the compact page banner: pressing the banner button opens the
        correct workflow tab/section, scrolls to the real green action button,
        and briefly highlights it so the user knows which control to click.
        """
        if widget is None:
            return
        self._activate_tab_ancestors(widget)
        self._expand_section_ancestors(widget)
        widget.show()
        widget.setFocus(Qt.OtherFocusReason)
        self._ensure_widget_visible(widget)
        self._spotlight_widget(widget)
        if message and hasattr(self, 'main_window'):
            self.main_window.set_status_message(message)

    def _activate_tab_ancestors(self, widget: QWidget) -> None:
        current = widget.parentWidget()
        while current is not None:
            parent = current.parentWidget()
            if isinstance(parent, QTabWidget):
                index = parent.indexOf(current)
                if index >= 0:
                    parent.setCurrentIndex(index)
            current = parent

    def _expand_section_ancestors(self, widget: QWidget) -> None:
        current = widget.parentWidget()
        while current is not None:
            if isinstance(current, CollapsibleSection):
                current.set_expanded(True)
            current = current.parentWidget()

    def _ensure_widget_visible(self, widget: QWidget) -> None:
        for scroll_area in self.findChildren(QScrollArea):
            content = scroll_area.widget()
            if content is not None and (content is widget or content.isAncestorOf(widget)):
                scroll_area.ensureWidgetVisible(widget, 24, 24)

    def _spotlight_widget(self, widget: QWidget) -> None:
        widget.setProperty('spotlight', True)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

        def clear_spotlight() -> None:
            widget.setProperty('spotlight', False)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

        QTimer.singleShot(2600, clear_spotlight)

    def _layout_key(self, name: str) -> str:
        return f"{self.page_id}/{self.layout_version}/{name}"

    def save_layout(self) -> None:
        settings = QSettings("OpenAI", "PiTrainer")
        settings.setValue(self._layout_key("geometry"), self.saveGeometry())
        settings.setValue(self._layout_key("state"), self.saveState())
        for splitter in self._splitters:
            settings.setValue(self._layout_key(splitter.objectName()), splitter.saveState())

    def restore_layout(self) -> None:
        settings = QSettings("OpenAI", "PiTrainer")
        geometry = settings.value(self._layout_key("geometry"))
        state = settings.value(self._layout_key("state"))
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)
        for splitter in self._splitters:
            splitter_state = settings.value(self._layout_key(splitter.objectName()))
            if splitter_state is not None:
                splitter.restoreState(splitter_state)

    def reset_layout(self) -> None:
        settings = QSettings("OpenAI", "PiTrainer")
        settings.remove(f"{self.page_id}/{self.layout_version}")
        self.build_default_layout()

    def build_default_layout(self) -> None:
        raise NotImplementedError
