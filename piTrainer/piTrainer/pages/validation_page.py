from __future__ import annotations

from ..services.task_outputs import confirmed_receipt_paths

from ..app_state import TrainConfig
import pandas as pd

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.common.task_progress_panel import TaskProgressPanel
from ..services.background_task import BackgroundTaskRunner
from ..panels.validation.validation_actions_panel import ValidationActionsPanel
from ..panels.validation.validation_config_panel import ValidationConfigPanel
from ..panels.validation.validation_frame_review_panel import ValidationFrameReviewPanel
from ..panels.validation.validation_plot_panel import ValidationPlotPanel
from ..panels.validation.validation_summary_panel import ValidationSummaryPanel
from ..services.data.visibility_service import without_hidden_rows
from ..services.validation.validation_provenance import in_memory_context, file_context, stable_file_context
from ..services.validation.validation_receipts import save_validation_receipt
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
        self.task_progress = TaskProgressPanel()
        self.actions_panel.layout().addWidget(self.task_progress)
        self.task_runner = BackgroundTaskRunner(self.task_progress, self)
        self.config_panel.dataset_source_combo.currentTextChanged.connect(self.refresh_selected_scope)
        self.config_panel.max_rows_spin.valueChanged.connect(self.refresh_selected_scope)

        self.build_default_layout()
        self.restore_layout()
        self.refresh_from_state()

    def build_default_layout(self) -> None:
        self.clear_docks()

        workflow_tabs = make_workflow_tabs([
            (
                '1 Run',
                make_scrollable_stack([
                    ('Actions', self.actions_panel, True),
                    ('Settings', self.config_panel, True),
                ], object_name='validationRunWorkflowScrollArea', intro='Choose model source and dataset, then run validation.'),
            ),
            (
                '2 Summary',
                make_scrollable_stack([
                    ('Summary', self.summary_panel, True),
                ], object_name='validationStatusWorkflowScrollArea', intro='Review errors and metrics after validation.'),
            ),
        ], object_name='validationWorkflowTabs')

        result_tabs = make_workflow_tabs([
            ('1 Plot', self.plot_panel, 'Prediction error plot.'),
            ('2 Log', self.log_panel, 'Messages and errors.'),
        ], object_name='validationResultTabs')

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'Validate Workflow', workflow_tabs),
            self.make_panel_frame('results', 'Validate Output', result_tabs),
            self.make_panel_frame('frame_review', 'Frame Review', self.frame_review_panel),
        ], object_name='main_workspace', **splitter_args('validation_three_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='4 of 6',
            title='Validate',
            summary='Run validation, inspect frames, and send bad labels back to Data if needed.',
            next_step='Run Validation',
            next_callback=lambda: self.reveal_widget(
                self.actions_panel.run_button,
                message='Focused the green Run Validation button.'
            ),
            next_tooltip='Focus Run Validation in 1 Run.',
        )

    def refresh_selected_scope(self, *_args) -> None:
        source = self.config_panel.dataset_source()
        if source == 'Validation split':
            frame = self.state.val_df
        elif source == 'Training split':
            frame = self.state.train_df
        else:
            frame = self.state.filtered_df
        self.summary_panel.set_selected_scope(source, len(frame), self.config_panel.max_rows())

    def refresh_from_state(self) -> None:
        self.refresh_selected_scope()
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
            self.summary_panel.set_result_text('No validation yet. Choose a model source and run validation.')
            self.plot_panel.set_result(None)
            self.frame_review_panel.set_result(None)

    def browse_model(self) -> None:
        self.config_panel.browse_model_file(self)
        self.refresh_from_state()

    def _selected_dataset(self) -> pd.DataFrame:
        dataset_name = self.config_panel.dataset_source()
        if dataset_name == 'Validation split':
            return without_hidden_rows(self.state.val_df)
        if dataset_name == 'Training split':
            return without_hidden_rows(self.state.train_df)
        return without_hidden_rows(self.state.filtered_df)

    def validate_model(self) -> None:
        if not self.main_window.can_start_task(self):
            return
        if self.task_runner.active:
            return
        dataset_df = self._selected_dataset()
        if dataset_df.empty:
            message = 'No rows available for the selected validation dataset.'
            self.log_panel.append_line(message)
            self.main_window.set_status_message(message)
            return

        self.config_panel.push_to_state()
        source = self.config_panel.model_source()
        # A remembered file path must not be attributed to the in-memory model.
        model_path = self.config_panel.model_path() if source != 'Current trained model' else ''
        in_memory_model = self.state.model
        train_page = getattr(self.main_window, 'train_page', None)
        tracked = (train_page.provenance_for_model(in_memory_model)
                   if source == 'Current trained model' and train_page is not None else None)
        memory_context = in_memory_context(tracked[0] if tracked else None)
        dataset_source = self.config_panel.dataset_source()
        train_config = TrainConfig(**vars(self.state.train_config))
        batch_size = self.config_panel.batch_size()
        max_rows = self.config_panel.max_rows()
        snapshot = dataset_df.copy(deep=True)
        receipt_root = self.state.out_dir_path
        self.log_panel.append_line(f'Running validation on {len(snapshot)} row(s) using {source}...')

        def work(report):
            report('Loading model and checking predictions', None)
            before = memory_context if source == 'Current trained model' else file_context(model_path)
            result = run_validation(
                dataset_df=snapshot, train_config=train_config,
                in_memory_model=in_memory_model, model_source=source,
                model_path=model_path, batch_size=batch_size, max_rows=max_rows,
            )
            result['experiment_context'] = (before if source == 'Current trained model'
                                            else stable_file_context(before, file_context(model_path)))
            result['dataset_source'] = dataset_source
            try:
                receipt, path = save_validation_receipt(receipt_root, result)
                result['validation_receipt'] = {'id': receipt['validation_id'], 'path': str(path),
                                                'rows_sha256': receipt['evaluated_rows_sha256']}
            except (OSError, ValueError, TypeError) as exc:
                result['validation_receipt_error'] = str(exc)
            return result

        def completed(result):
            self.last_result = result
            receipt = result.get('validation_receipt')
            if receipt:
                self.log_panel.append_line(f"Validation summary saved: {receipt['path']}")
            elif result.get('validation_receipt_error'):
                self.log_panel.append_line(f"WARNING: Validation completed but summary could not be saved: {result['validation_receipt_error']}")
            self.summary_panel.set_result_text(build_validation_summary_text(result))
            self.plot_panel.set_result(result)
            self.frame_review_panel.set_result(result)
            self.log_panel.append_line(
                'Validation complete: '
                f"rows={result['rows_used']}, steering_mae={result['steering_mae']:.4f}, speed_mae={result['throttle_mae']:.4f}"
            )
            self.main_window.set_status_message('Validation complete.')
            self.refresh_from_state()
            return (f"Validation completed: {result['rows_used']} rows",
                    confirmed_receipt_paths((receipt or {}).get("path")))

        def failed(error):
            self.log_panel.append_line(f'Validation failed: {error}')
            self.main_window.set_status_message('Validation failed.')

        self.task_runner.start(
            'Model validation', work, completed, on_failure=failed,
            controls=(self.actions_panel.run_button, self.actions_panel.clear_button, self.actions_panel.browse_button, self.config_panel),
        )

    def has_active_task(self) -> bool:
        return self.task_runner.active

    def clear_results(self) -> None:
        self.last_result = None
        self.plot_panel.set_result(None)
        self.frame_review_panel.set_result(None)
        self.summary_panel.set_result_text('Validation results cleared.')
        self.log_panel.clear()
        self.main_window.set_status_message('Validation results cleared.')
