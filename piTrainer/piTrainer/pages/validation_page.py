from __future__ import annotations

import pandas as pd

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.validation.validation_actions_panel import ValidationActionsPanel
from ..panels.validation.validation_config_panel import ValidationConfigPanel
from ..panels.validation.validation_frame_review_panel import ValidationFrameReviewPanel
from ..panels.validation.validation_plot_panel import ValidationPlotPanel
from ..panels.validation.validation_summary_panel import ValidationSummaryPanel
from ..services.validation.validation_service import build_validation_summary_text, run_validation
from .dock_page import DockPage
from ..ui.formatting import splitter_args
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs


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
        self.frame_review_panel = ValidationFrameReviewPanel(edit_in_data_callback=self.main_window.open_validation_frame_in_data_editor)
        self.log_panel = LogPanel('Validation Log')

        self.build_default_layout()
        self.restore_layout()
        self.refresh_from_state()

    def build_default_layout(self) -> None:
        self.clear_docks()

        workflow_tabs = make_workflow_tabs([
            (
                '1 Run',
                make_scrollable_stack([
                    ('Validation Actions', self.actions_panel, True),
                    ('Validation Config', self.config_panel, True),
                ], object_name='validationRunWorkflowScrollArea', intro='Choose the model source and dataset, then run validation to inspect prediction error.'),
            ),
            (
                '2 Results',
                make_scrollable_stack([
                    ('Validation Summary', self.summary_panel, True),
                ], object_name='validationStatusWorkflowScrollArea', intro='Read the result summary here after validation finishes.'),
            ),
        ], object_name='validationWorkflowTabs')

        result_tabs = make_workflow_tabs([
            ('Plot', self.plot_panel, 'Validation error plot.'),
            ('Log', self.log_panel, 'Validation messages and errors.'),
        ], object_name='validationResultTabs')

        right_stack = self.make_vertical_splitter([
            self.make_panel_frame('frame_review', 'Validation Frame Review', self.frame_review_panel),
            self.make_panel_frame('results', 'Validation Plot / Log', result_tabs),
        ], object_name='right_stack', **splitter_args('preview_over_results'))

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'Validation Workflow', workflow_tabs),
            right_stack,
        ], object_name='main_workspace', **splitter_args('two_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='4 of 5',
            title='Validate',
            summary='Run the model on validation data, inspect frames, and send bad labels back to Data if needed.',
            next_step='Show: Run Validation',
            next_callback=lambda: self.reveal_widget(
                self.actions_panel.run_button,
                message='Showing the green Run Validation button.'
            ),
            next_tooltip='Click to show the green Run Validation button in Validation Workflow > Run > Validation Actions.',
        )

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
            self.frame_review_panel.set_result(self.last_result)
        else:
            self.summary_panel.set_result_text('No validation run yet. Choose a model source and click Run Validation.')
            self.plot_panel.set_result(None)
            self.frame_review_panel.set_result(None)

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
        self.frame_review_panel.set_result(result)
        self.log_panel.append_line(
            'Validation complete: '
            f"rows={result['rows_used']}, steering_mae={result['steering_mae']:.4f}, speed_mae={result['throttle_mae']:.4f}"
        )
        self.main_window.set_status_message('Validation complete.')
        self.refresh_from_state()

    def clear_results(self) -> None:
        self.last_result = None
        self.plot_panel.set_result(None)
        self.frame_review_panel.set_result(None)
        self.summary_panel.set_result_text('Validation results cleared.')
        self.log_panel.clear()
        self.main_window.set_status_message('Validation results cleared.')
