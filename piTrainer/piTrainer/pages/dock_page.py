from __future__ import annotations

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QLabel, QDockWidget, QMainWindow, QWidget


class DockPage(QMainWindow):
    def __init__(self, page_id: str, title: str) -> None:
        super().__init__()
        self.page_id = page_id
        self.setObjectName(f"dock_page_{page_id}")
        self.setDockOptions(
            QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
            | QMainWindow.GroupedDragging
        )
        placeholder = QLabel(title)
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setObjectName('dockPagePlaceholder')
        self.setCentralWidget(placeholder)
        self._dock_widgets: list[QDockWidget] = []

    def add_panel(self, panel_id: str, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{self.page_id}_{panel_id}_dock")
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(area, dock)
        self._dock_widgets.append(dock)
        return dock

    def save_layout(self) -> None:
        settings = QSettings('OpenAI', 'PiTrainer')
        settings.setValue(f'{self.page_id}/geometry', self.saveGeometry())
        settings.setValue(f'{self.page_id}/state', self.saveState())

    def restore_layout(self) -> None:
        settings = QSettings('OpenAI', 'PiTrainer')
        geometry = settings.value(f'{self.page_id}/geometry')
        state = settings.value(f'{self.page_id}/state')
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)

    def reset_layout(self) -> None:
        settings = QSettings('OpenAI', 'PiTrainer')
        settings.remove(f'{self.page_id}/geometry')
        settings.remove(f'{self.page_id}/state')
        self.build_default_layout()

    def build_default_layout(self) -> None:
        raise NotImplementedError
