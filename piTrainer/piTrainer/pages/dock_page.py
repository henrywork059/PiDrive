from __future__ import annotations

from collections.abc import Iterable, Sequence

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..ui.layout_widgets import make_page_banner


class DockPage(QMainWindow):
    layout_version = "0_4_10_presentation_layout"

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
    ) -> None:
        """Set the page's central workspace with an optional workflow banner.

        The default pages use full-width splitter workspaces rather than nested
        docks. The banner adds quick orientation above the splitter so users can
        tell where they are, what to check, and what the recommended next action
        is without hunting through dense panels.
        """
        widget.setObjectName(f"{self.page_id}_workspace_widget")
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if title or summary or next_step:
            wrapper = QFrame()
            wrapper.setObjectName(f"{self.page_id}_page_shell")
            wrapper.setProperty("role", "pageShell")
            wrapper.setFrameShape(QFrame.NoFrame)
            wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(12, 10, 12, 12)
            layout.setSpacing(10)
            layout.addWidget(make_page_banner(step, title, summary, next_step), 0)
            layout.addWidget(widget, 1)
            self.setCentralWidget(wrapper)
        else:
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
        frame.setProperty("role", "splitterPanel")
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = QLabel(title)
        header.setObjectName("splitterPanelTitle")
        header.setProperty("role", "panelTitle")
        header.setWordWrap(False)

        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(header)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("splitterPanelSubtitle")
            subtitle_label.setProperty("role", "panelSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        layout.addWidget(widget, 1)
        if panel_id == 'workflow_controls':
            frame.setMinimumWidth(330)
            frame.setMaximumWidth(520)
        return frame

    def make_splitter(
        self,
        orientation: Qt.Orientation,
        widgets: Sequence[QWidget],
        *,
        sizes: Sequence[int] | None = None,
        object_name: str,
        stretch: Sequence[int] | None = None,
        children_collapsible: bool = False,
    ) -> QSplitter:
        splitter = QSplitter(orientation)
        splitter.setObjectName(f"{self.page_id}_{object_name}_splitter")
        splitter.setProperty("role", "pageSplitter")
        splitter.setChildrenCollapsible(children_collapsible)
        splitter.setHandleWidth(10)
        splitter.setOpaqueResize(True)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for index, widget in enumerate(widgets):
            splitter.addWidget(widget)
            if stretch and index < len(stretch):
                splitter.setStretchFactor(index, int(stretch[index]))
            else:
                splitter.setStretchFactor(index, 1)
        if sizes:
            splitter.setSizes([int(size) for size in sizes])
        self._splitters.append(splitter)
        return splitter

    def make_horizontal_splitter(
        self,
        widgets: Sequence[QWidget],
        *,
        sizes: Sequence[int] | None = None,
        object_name: str,
        stretch: Sequence[int] | None = None,
    ) -> QSplitter:
        return self.make_splitter(
            Qt.Horizontal,
            widgets,
            sizes=sizes,
            object_name=object_name,
            stretch=stretch,
        )

    def make_vertical_splitter(
        self,
        widgets: Sequence[QWidget],
        *,
        sizes: Sequence[int] | None = None,
        object_name: str,
        stretch: Sequence[int] | None = None,
    ) -> QSplitter:
        return self.make_splitter(
            Qt.Vertical,
            widgets,
            sizes=sizes,
            object_name=object_name,
            stretch=stretch,
        )

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
