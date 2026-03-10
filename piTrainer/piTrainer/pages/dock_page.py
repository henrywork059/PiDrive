from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDockWidget, QFrame, QMainWindow, QWidget


class DockPage(QMainWindow):
    def __init__(self, page_id: str) -> None:
        super().__init__()
        self.page_id = page_id
        self.setObjectName(f"dock_page_{page_id}")
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

    def set_workspace_widget(self, widget: QWidget) -> None:
        """Backward-compatible helper for older pages.

        Newer pages should prefer making the main content a dock panel rather than
        replacing the central filler widget.
        """
        widget.setObjectName(f"{self.page_id}_workspace_widget")
        self.setCentralWidget(widget)


    def clear_docks(self) -> None:
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()

    def add_panel(self, panel_id: str, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
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

    def save_layout(self) -> None:
        settings = QSettings("OpenAI", "PiTrainer")
        settings.setValue(f"{self.page_id}/geometry", self.saveGeometry())
        settings.setValue(f"{self.page_id}/state", self.saveState())

    def restore_layout(self) -> None:
        settings = QSettings("OpenAI", "PiTrainer")
        geometry = settings.value(f"{self.page_id}/geometry")
        state = settings.value(f"{self.page_id}/state")
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)

    def reset_layout(self) -> None:
        settings = QSettings("OpenAI", "PiTrainer")
        settings.remove(f"{self.page_id}/geometry")
        settings.remove(f"{self.page_id}/state")
        self.build_default_layout()

    def build_default_layout(self) -> None:
        raise NotImplementedError
