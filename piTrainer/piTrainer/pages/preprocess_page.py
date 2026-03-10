from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

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


class PreprocessPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
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
        )
        self.result_panel = PreprocessResultPanel()
        self.log_panel = LogPanel('Preprocess Log')

        self.build_default_layout()
        self.restore_layout()
        self._load_saved_recipe_if_available()
        self.refresh_from_state()

    def build_default_layout(self) -> None:
        self.clear_docks()

        summary_dock = self.add_panel('summary', 'Source Summary', self.summary_panel, Qt.LeftDockWidgetArea)
        filter_dock = self.add_panel('filter', 'Preprocess Filters', self.filter_panel, Qt.LeftDockWidgetArea)
        config_dock = self.add_panel('config', 'Preprocess Recipe', self.config_panel, Qt.LeftDockWidgetArea)
        actions_dock = self.add_panel('actions', 'Preprocess Actions', self.actions_panel, Qt.LeftDockWidgetArea)
        result_dock = self.add_panel('result', 'Preprocess Preview', self.result_panel, Qt.RightDockWidgetArea)
        log_dock = self.add_panel('log', 'Preprocess Log', self.log_panel, Qt.RightDockWidgetArea)

        self.splitDockWidget(summary_dock, filter_dock, Qt.Vertical)
        self.splitDockWidget(filter_dock, config_dock, Qt.Vertical)
        self.splitDockWidget(config_dock, actions_dock, Qt.Vertical)
        self.splitDockWidget(summary_dock, result_dock, Qt.Horizontal)
        self.splitDockWidget(result_dock, log_dock, Qt.Vertical)

        self.resizeDocks([summary_dock, filter_dock, config_dock, actions_dock], [180, 300, 250, 170], Qt.Vertical)
        self.resizeDocks([result_dock, log_dock], [520, 170], Qt.Vertical)
        self.resizeDocks([summary_dock, result_dock], [330, 760], Qt.Horizontal)

    def _load_saved_recipe_if_available(self) -> None:
        recipe = load_preprocess_settings(self.state.out_dir_path)
        if recipe:
            self.filter_panel.load_from_recipe(recipe)
            self.config_panel.load_from_recipe(recipe)
            self.state.preprocess_recipe = recipe
            self.state.last_saved_preprocess_settings_path = str(self.state.out_dir_path / 'preprocess' / 'preprocess_settings.json')

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

    def preview_recipe(self) -> None:
        source_df = self._source_df()
        recipe = self.current_recipe()
        result_df, summary = apply_preprocessing_recipe(source_df, recipe)
        preview_text = format_preprocess_preview(summary, recipe)
        self.result_panel.set_preview_text(preview_text)
        self.summary_panel.set_preview_counts(summary)
        self.main_window.set_status_message(f'Preprocess preview ready: {len(result_df)} active row(s) after synthesis.')
        self.log_panel.append_line(
            f"Previewed preprocess recipe -> {summary['rows_after']} active row(s), generated {summary['generated_rows']} synthetic row(s)."
        )

    def apply_recipe(self) -> None:
        source_df = self._source_df()
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
        message = (
            f"Confirmed preprocessing: {summary['rows_after']} active row(s), including {summary['generated_rows']} synthetic row(s). "
            f"Image size set to {recipe['image_width']}x{recipe['image_height']}. Train tab now uses the active preprocessed rows."
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
        self.log_panel.append_line(
            f"Synced preprocess image size to Train tab: {recipe['image_width']}x{recipe['image_height']}."
        )
        self.main_window.set_status_message('Preprocess image size synced to Train tab.')
