from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.preprocess.preprocess_actions_panel import PreprocessActionsPanel
from ..panels.preprocess.preprocess_config_panel import PreprocessConfigPanel
from ..panels.preprocess.preprocess_filter_panel import PreprocessFilterPanel
from ..panels.preprocess.preprocess_result_panel import PreprocessResultPanel
from ..panels.preprocess.preprocess_summary_panel import PreprocessSummaryPanel
from ..services.data.record_loader_service import build_filtered_dataframe
from ..services.preprocess.preprocess_service import (
    apply_preprocessing_recipe,
    build_preprocess_summary,
    format_preprocess_preview,
    load_preprocess_settings,
    save_preprocess_settings,
    save_preprocessed_dataset,
)
from .dock_page import DockPage
from ..ui.formatting import splitter_args
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs


class PreprocessPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.output_tabs = None
        super().__init__('preprocess')

        self.summary_panel = PreprocessSummaryPanel()
        self.filter_panel = PreprocessFilterPanel(self.state)
        self.config_panel = PreprocessConfigPanel(self.state)
        self.actions_panel = PreprocessActionsPanel(
            preview_callback=self.preview_recipe,
            apply_callback=self.apply_recipe,
            reset_callback=self.reset_recipe,
            sync_callback=self.sync_image_size_to_train,
            save_settings_callback=self.save_recipe_settings,
            save_data_callback=self.save_processed_data,
            defaults_callback=self.use_recommended_defaults,
            auto_callback=self.auto_preprocess,
        )
        self.result_panel = PreprocessResultPanel()
        self.log_panel = LogPanel('Preprocess Log')

        self.build_default_layout()
        self.restore_layout()
        self._load_saved_recipe_if_available()
        self.refresh_from_state()

    def build_default_layout(self) -> None:
        self.clear_docks()

        workflow_tabs = make_workflow_tabs([
            (
                '1 Auto',
                make_scrollable_stack([
                    ('Source Summary', self.summary_panel, True),
                    ('Actions', self.actions_panel, True),
                ], object_name='preprocessAutoWorkflowScrollArea', intro='Check the source summary, then run Auto Preprocess.'),
                'Recommended workflow for most preprocessing runs.',
            ),
            (
                '2 Settings',
                make_scrollable_stack([
                    ('Source Filters', self.filter_panel, True),
                    ('Recipe + Image Size', self.config_panel, True),
                ], object_name='preprocessSettingsWorkflowScrollArea', intro='Optional filters, balancing, augmentation, and image size.'),
                'Optional filters and image settings.',
            ),
        ], object_name='preprocessWorkflowTabs')

        self.output_tabs = make_workflow_tabs([
            ('1 Preview', self.result_panel, 'Preview row counts and applied preprocessing results.'),
            ('2 Log', self.log_panel, 'Detailed preprocessing messages.'),
        ], object_name='preprocessOutputTabs')

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'Preprocess Workflow', workflow_tabs),
            self.make_panel_frame('result', 'Preprocess Review', self.output_tabs),
        ], object_name='main_workspace', **splitter_args('two_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='2 of 6',
            title='Preprocess',
            summary='Use Auto for the normal path, or open Settings for filters, balancing, augmentation, and image size.',
            next_step='Auto Preprocess',
            next_callback=lambda: self.reveal_widget(
                self.actions_panel.apply_btn,
                message='Focused the green Auto Preprocess button.'
            ),
            next_tooltip='Focus Auto Preprocess in Preprocess Workflow > 1 Auto.',
        )

    def _activate_preview_tab(self) -> None:
        if self.output_tabs is not None:
            self.output_tabs.setCurrentIndex(0)

    def _activate_log_tab(self) -> None:
        if self.output_tabs is not None:
            self.output_tabs.setCurrentIndex(1)

    def _load_saved_recipe_if_available(self) -> None:
        recipe = load_preprocess_settings(self.state.out_dir_path)
        if recipe:
            self.filter_panel.load_from_recipe(recipe)
            self.config_panel.load_from_recipe(recipe)
            self.state.preprocess_recipe = recipe
            self.state.last_saved_preprocess_settings_path = str(self.state.out_dir_path / 'preprocess' / 'preprocess_settings.json')

    def on_working_folder_changed(self, working_dir: Path | str) -> None:
        path = Path(working_dir).expanduser().resolve()
        self.state.last_saved_preprocess_settings_path = str(path / 'preprocess' / 'preprocess_settings.json')
        self.log_panel.append_line(f'Preprocess save/settings folder now follows loaded session: {path}')
        self.refresh_from_state()

    def _source_df(self) -> pd.DataFrame:
        source_mode = self.filter_panel.recipe().get('source_mode', 'Loaded dataset (all rows)')
        if source_mode == 'Current filtered rows':
            return self.state.filtered_df.copy()
        return self.state.dataset_df.copy()

    def current_recipe(self) -> dict[str, object]:
        recipe = {}
        recipe.update(self.filter_panel.recipe())
        recipe.update(self.config_panel.recipe())
        return recipe

    def refresh_from_state(self) -> None:
        self.summary_panel.set_summary(
            dataset_df=self.state.dataset_df,
            filtered_df=self.state.filtered_df,
            selected_sessions=self.state.selected_sessions,
            train_config=self.state.train_config,
            last_saved_preprocess_path=self.state.last_saved_preprocess_path,
        )
        self.filter_panel.sync_from_state()
        self.config_panel.sync_from_state()
        self.result_panel.set_preview_text(
            build_preprocess_summary(
                self.state.filtered_df,
                self.state.selected_sessions,
                title='Current active training dataset',
            )
        )

    def _set_recommended_defaults(self) -> dict[str, object]:
        self.filter_panel.reset_to_defaults()
        self.config_panel.reset_to_defaults()
        recipe = self.current_recipe()
        self.state.preprocess_recipe = recipe
        return recipe

    def use_recommended_defaults(self) -> None:
        self._set_recommended_defaults()
        self.preview_recipe(message_prefix='Recommended defaults loaded and previewed')

    def auto_preprocess(self) -> None:
        self._set_recommended_defaults()
        source_df = self._source_df()
        if source_df.empty:
            self.result_panel.set_preview_text(
                build_preprocess_summary(
                    source_df,
                    self.state.selected_sessions,
                    title='Auto preprocess could not start',
                )
            )
            self._activate_preview_tab()
            self.log_panel.append_line('Auto preprocess skipped: no source rows are loaded. Load sessions on the Data tab first.')
            self.main_window.set_status_message('Auto preprocess needs loaded session data first.')
            return
        self.apply_recipe(source_df=source_df, message_prefix='Auto preprocessing complete')

    def preview_recipe(self, *, message_prefix: str = 'Preprocess preview ready') -> None:
        source_df = self._source_df()
        recipe = self.current_recipe()
        result_df, summary = apply_preprocessing_recipe(source_df, recipe)
        preview_text = format_preprocess_preview(summary, recipe)
        self.result_panel.set_preview_text(preview_text)
        self.summary_panel.set_preview_counts(summary)
        self._activate_preview_tab()
        self.main_window.set_status_message(f'{message_prefix}: {len(result_df)} active row(s) after synthesis.')
        self.log_panel.append_line(
            f"{message_prefix} -> {summary['rows_after']} active row(s), generated {summary['generated_rows']} synthetic row(s)."
        )

    def apply_recipe(self, *, source_df: pd.DataFrame | None = None, message_prefix: str = 'Confirmed preprocessing') -> None:
        if source_df is None:
            source_df = self._source_df()
        if source_df.empty:
            self.result_panel.set_preview_text(
                build_preprocess_summary(
                    source_df,
                    self.state.selected_sessions,
                    title='No source rows to preprocess',
                )
            )
            self._activate_preview_tab()
            self.log_panel.append_line('Preprocess was not applied because no source rows are available.')
            self.main_window.set_status_message('No source rows to preprocess.')
            return

        recipe = self.current_recipe()
        result_df, summary = apply_preprocessing_recipe(source_df, recipe)

        self.state.preprocess_recipe = recipe
        self.state.filtered_df = result_df
        self.state.train_df = result_df.iloc[0:0].copy() if not result_df.empty else pd.DataFrame()
        self.state.val_df = result_df.iloc[0:0].copy() if not result_df.empty else pd.DataFrame()
        self.state.model = None
        self.state.history = {}
        self.state.train_config.img_h = int(recipe['image_height'])
        self.state.train_config.img_w = int(recipe['image_width'])

        self.result_panel.set_preview_text(format_preprocess_preview(summary, recipe, applied=True))
        self.summary_panel.set_summary(
            dataset_df=self.state.dataset_df,
            filtered_df=self.state.filtered_df,
            selected_sessions=self.state.selected_sessions,
            train_config=self.state.train_config,
            last_saved_preprocess_path=self.state.last_saved_preprocess_path,
        )
        self.summary_panel.set_preview_counts(summary)
        self.main_window.train_page.config_panel.img_h.setValue(self.state.train_config.img_h)
        self.main_window.train_page.config_panel.img_w.setValue(self.state.train_config.img_w)
        self.main_window.data_page.refresh_from_state()
        self.main_window.train_page.refresh_from_state()
        self.main_window.export_page.refresh_from_state()
        self.main_window.validation_page.refresh_from_state()
        self._activate_preview_tab()
        message = (
            f"{message_prefix}: {summary['rows_after']} active row(s), including {summary['generated_rows']} synthetic row(s). "
            f"Image size set to {recipe['image_width']}x{recipe['image_height']}. Train tab uses all active preprocessed rows; "
            "Data review hides generated rows by default and shows their original source frames for editing."
        )
        self.main_window.set_status_message(message)
        self.log_panel.append_line(message)

    def reset_recipe(self) -> None:
        self.filter_panel.reset_to_defaults()
        self.config_panel.reset_to_defaults()
        baseline = build_filtered_dataframe(self.state.dataset_df, self.state.train_config.only_manual)
        self.state.preprocess_recipe = {}
        self.state.filtered_df = baseline
        self.state.train_df = baseline.iloc[0:0].copy() if not baseline.empty else pd.DataFrame()
        self.state.val_df = baseline.iloc[0:0].copy() if not baseline.empty else pd.DataFrame()
        self.state.model = None
        self.state.history = {}
        self.refresh_from_state()
        self.main_window.data_page.refresh_from_state()
        self.main_window.train_page.refresh_from_state()
        self.main_window.export_page.refresh_from_state()
        self.main_window.validation_page.refresh_from_state()
        self.log_panel.append_line('Reset preprocessing recipe and restored the baseline loaded dataset filter.')
        self.main_window.set_status_message('Preprocess settings reset to defaults.')

    def save_recipe_settings(self) -> None:
        recipe = self.current_recipe()
        path = save_preprocess_settings(recipe, self.state.out_dir_path)
        self.state.preprocess_recipe = recipe
        self.state.last_saved_preprocess_settings_path = str(path)
        self._activate_log_tab()
        self.log_panel.append_line(f'Saved preprocess settings: {path}')
        self.main_window.set_status_message('Saved preprocess settings.')

    def save_processed_data(self) -> None:
        active_df = self.state.filtered_df.copy()
        if active_df.empty:
            self.log_panel.append_line('No active preprocessed rows to save. Confirm preprocessing first.')
            self.main_window.set_status_message('No active preprocessed rows to save.')
            return
        recipe = self.state.preprocess_recipe or self.current_recipe()
        folder = save_preprocessed_dataset(active_df, recipe, self.state.out_dir_path)
        self.state.last_saved_preprocess_path = str(folder)
        self.summary_panel.set_summary(
            dataset_df=self.state.dataset_df,
            filtered_df=self.state.filtered_df,
            selected_sessions=self.state.selected_sessions,
            train_config=self.state.train_config,
            last_saved_preprocess_path=self.state.last_saved_preprocess_path,
        )
        self._activate_log_tab()
        self.log_panel.append_line(f'Saved preprocessed dataset: {folder}')
        self.main_window.set_status_message('Saved preprocessed dataset.')

    def sync_image_size_to_train(self) -> None:
        recipe = self.current_recipe()
        self.state.train_config.img_h = int(recipe['image_height'])
        self.state.train_config.img_w = int(recipe['image_width'])
        self.main_window.train_page.config_panel.img_h.setValue(int(recipe['image_height']))
        self.main_window.train_page.config_panel.img_w.setValue(int(recipe['image_width']))
        self.summary_panel.set_summary(
            dataset_df=self.state.dataset_df,
            filtered_df=self.state.filtered_df,
            selected_sessions=self.state.selected_sessions,
            train_config=self.state.train_config,
            last_saved_preprocess_path=self.state.last_saved_preprocess_path,
        )
        self._activate_log_tab()
        self.log_panel.append_line(
            f"Synced preprocess image size to Train tab: {recipe['image_width']}x{recipe['image_height']}."
        )
        self.main_window.set_status_message('Preprocess image size synced to Train tab.')
