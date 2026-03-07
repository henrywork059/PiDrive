from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.export.export_actions_panel import ExportActionsPanel
from ..panels.export.export_options_panel import ExportOptionsPanel
from ..panels.export.model_status_panel import ModelStatusPanel
from ..services.export.export_service import export_model_artifacts
from .dock_page import DockPage


class ExportPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        super().__init__('export')

        self.model_status_panel = ModelStatusPanel()
        self.options_panel = ExportOptionsPanel(self.state)
        self.actions_panel = ExportActionsPanel(self.export_model)
        self.log_panel = LogPanel('Export Log')
        self.build_default_layout()
        self.restore_layout()

    def build_default_layout(self) -> None:
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()
        status_dock = self.add_panel('status', 'Model Status', self.model_status_panel, Qt.LeftDockWidgetArea)
        options_dock = self.add_panel('options', 'Export Options', self.options_panel, Qt.LeftDockWidgetArea)
        actions_dock = self.add_panel('actions', 'Export Actions', self.actions_panel, Qt.LeftDockWidgetArea)
        log_dock = self.add_panel('log', 'Export Log', self.log_panel, Qt.RightDockWidgetArea)
        self.splitDockWidget(status_dock, options_dock, Qt.Vertical)
        self.splitDockWidget(options_dock, actions_dock, Qt.Vertical)
        self.splitDockWidget(status_dock, log_dock, Qt.Horizontal)
        self.resizeDocks([status_dock, options_dock, actions_dock], [150, 260, 150], Qt.Vertical)
        self.resizeDocks([status_dock, log_dock], [280, 620], Qt.Horizontal)

    def refresh_from_state(self) -> None:
        model_ready = self.state.model is not None
        history_len = len(self.state.history.get('loss', [])) if self.state.history else 0
        self.model_status_panel.set_status(
            model_ready=model_ready,
            train_rows=len(self.state.train_df),
            val_rows=len(self.state.val_df),
            epochs_ran=history_len,
        )

    def export_model(self) -> None:
        self.options_panel.push_to_state()
        if self.state.model is None:
            self.log_panel.append_line('No trained model available. Train a model first.')
            return
        try:
            created = export_model_artifacts(
                model=self.state.model,
                export_config=self.state.export_config,
                train_df=self.state.train_df,
                train_config=self.state.train_config,
            )
        except Exception as exc:
            self.log_panel.append_line(f'ERROR: {exc}')
            self.main_window.set_status_message('Export failed.')
            return

        for item in created:
            self.log_panel.append_line(f'Created: {item}')
        self.main_window.set_status_message('Export finished.')
