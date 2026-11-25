from __future__ import annotations

from pathlib import Path

from ..app_state import ExportConfig, TrainConfig

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.common.task_progress_panel import TaskProgressPanel
from ..services.background_task import BackgroundTaskRunner
from ..services.task_outputs import confirmed_model_paths
from ..services.train.experiment_service import attach_model_artifact
from ..panels.export.export_actions_panel import ExportActionsPanel
from ..panels.export.export_options_panel import ExportOptionsPanel
from ..panels.export.model_status_panel import ModelStatusPanel
from ..services.export.export_service import export_model_artifacts
from .dock_page import DockPage
from ..ui.formatting import splitter_args
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs


class ExportPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self._confirmed_export_model = None
        self._confirmed_export_paths = ()
        super().__init__('export')

        self.model_status_panel = ModelStatusPanel()
        self.options_panel = ExportOptionsPanel(self.state)
        self.actions_panel = ExportActionsPanel(self.export_model)
        self.log_panel = LogPanel('Export Log')
        self.task_progress = TaskProgressPanel()
        self.actions_panel.layout().addWidget(self.task_progress)
        self.task_runner = BackgroundTaskRunner(self.task_progress, self)
        self.build_default_layout()
        self.restore_layout()

    def build_default_layout(self) -> None:
        self.clear_docks()

        workflow_tabs = make_workflow_tabs([
            (
                '1 Export',
                make_scrollable_stack([
                    ('Actions', self.actions_panel, True),
                    ('Options', self.options_panel, True),
                ], object_name='exportRunWorkflowScrollArea', intro='Choose output folder and file types, then export.'),
            ),
            (
                '2 Status',
                make_scrollable_stack([
                    ('Model', self.model_status_panel, True),
                ], object_name='exportStatusWorkflowScrollArea', intro='Confirm that a trained model is ready before exporting.'),
            ),
        ], object_name='exportWorkflowTabs')

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'Export Workflow', workflow_tabs),
            self.make_panel_frame('log', 'Export Log', self.log_panel),
        ], object_name='main_workspace', **splitter_args('two_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='5 of 6',
            title='Export',
            summary='Export deployment files and check model readiness.',
            next_step='Export',
            next_callback=lambda: self.reveal_widget(
                self.actions_panel.export_btn,
                message='Focused the green Export button.'
            ),
            next_tooltip='Focus Export in 1 Export.',
        )

    def set_output_dir(self, folder: str) -> None:
        self.options_panel.set_output_dir(folder)

    def refresh_from_state(self) -> None:
        model_ready = self.state.model is not None
        history_len = len(self.state.history.get('loss', [])) if self.state.history else 0
        train_page = getattr(self.main_window, 'train_page', None)
        provenance = train_page.provenance_for_model(self.state.model) if model_ready and train_page is not None else None
        run = provenance[0] if provenance else None
        self.model_status_panel.set_status(
            model_ready=model_ready,
            train_rows=run.get('train_rows') if run else None,
            val_rows=run.get('validation_rows') if run else None,
            epochs_ran=(run.get('metrics') or {}).get('epochs_ran') if run else (history_len if model_ready and history_len else None),
            run_id=run.get('run_id') if run else None,
        )

    def has_confirmed_export_for(self, model) -> bool:
        if model is None or model is not self._confirmed_export_model or not self._confirmed_export_paths:
            return False
        try:
            return all(Path(path).is_file() and Path(path).stat().st_size > 0
                       for path in self._confirmed_export_paths)
        except (OSError, ValueError):
            return False

    def export_model(self) -> None:
        if not self.main_window.can_start_task(self):
            return
        if self.task_runner.active:
            self.log_panel.append_line('Export in progress. Wait for completion before starting another export.')
            return
        self.options_panel.push_to_state()
        if self.state.model is None:
            self.log_panel.append_line('No model to export. Open Train and complete training first.')
            return
        train_page = getattr(self.main_window, 'train_page', None)
        if train_page is not None and train_page.has_active_task():
            self.log_panel.append_line('Wait for training to finish before exporting the model.')
            return

        model = self.state.model
        export_config = ExportConfig(**vars(self.state.export_config))
        train_config = TrainConfig(**vars(self.state.train_config))
        train_df = self.state.train_df.copy(deep=True)
        self.actions_panel.set_export_status('Export running — no output confirmed yet.')
        provenance = train_page.provenance_for_model(model) if train_page is not None else None
        run = provenance[0] if provenance else None
        if run and isinstance(run.get('model_settings'), dict):
            train_config = TrainConfig(**{**vars(train_config), **{k: v for k, v in run['model_settings'].items() if k in vars(train_config)}})
        shape = getattr(model, 'input_shape', None)
        if isinstance(shape, (tuple, list)) and len(shape) == 4 and shape[1] and shape[2]:
            train_config.img_h, train_config.img_w = int(shape[1]), int(shape[2])

        def work(report):
            report('Preparing model export', None)
            created = export_model_artifacts(
                model=model, export_config=export_config,
                train_df=train_df, train_config=train_config,
                progress_callback=report, experiment_record=run, seed_known=run is not None,
            )
            linked = None
            experiment_paths = []
            if provenance is not None:
                linked, root = provenance
                for artifact in created:
                    report(f'Linking experiment provenance: {artifact.kind}', None)
                    linked, sidecar = attach_model_artifact(root, linked, artifact.path)
                    experiment_paths.append(str(sidecar))
            return created, linked, experiment_paths

        def completed(result):
            created, linked, experiment_paths = result
            if not created:
                raise RuntimeError('Exporter returned no completed artifacts.')
            output_paths = confirmed_model_paths(item.path for item in created)
            if linked is not None and train_page is not None:
                train_page.note_model_run_artifacts(model, linked)
                output_paths = (*output_paths, *experiment_paths)
            elif provenance is None:
                self.log_panel.append_line('Experiment provenance: Unknown (model has no tracked R40 training run).')
            self._confirmed_export_model = model
            self._confirmed_export_paths = tuple(output_paths)
            latest_tflite_path = ''
            saved_lines: list[str] = []
            for item in created:
                size_label = getattr(item, 'size_label', '')
                suffix = f' ({size_label})' if size_label else ''
                kind = getattr(item, "kind", "artifact")
                path = getattr(item, "path", item)
                self.log_panel.append_line(f'Created {kind}: {path}{suffix}')
                saved_lines.append(f'{kind} -> {path}{suffix}')
                if str(kind).lower() == '.tflite' or str(path).lower().endswith('.tflite'):
                    latest_tflite_path = str(path)
                for note in getattr(item, 'notes', ()): 
                    self.log_panel.append_line(f'  Note: {note}')
            if saved_lines:
                self.actions_panel.set_export_status(
                    'Saved exported model file(s):\n' + '\n'.join(saved_lines),
                    success=True,
                )
                self.log_panel.append_line('Saved exported model file(s):')
                for line in saved_lines:
                    self.log_panel.append_line(f'  {line}')
            if latest_tflite_path:
                self.state.last_exported_tflite_path = latest_tflite_path
                export_validation_page = getattr(self.main_window, 'export_validation_page', None)
                if export_validation_page is not None:
                    export_validation_page.set_exported_tflite_path(latest_tflite_path)
                self.log_panel.append_line(f'Linked exported TFLite model to 6 TFLite Check: {latest_tflite_path}')
            self.refresh_from_state()
            self.log_panel.append_line('Export finished. TensorFlow converter details are summarised above; non-fatal internal converter chatter is suppressed.')
            self.main_window.set_status_message(
                'Export saved: ' + '; '.join(saved_lines) if saved_lines else 'Export finished. Next: 6 TFLite Check.'
            )

            return (f"Export complete: {len(created)} model(s)", output_paths)

        def failed(error):
            self.actions_panel.set_export_status(f'Export failed:\n{error}', success=False)
            self.log_panel.append_line(f'ERROR: {error}')
            self.main_window.set_status_message('Export failed. Review Export Log, then retry; partial files are not confirmed.')

        self.task_runner.start(
            'Model export', work, completed, on_failure=failed,
            controls=(self.actions_panel.export_btn, self.options_panel),
        )

    def has_active_task(self) -> bool:
        return self.task_runner.active
