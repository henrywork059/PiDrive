from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QDockWidget, QLabel, QMainWindow, QSizePolicy, QTabWidget, QVBoxLayout, QWidget

from custom_trainer.services.ui_state_service import get_layout_state, set_layout_state


class DockWorkspacePage(QWidget):
    """Reusable dock-enabled page shell for draggable, snappable, tabifiable panels."""

    def __init__(self, layout_key: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout_key = layout_key
        self._default_layout_builder: Callable[[], None] | None = None
        self.workspace = QMainWindow(self)
        self.workspace.setObjectName(f'{layout_key}_workspace')
        self.workspace.setDockNestingEnabled(True)
        self.workspace.setDockOptions(
            QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
            | QMainWindow.GroupedDragging
        )
        self.workspace.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        self.workspace.setDocumentMode(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.workspace, 1)

    def set_central_panel(self, widget: QWidget, *, title: str | None = None) -> None:
        if title:
            widget.setWindowTitle(title)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.workspace.setCentralWidget(widget)

    def set_placeholder_central(self, text: str) -> None:
        label = QLabel(text, self.workspace)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setProperty('role', 'muted')
        self.set_central_panel(label)

    def create_dock(
        self,
        object_name: str,
        title: str,
        widget: QWidget,
        *,
        area: Qt.DockWidgetArea = Qt.LeftDockWidgetArea,
        allowed_areas: Qt.DockWidgetAreas = Qt.AllDockWidgetAreas,
        floating: bool = False,
    ) -> QDockWidget:
        dock = QDockWidget(title, self.workspace)
        dock.setObjectName(object_name)
        dock.setAllowedAreas(allowed_areas)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock.setWidget(widget)
        dock.setFloating(floating)
        self.workspace.addDockWidget(area, dock)
        return dock

    def set_default_layout_builder(self, builder: Callable[[], None]) -> None:
        self._default_layout_builder = builder

    def restore_splitters(self) -> None:
        restored = False
        state = get_layout_state(self._layout_key)
        if state:
            try:
                restored = self.workspace.restoreState(QByteArray(state), 1)
            except Exception:
                restored = False
        if not restored and self._default_layout_builder is not None:
            self._default_layout_builder()

    def save_splitters(self) -> None:
        try:
            set_layout_state(self._layout_key, bytes(self.workspace.saveState(1)))
        except Exception:
            pass

    def reset_panel_layout(self) -> None:
        if self._default_layout_builder is not None:
            self._default_layout_builder()
        self.save_splitters()
