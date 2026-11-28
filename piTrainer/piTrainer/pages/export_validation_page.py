from __future__ import annotations

from ..services.task_outputs import confirmed_receipt_paths

from ..app_state import TrainConfig
import pandas as pd

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.common.task_progress_panel import TaskProgressPanel
from ..services.background_task import BackgroundTaskRunner
from ..panels.export_validation.export_validation_actions_panel import ExportValidationActionsPanel
from ..panels.export_validation.export_validation_config_panel import ExportValidationConfigPanel
from ..panels.export_validation.export_validation_summary_panel import ExportValidationSummaryPanel
from ..panels.validation.validation_frame_review_panel import ValidationFrameReviewPanel
from ..panels.validation.validation_plot_panel import ValidationPlotPanel
from ..services.data.visibility_service import without_hidden_rows
from ..services.validation.validation_provenance import file_context, stable_file_context
from ..services.validation.validation_receipts import save_validation_receipt
from ..services.validation.validation_service import build_validation_summary_text, run_tflite_validation
from ..ui.formatting import splitter_args
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs
from .dock_page import DockPage


class ExportValidationPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.last_result: dict | None = None
        super().__init__('export_validation')

        self.summary_panel = ExportValidationSummaryPanel()
        self.config_panel = ExportValidationConfigPanel(self.state)
        self.actions_panel = ExportValidationActionsPanel(
            browse_model_callback=self.browse_model,
            validate_callback=self.validate_export,
            clear_callback=self.clear_results,
        )
        self.plot_panel = ValidationPlotPanel()
        self.frame_review_panel = ValidationFrameReviewPanel(edit_in_data_callback=self.main_window.open_validation_frame_in_data_editor)
        self.log_panel = LogPanel('TFLite Check Log')
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
                ], object_name='exportValidationRunWorkflowScrollArea', intro='Choose the .tflite file and dataset, then run the check.'),
            ),
            (
                '2 Summary',
                make_scrollable_stack([
                    ('Summary', self.summary_panel, True),
                ], object_name='exportValidationStatusWorkflowScrollArea', intro='Review errors and output ranges.'),
            ),
        ], object_name='exportValidationWorkflowTabs')

        result_tabs = make_workflow_tabs([
            ('1 Plot', self.plot_panel, 'Prediction error plot.'),
            ('2 Log', self.log_panel, 'Interpreter messages and errors.'),
        ], object_name='exportValidationResultTabs')

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'TFLite Workflow', workflow_tabs),
            self.make_panel_frame('results', 'TFLite Output', result_tabs),
            self.make_panel_frame('frame_review', 'Frame Review', self.frame_review_panel),
        ], object_name='main_workspace', **splitter_args('validation_three_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='6 of 6',
            title='TFLite Check',
            summary='Check exported TFLite predictions before copying the model to the car.',
            next_step='Run Check',
            next_callback=lambda: self.reveal_widget(
                self.actions_panel.run_button,
                message='Focused the green Run Check button.'
            ),
            next_tooltip='Focus Run Check in 1 Run.',
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
            tflite_path=self.config_panel.tflite_path(),
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
            self.summary_panel.set_result_text('No TFLite check yet. Choose a .tflite model, then Run TFLite Check.')
            self.plot_panel.set_result(None)
            self.frame_review_panel.set_result(None)

    def browse_model(self) -> None:
        self.config_panel.browse_model_file(self)
        self.refresh_from_state()

    def set_exported_tflite_path(self, path: str) -> None:
        self.config_panel.set_tflite_path(path)
        self.refresh_from_state()

    def _selected_dataset(self) -> pd.DataFrame:
        dataset_name = self.config_panel.dataset_source()
        if dataset_name == 'Validation split':
            return without_hidden_rows(self.state.val_df)
        if dataset_name == 'Training split':
            return without_hidden_rows(self.state.train_df)
        return without_hidden_rows(self.state.filtered_df)

    def validate_export(self) -> None:
        if not self.main_window.can_start_task(self):
            return
        if self.task_runner.active:
            return
        dataset_df = self._selected_dataset()
        if dataset_df.empty:
            message = 'No rows in this dataset. Load sessions in Data, then choose a populated split.'
            self.log_panel.append_line(message)
            self.main_window.set_status_message(message)
            return
        self.config_panel.push_to_state()
        tflite_path = self.config_panel.tflite_path()
        if not tflite_path:
            message = 'No exported .tflite model selected. Export first or browse to a .tflite file.'
            self.log_panel.append_line(message)
            self.main_window.set_status_message(message)
            return

        train_config = TrainConfig(**vars(self.state.train_config))
        batch_size = self.config_panel.batch_size()
        max_rows = self.config_panel.max_rows()
        snapshot = dataset_df.copy(deep=True)
        receipt_root = self.state.out_dir_path
        dataset_source = self.config_panel.dataset_source()
        self.log_panel.append_line(f'Running TFLite check on {len(snapshot)} row(s): {tflite_path}...')

        def work(report):
            report('Loading TFLite interpreter and checking predictions', None)
            before = file_context(tflite_path)
            result = run_tflite_validation(
                dataset_df=snapshot, train_config=train_config,
                tflite_path=tflite_path, batch_size=batch_size, max_rows=max_rows,
            )
            result['experiment_context'] = stable_file_context(before, file_context(tflite_path))
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
                'TFLite check complete: '
                f"rows={result['rows_used']}, steering_mae={result['steering_mae']:.4f}, speed_mae={result['throttle_mae']:.4f}"
            )
            ranges = result.get('prediction_ranges', {}) if isinstance(result.get('prediction_ranges', {}), dict) else {}
            if ranges:
                steering_range = ranges.get('steering', {})
                speed_range = ranges.get('speed', {})
                self.log_panel.append_line(
                    'TFLite output range: '
                    f"steering={steering_range.get('min', 0.0):.4f}..{steering_range.get('max', 0.0):.4f}, "
                    f"speed={speed_range.get('min', 0.0):.4f}..{speed_range.get('max', 0.0):.4f}"
                )
            for note in result.get('backend_notes', [])[:6]:
                self.log_panel.append_line(f'  Note: {note}')
            self.main_window.set_status_message('TFLite check complete.')
            self.refresh_from_state()
            return (f"TFLite check completed: {result['rows_used']} rows",
                    confirmed_receipt_paths((receipt or {}).get("path")))

        def failed(error):
            self.log_panel.append_line(f'TFLite check failed: {error}')
            self.main_window.set_status_message('TFLite check failed. Review the Check Log, then retry.')

        self.task_runner.start(
            'TFLite validation', work, completed, on_failure=failed,
            controls=(self.actions_panel.run_button, self.actions_panel.clear_button, self.actions_panel.browse_button, self.config_panel),
        )

    def has_active_task(self) -> bool:
        return self.task_runner.active

    def clear_results(self) -> None:
        self.last_result = None
        self.plot_panel.set_result(None)
        self.frame_review_panel.set_result(None)
        self.summary_panel.set_result_text('TFLite check results cleared.')
        self.log_panel.clear()
        self.main_window.set_status_message('TFLite check results cleared.')
