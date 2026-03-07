from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.validation.validation_actions_panel import ValidationActionsPanel
from ..panels.validation.validation_config_panel import ValidationConfigPanel
from ..panels.validation.validation_plot_panel import ValidationPlotPanel
from ..panels.validation.validation_summary_panel import ValidationSummaryPanel
from ..services.validation.validation_service import (
    build_validation_summary_text,
    run_validation,
)
from .dock_page import DockPage


class ValidationPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.last_result: dict | None = None
        super().__init__('validation')

        self.summary_panel = ValidationSummaryPanel()
        self.config_panel = ValidationConfigPanel(self.state)
        self.actions_panel = ValidationActionsPanel(
            browse_model_callback=self.browse_model,
            validate_callback=self.validate_model,
            clear_callback=self.clear_results,
        )
        self.plot_panel = ValidationPlotPanel()
        self.log_panel = LogPanel('Validation Log')

        self.build_default_layout()
        self.restore_layout()
        self.refresh_from_state()

    def build_default_layout(self) -> None:
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()

        summary_dock = self.add_panel('summary', 'Validation Summary', self.summary_panel, Qt.LeftDockWidgetArea)
        config_dock = self.add_panel('config', 'Validation Config', self.config_panel, Qt.LeftDockWidgetArea)
        actions_dock = self.add_panel('actions', 'Validation Actions', self.actions_panel, Qt.LeftDockWidgetArea)
        plot_dock = self.add_panel('plot', 'Validation Plot', self.plot_panel, Qt.RightDockWidgetArea)
        log_dock = self.add_panel('log', 'Validation Log', self.log_panel, Qt.RightDockWidgetArea)

        self.splitDockWidget(summary_dock, config_dock, Qt.Vertical)
        self.splitDockWidget(config_dock, actions_dock, Qt.Vertical)
        self.splitDockWidget(summary_dock, plot_dock, Qt.Horizontal)
        self.splitDockWidget(plot_dock, log_dock, Qt.Vertical)

        self.resizeDocks([summary_dock, config_dock, actions_dock], [180, 260, 150], Qt.Vertical)
        self.resizeDocks([plot_dock, log_dock], [480, 210], Qt.Vertical)
        self.resizeDocks([summary_dock, plot_dock], [320, 720], Qt.Horizontal)

    def refresh_from_state(self) -> None:
        self.summary_panel.set_model_state(
            in_memory_ready=self.state.model is not None,
            current_model_path=self.config_panel.model_path(),
            dataset_rows={
                'validation': len(self.state.val_df),
                'filtered': len(self.state.filtered_df),
                'training': len(self.state.train_df),
            },
        )
        if self.last_result:
            self.summary_panel.set_result_text(build_validation_summary_text(self.last_result))
            self.plot_panel.set_result(self.last_result)
        else:
            self.summary_panel.set_result_text('No validation run yet. Choose a model source and click Run Validation.')
            self.plot_panel.set_result(None)

    def browse_model(self) -> None:
        self.config_panel.browse_model_file(self)
        self.refresh_from_state()

    def _selected_dataset(self) -> pd.DataFrame:
        dataset_name = self.config_panel.dataset_source()
        if dataset_name == 'Validation split':
            return self.state.val_df.copy()
        if dataset_name == 'Training split':
            return self.state.train_df.copy()
        return self.state.filtered_df.copy()

    def validate_model(self) -> None:
        dataset_df = self._selected_dataset()
        if dataset_df.empty:
            message = 'No rows available for the selected validation dataset.'
            self.log_panel.append_line(message)
            self.main_window.set_status_message(message)
            return

        self.config_panel.push_to_state()
        self.log_panel.append_line(
            f"Running validation on {len(dataset_df)} row(s) using {self.config_panel.model_source()}..."
        )
        try:
            result = run_validation(
                dataset_df=dataset_df,
                train_config=self.state.train_config,
                in_memory_model=self.state.model,
                model_source=self.config_panel.model_source(),
                model_path=self.config_panel.model_path(),
                batch_size=self.config_panel.batch_size(),
                max_rows=self.config_panel.max_rows(),
            )
        except Exception as exc:
            message = f'Validation failed: {exc}'
            self.log_panel.append_line(message)
            self.main_window.set_status_message('Validation failed.')
            return

        self.last_result = result
        self.summary_panel.set_result_text(build_validation_summary_text(result))
        self.plot_panel.set_result(result)
        self.log_panel.append_line(
            'Validation complete: '
            f"rows={result['rows_used']}, steering_mae={result['steering_mae']:.4f}, speed_mae={result['throttle_mae']:.4f}"
        )
        self.main_window.set_status_message('Validation complete.')
        self.refresh_from_state()

    def clear_results(self) -> None:
        self.last_result = None
        self.plot_panel.set_result(None)
        self.summary_panel.set_result_text('Validation results cleared.')
        self.log_panel.clear()
        self.main_window.set_status_message('Validation results cleared.')
