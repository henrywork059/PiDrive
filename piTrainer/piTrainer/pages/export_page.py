from __future__ import annotations


from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
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
        super().__init__('export')

        self.model_status_panel = ModelStatusPanel()
        self.options_panel = ExportOptionsPanel(self.state)
        self.actions_panel = ExportActionsPanel(self.export_model)
        self.log_panel = LogPanel('Export Log')
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
            self.actions_panel.set_export_status(f'Export failed:\n{exc}', success=False)
            self.log_panel.append_line(f'ERROR: {exc}')
            self.main_window.set_status_message('Export failed.')
            return

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
        self.log_panel.append_line('Export finished. TensorFlow converter details are summarised above; non-fatal internal converter chatter is suppressed.')
        self.main_window.set_status_message(
            'Export saved: ' + '; '.join(saved_lines) if saved_lines else 'Export finished. Next: 6 TFLite Check.'
        )
