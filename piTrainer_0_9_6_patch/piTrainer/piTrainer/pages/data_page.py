from __future__ import annotations

import pandas as pd
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from ..app_state import AppState
from ..panels.data.bulk_edit_panel import BulkEditPanel
from ..panels.data.data_control_panel import DataControlPanel
from ..panels.data.data_plot_panel import DataPlotPanel
from ..panels.data.dataset_stats_panel import DatasetStatsPanel
from ..panels.data.frame_filter_panel import FrameFilterPanel
from ..panels.data.image_preview_panel import ImagePreviewPanel
from ..panels.data.merge_sessions_panel import MergeSessionsPanel
from ..panels.data.model_deploy_panel import ModelDeployPanel
from ..panels.data.overlay_control_panel import OverlayControlPanel
from ..panels.data.playback_control_panel import PlaybackControlPanel
from ..panels.data.preview_panel import PreviewPanel
from ..panels.data.session_source_panel import SessionSourcePanel
from ..services.data.delete_service import hide_frames_from_training, purge_hidden_frames, recover_hidden_frames
from ..services.data.edit_service import update_frame_controls_batch, update_frame_controls_many
from ..services.data.filter_service import filter_preview_dataframe
from ..services.data.merge_service import merge_sessions
from ..services.data.model_deploy_service import run_model_deploy
from ..services.data.record_loader_service import build_filtered_dataframe, load_records_dataframe
from ..services.data.visibility_service import is_synthetic_record, without_synthetic_rows
from ..services.data.session_service import list_sessions
from ..services.data.stats_service import calculate_basic_stats
from .dock_page import DockPage
from ..ui.formatting import get_density_profile, splitter_args
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs


class DataPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.current_preview_source_df = pd.DataFrame()
        self.last_focus_redirected_to_source = False
        self.last_focus_source_frame_id = ''
        super().__init__('data')

        self.session_source_panel = SessionSourcePanel(self.state, self.refresh_sessions, self.load_selected_sessions)
        self.session_list_panel = self.session_source_panel
        self.bulk_edit_panel = BulkEditPanel(
            apply_steering_callback=self.apply_bulk_steering_edit,
            apply_speed_callback=self.apply_bulk_speed_edit,
            select_all_callback=self.select_all_preview_frames_for_bulk_edit,
        )
        self.merge_sessions_panel = MergeSessionsPanel(self.merge_selected_sessions)
        self.filter_panel = FrameFilterPanel(self.apply_preview_filter, self.clear_preview_filter)
        self.overlay_panel = OverlayControlPanel(self.on_overlay_options_changed)
        self.stats_panel = DatasetStatsPanel()
        self.image_preview_panel = ImagePreviewPanel(record_edited_callback=self.on_image_record_edited)
        self.preview_panel = PreviewPanel(
            selection_callback=self.on_preview_record_selected,
            playback_state_callback=self.on_playback_state_changed,
        )
        self.image_preview_panel.set_record_navigation_callback(self.preview_panel.select_adjacent_record)
        self.playback_panel = PlaybackControlPanel(
            play_callback=self.start_preview_playback,
            stop_callback=self.stop_preview_playback,
            restart_callback=self.restart_preview_playback,
            speed_change_callback=self.on_playback_speed_changed,
        )
        self.plot_panel = DataPlotPanel()
        self.single_edit_plot_timer = QTimer(self)
        self.single_edit_plot_timer.setSingleShot(True)
        self.single_edit_plot_timer.setInterval(650)
        self.single_edit_plot_timer.timeout.connect(self.refresh_plot_from_preview)
        self.data_control_panel = DataControlPanel(
            delete_frame_callback=self.delete_selected_frame,
            recover_last_callback=self.recover_last_hidden_frames,
            recover_all_callback=self.recover_all_hidden_frames,
        )
        self.model_deploy_panel = ModelDeployPanel(
            self.state,
            deploy_callback=self.deploy_model_to_visible_frames,
            apply_selected_callback=self.apply_deployed_outputs_to_selected,
            sort_steering_diff_callback=self.sort_by_steering_diff,
            sort_speed_diff_callback=self.sort_by_speed_diff,
        )
        self.build_default_layout()
        self.restore_layout()
        self.preview_panel.set_playback_fps(self.playback_panel.playback_fps())

    def build_default_layout(self) -> None:
        self.clear_docks()

        workflow_tabs = make_workflow_tabs([
            (
                '1 Load',
                make_scrollable_stack([
                    ('Session Source', self.session_source_panel, True),
                ], object_name='dataLoadWorkflowScrollArea', intro='Choose a records root, scan sessions, select sessions, then load.'),
            ),
            (
                '2 Hide & Recover',
                make_scrollable_stack([
                    ('Hide & Recover', self.data_control_panel, True),
                ], object_name='dataDeleteRecoverWorkflowScrollArea', intro='Hide bad frames or recover hidden ones.'),
            ),
            (
                '3 Filter',
                make_scrollable_stack([
                    ('Filter', self.filter_panel, True),
                ], object_name='dataFilterWorkflowScrollArea', intro='Filter by text, mode, speed, or steering.'),
            ),
            (
                '4 Deploy',
                make_scrollable_stack([
                    ('Model Deploy', self.model_deploy_panel, True),
                ], object_name='dataDeployWorkflowScrollArea', intro='Run model output on visible frames and compare labels.'),
            ),
            (
                '5 Review',
                make_scrollable_stack([
                    ('Bulk Edit', self.bulk_edit_panel, True, 'Overwrite steering or speed for selected rows.'),
                    ('Merge Sessions', self.merge_sessions_panel, False),
                    ('Overlays', self.overlay_panel, False),
                ], object_name='dataReviewWorkflowScrollArea', intro='Edit labels, merge sessions, and check overlays.'),
            ),
        ], object_name='dataWorkflowTabs')

        review_tabs = make_workflow_tabs([
            (
                '1 Records',
                self.preview_panel,
                'Inspect and select frame rows.',
            ),
            (
                '2 Stats',
                self.stats_panel,
                'Check dataset totals and label spread.',
            ),
            (
                '3 Plots',
                self.plot_panel,
                'Review steering, speed, mode, and session plots.',
            ),
        ], object_name='dataReviewTabs')

        visual_review = QWidget()
        visual_review.setObjectName('dataImagePlaybackStack')
        visual_layout = QVBoxLayout(visual_review)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        visual_layout.setSpacing(get_density_profile().panel_spacing)
        visual_layout.addWidget(self.image_preview_panel, 1)
        visual_layout.addWidget(self.playback_panel, 0)

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'Data Workflow', workflow_tabs),
            self.make_panel_frame('record_review', 'Data Review', review_tabs),
            self.make_panel_frame('image_preview', 'Image + Playback', visual_review),
        ], object_name='main_workspace', **splitter_args('three_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='1 of 6',
            title='Data',
            summary='Load sessions, hide/recover rows, filter, deploy models, review labels, and check overlays.',
            next_step='Load Selected',
            next_callback=lambda: self.reveal_widget(
                self.session_source_panel.load_btn,
                message='Focused the green Load Selected button.'
            ),
            next_tooltip='Focus Load Selected in 1 Load.',
        )

    @staticmethod
    def _record_identity(record) -> tuple[str, str, str, str]:
        return PreviewPanel.record_identity(record)

    @staticmethod
    def _bulk_edit_target_key(record) -> tuple[str, str, str, str]:
        return (
            str(record.get('session', '') or ''),
            str(record.get('frame_id', '') or ''),
            Path(str(record.get('abs_image', '') or record.get('image_path', '') or record.get('frame', '') or '')).name,
            str(record.get('ts', '') or ''),
        )

    @staticmethod
    def _record_mask(df: pd.DataFrame, identity: tuple[str, str, str, str]):
        if df.empty:
            return pd.Series([], dtype=bool)

        def column_text(column: str) -> pd.Series:
            return DataPage._column_text(df, column)

        session, frame_id, ts, abs_image = identity
        return (
            column_text('session') == session
        ) & (
            column_text('frame_id') == frame_id
        ) & (
            column_text('ts') == ts
        ) & (
            column_text('abs_image') == abs_image
        )


    @staticmethod
    def _review_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Return Data-page review rows with generated/synthetic copies hidden by default."""
        return without_synthetic_rows(df).reset_index(drop=True) if isinstance(df, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    def _column_text(df: pd.DataFrame, column: str) -> pd.Series:
        if column in df.columns:
            series = df[column]
            return series.astype(object).where(series.notna(), '').astype(str)
        return pd.Series([''] * len(df), index=df.index, dtype=str)

    def _find_source_record_for_synthetic(self, record: dict) -> dict | None:
        if not record or not is_synthetic_record(record):
            return None
        source_frame_id = str(record.get('source_frame_id', '') or '').strip()
        if not source_frame_id:
            return None
        session = str(record.get('session', '') or '').strip()
        abs_image = str(record.get('abs_image', '') or '').strip()
        ts = str(record.get('ts', '') or '').strip()

        candidates = [
            self.current_preview_source_df,
            self._review_dataframe(self.state.filtered_df),
            self._review_dataframe(self.state.dataset_df),
        ]
        for df in candidates:
            if not isinstance(df, pd.DataFrame) or df.empty or 'frame_id' not in df.columns:
                continue
            mask = self._column_text(df, 'frame_id').str.strip().eq(source_frame_id)
            if session:
                mask &= self._column_text(df, 'session').str.strip().eq(session)
            if not mask.any() and abs_image:
                # Some older rows may not have a stable source_frame_id. Fall back
                # to the shared source image when it is in the same session.
                mask = self._column_text(df, 'abs_image').str.strip().eq(abs_image)
                if session:
                    mask &= self._column_text(df, 'session').str.strip().eq(session)
            if not mask.any() and ts:
                relaxed = self._column_text(df, 'frame_id').str.strip().eq(source_frame_id)
                relaxed &= self._column_text(df, 'ts').str.strip().eq(ts)
                if session:
                    relaxed &= self._column_text(df, 'session').str.strip().eq(session)
                mask = relaxed
            if mask.any():
                return df.loc[mask].iloc[0].to_dict()
        return None

    def _focus_target_record(self, record: dict) -> dict:
        self.last_focus_redirected_to_source = False
        self.last_focus_source_frame_id = ''
        source_record = self._find_source_record_for_synthetic(record)
        if source_record:
            self.last_focus_redirected_to_source = True
            self.last_focus_source_frame_id = str(record.get('source_frame_id', '') or '')
            return source_record
        return record

    def refresh_sessions(self) -> None:
        self.state.available_sessions = list_sessions(self.state.records_root_path)
        self.session_source_panel.set_sessions(self.state.available_sessions)
        self.main_window.set_status_message(
            f"Found {len(self.state.available_sessions)} session(s) under {self.state.records_root_path}."
        )

    def load_selected_sessions(self) -> None:
        selected = self.session_source_panel.selected_sessions()
        self.state.selected_sessions = selected
        self._load_sessions(selected)

    def _load_sessions(self, selected: list[str]) -> None:
        df = load_records_dataframe(self.state.records_root_path, selected)
        filtered = build_filtered_dataframe(df, self.state.train_config.only_manual)
        self.state.dataset_df = df
        self.state.filtered_df = filtered
        self.state.train_df = filtered.iloc[0:0].copy()
        self.state.val_df = filtered.iloc[0:0].copy()
        self.state.model = None
        self.state.history = {}
        self.current_preview_source_df = self._review_dataframe(filtered)

        sync_working_folder = getattr(self.main_window, 'sync_working_folder_from_loaded_sessions', None)
        if callable(sync_working_folder):
            sync_working_folder()

        stats = calculate_basic_stats(filtered)
        self.stats_panel.set_stats(stats)
        self.apply_preview_filter()
        self.main_window.on_dataset_loaded()

    def focus_record(self, record: dict | None) -> bool:
        if not record:
            return False
        target_record = self._focus_target_record(dict(record))
        session = str(target_record.get('session', '')).strip()
        if not session:
            return False

        current_sessions = set(self.state.dataset_df.get('session', pd.Series(dtype=str)).astype(str).tolist()) if not self.state.dataset_df.empty else set()
        need_reload = session not in current_sessions
        self.state.selected_sessions = [session]
        self.session_source_panel.set_selected_sessions([session])
        if need_reload:
            self._load_sessions([session])
            if self.last_focus_redirected_to_source:
                reloaded_target = self._find_source_record_for_synthetic(record)
                if reloaded_target:
                    target_record = reloaded_target

        identity = self._record_identity(target_record)
        self.filter_panel.reset()
        self.apply_preview_filter(select_identity=identity)
        found = self.preview_panel.select_record_identity(identity)
        if found:
            self.on_preview_record_selected(self.preview_panel.selected_record())
        return bool(found)

    def merge_selected_sessions(self) -> None:
        selected = self.session_source_panel.selected_sessions()
        if len(selected) < 2:
            QMessageBox.information(self, 'Merge Sessions', 'Select at least 2 sessions first.')
            return

        merged_name = self.merge_sessions_panel.merged_session_name()
        if not merged_name:
            merged_name = f'merged_{selected[0]}_{selected[-1]}'
            self.merge_sessions_panel.set_merged_session_name(merged_name)

        confirm = QMessageBox.question(
            self,
            'Merge Sessions',
            'Create one merged session from the selected sessions?'
            + f"\n\nSource sessions: {', '.join(selected)}"
            + f"\nTarget session: {merged_name}",
        )
        if confirm != QMessageBox.Yes:
            return

        ok, message, details = merge_sessions(self.state.records_root_path, selected, merged_name)
        if not ok:
            QMessageBox.warning(self, 'Merge Sessions', message)
            self.main_window.set_status_message(message)
            return

        target_session = str(details.get('target_session', merged_name))
        self.state.selected_sessions = selected.copy()
        self.refresh_sessions()
        if self.merge_sessions_panel.should_load_after_merge():
            self.state.selected_sessions = [target_session]
            self.session_source_panel.set_selected_sessions([target_session])
            self._load_sessions([target_session])
        else:
            self.session_source_panel.set_selected_sessions(selected)
            self.main_window.set_status_message(message)

        QMessageBox.information(self, 'Merge Sessions', message)

    def apply_preview_filter(self, select_identity: tuple[str, str, str, str] | None = None) -> None:
        filtered_preview = filter_preview_dataframe(
            self.current_preview_source_df,
            text=self.filter_panel.filter_text(),
            mode=self.filter_panel.selected_mode(),
            speed_range=self.filter_panel.speed_range() if self.filter_panel.speed_filter_enabled() else None,
            steering_range=self.filter_panel.steering_range() if self.filter_panel.steering_filter_enabled() else None,
        )
        self.preview_panel.set_dataframe(filtered_preview)
        if select_identity:
            self.preview_panel.select_record_identity(select_identity)
        self.plot_panel.set_dataframe(filtered_preview)
        if hasattr(self, 'model_deploy_panel'):
            prediction_count = 0
            if 'pred_steering' in filtered_preview.columns and ('pred_throttle' in filtered_preview.columns or 'pred_speed' in filtered_preview.columns):
                prediction_count = int(pd.to_numeric(filtered_preview.get('pred_steering'), errors='coerce').notna().sum())
            self.model_deploy_panel.set_prediction_count(prediction_count)
        if filtered_preview.empty:
            self.image_preview_panel.clear_preview()
        self.main_window.set_status_message(f'Displaying {len(filtered_preview)} preview frame(s).')

    def clear_preview_filter(self) -> None:
        self.filter_panel.reset()
        self.apply_preview_filter()

    def on_overlay_options_changed(self, options: dict[str, bool]) -> None:
        self.image_preview_panel.set_overlay_options(options)
        enabled = [name for name, active in options.items() if active]
        if enabled:
            self.main_window.set_status_message(f"Overlay enabled: {', '.join(enabled)}")
        else:
            self.main_window.set_status_message('Overlay cleared.')

    def on_preview_record_selected(self, record) -> None:
        selected_count = len(self.preview_panel.selected_records())
        self.bulk_edit_panel.set_selected_count(selected_count)
        if hasattr(self, 'model_deploy_panel'):
            self.model_deploy_panel.set_selected_count(selected_count)
        if not record:
            self.image_preview_panel.clear_preview()
            return
        self.image_preview_panel.set_record(record)

    def on_image_record_edited(self, record: dict | list[dict]) -> None:
        if not record:
            return
        if isinstance(record, list):
            self.on_image_records_edited(record)
            return
        self.on_image_records_edited([record])

    def on_image_records_edited(self, records: list[dict]) -> None:
        records = [dict(record) for record in records if record]
        if not records:
            return
        self.preview_panel.stop_autoplay()
        current_record = self.preview_panel.selected_record()
        current_identity = self._record_identity(current_record) if current_record else None

        result = update_frame_controls_many(self.state.records_root_path, records)
        matched_key_set = {tuple(key) for key in result.get('matched_keys', [])}
        updated_records = [
            record for record in records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]
        if not updated_records:
            failed_messages = list(result.get('failed_messages', []))
            self.main_window.set_status_message(failed_messages[0] if failed_messages else 'No frame edit was applied.')
            return

        needs_filter_rebuild = False
        for edited_record in updated_records:
            identity = self._record_identity(edited_record)
            steering = float(edited_record.get('steering', 0.0) or 0.0)
            throttle = float(edited_record.get('throttle', 0.0) or 0.0)
            self._update_record_field_in_loaded_data(identity, 'steering', steering)
            self._update_record_field_in_loaded_data(identity, 'throttle', throttle)
            pred_steering = self._prediction_value(edited_record, 'pred_steering')
            pred_throttle = self._prediction_value(edited_record, 'pred_throttle')
            if pred_steering is not None and pred_throttle is not None:
                self._set_record_prediction_fields(
                    identity,
                    pred_steering=pred_steering,
                    pred_throttle=pred_throttle,
                    steering_diff=abs(pred_steering - steering),
                    speed_diff=abs(pred_throttle - throttle),
                )
                needs_filter_rebuild = True
            needs_filter_rebuild = needs_filter_rebuild or self._single_edit_needs_filter_rebuild(steering=steering, throttle=throttle)

        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        if needs_filter_rebuild:
            self.apply_preview_filter(select_identity=current_identity)
        else:
            for edited_record in updated_records:
                identity = self._record_identity(edited_record)
                preserve_preview_selection = bool(current_identity and current_identity != identity)
                self.preview_panel.update_record_values(
                    identity,
                    {
                        'steering': float(edited_record.get('steering', 0.0) or 0.0),
                        'throttle': float(edited_record.get('throttle', 0.0) or 0.0),
                    },
                    preserve_selection=preserve_preview_selection,
                )
            self.schedule_plot_refresh_from_preview()

        failed_messages = list(result.get('failed_messages', []))
        updated_count = int(result.get('updated_count', 0) or 0)
        rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        self.main_window.set_status_message(
            f'Updated steering/speed for {updated_count} frame edit(s) with {rows_changed} metadata row(s) changed.'
            + (f' {len(failed_messages)} failed.' if failed_messages else '')
        )
        if failed_messages:
            QMessageBox.warning(self, 'Edit Frame Data', '\n'.join(failed_messages[:8]))

    @staticmethod
    def _prediction_value(record: dict, key: str) -> float | None:
        value = record.get(key)
        if value is None and key == 'pred_throttle':
            value = record.get('pred_speed')
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _has_deployed_prediction(record: dict) -> bool:
        return DataPage._prediction_value(record, 'pred_steering') is not None and DataPage._prediction_value(record, 'pred_throttle') is not None

    def _set_record_prediction_fields(
        self,
        identity: tuple[str, str, str, str],
        *,
        pred_steering: float,
        pred_throttle: float,
        steering_diff: float,
        speed_diff: float,
    ) -> None:
        for field_name, value in {
            'pred_steering': pred_steering,
            'pred_throttle': pred_throttle,
            'steering_diff': steering_diff,
            'speed_diff': speed_diff,
        }.items():
            self._update_record_field_in_loaded_data(identity, field_name, float(value))

    def _merge_deploy_predictions(self, deploy_rows: list[dict]) -> list[tuple[str, str, str, str]]:
        updated_identities: list[tuple[str, str, str, str]] = []
        for row in deploy_rows:
            identity = self._record_identity(row)
            if not any(identity):
                continue
            pred_steering = float(row.get('pred_steering', 0.0) or 0.0)
            pred_throttle = float(row.get('pred_throttle', row.get('pred_speed', 0.0)) or 0.0)
            steering_diff = float(row.get('steering_diff', abs(pred_steering - float(row.get('target_steering', 0.0) or 0.0))) or 0.0)
            speed_diff = float(row.get('speed_diff', abs(pred_throttle - float(row.get('target_speed', 0.0) or 0.0))) or 0.0)
            self._set_record_prediction_fields(
                identity,
                pred_steering=pred_steering,
                pred_throttle=pred_throttle,
                steering_diff=steering_diff,
                speed_diff=speed_diff,
            )
            updated_identities.append(identity)
        return updated_identities

    def deploy_model_to_visible_frames(self) -> None:
        self.preview_panel.stop_autoplay()
        visible_df = self.preview_panel.df.copy()
        if visible_df.empty:
            QMessageBox.information(self, 'Deploy Model', 'No visible frames. Load a session or loosen the filter first.')
            return

        try:
            result = run_model_deploy(
                visible_df,
                self.state.train_config,
                self.state.model,
                model_source=self.model_deploy_panel.model_source(),
                model_path=self.model_deploy_panel.model_path(),
                batch_size=self.model_deploy_panel.batch_size(),
                max_rows=self.model_deploy_panel.max_rows(),
            )
        except Exception as exc:
            QMessageBox.warning(self, 'Deploy Model', f'Model deploy failed:\n{exc}')
            self.main_window.set_status_message('Model deploy failed.')
            return

        deploy_rows = list(result.get('deploy_rows', []))
        if not deploy_rows:
            QMessageBox.information(self, 'Deploy Model', 'No model outputs were produced.')
            self.main_window.set_status_message('No model outputs were produced.')
            return

        updated_identities = self._merge_deploy_predictions(deploy_rows)
        first_identity = updated_identities[0] if updated_identities else None
        self.apply_preview_filter(select_identity=first_identity)
        source = str(result.get('model_source', self.model_deploy_panel.model_source()) or self.model_deploy_panel.model_source())
        self.main_window.set_status_message(f'Deployed {len(updated_identities)} frame(s) using {source}.')

    def sort_by_steering_diff(self) -> None:
        if not self.preview_panel.sort_by_column_desc('steering_diff'):
            QMessageBox.information(self, 'Sort Diff', 'Deploy a model first to show steering differences.')
            return
        self.main_window.set_status_message('Sorted by largest steering difference.')

    def sort_by_speed_diff(self) -> None:
        if not self.preview_panel.sort_by_column_desc('speed_diff'):
            QMessageBox.information(self, 'Sort Diff', 'Deploy a model first to show speed differences.')
            return
        self.main_window.set_status_message('Sorted by largest speed difference.')

    def apply_deployed_outputs_to_selected(self) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        eligible = [dict(record) for record in records if self._has_deployed_prediction(record)]
        if not eligible:
            QMessageBox.information(self, 'Apply AI Output', 'Select rows with deployed AI output first.')
            return
        if not self.model_deploy_panel.apply_confirmed():
            QMessageBox.information(self, 'Apply AI Output', 'Tick "Confirm Apply" before overwriting selected labels.')
            return

        confirm = QMessageBox.warning(
            self,
            'Apply AI Output?',
            f'This overwrites steering and speed labels for {len(eligible)} selected frame(s) using deployed AI output.\n\nContinue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message('Apply AI output cancelled.')
            return

        update_records: list[dict] = []
        for record in eligible:
            pred_steering = float(self._prediction_value(record, 'pred_steering') or 0.0)
            pred_throttle = float(self._prediction_value(record, 'pred_throttle') or 0.0)
            updated = dict(record)
            updated['steering'] = pred_steering
            updated['throttle'] = pred_throttle
            update_records.append(updated)

        result = update_frame_controls_many(self.state.records_root_path, update_records)
        matched_key_set = {tuple(key) for key in result.get('matched_keys', [])}
        updated_records = [
            record for record in update_records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]

        for record in updated_records:
            identity = self._record_identity(record)
            pred_steering = float(record.get('steering', 0.0) or 0.0)
            pred_throttle = float(record.get('throttle', 0.0) or 0.0)
            self._update_record_field_in_loaded_data(identity, 'steering', pred_steering)
            self._update_record_field_in_loaded_data(identity, 'throttle', pred_throttle)
            self._set_record_prediction_fields(
                identity,
                pred_steering=pred_steering,
                pred_throttle=pred_throttle,
                steering_diff=0.0,
                speed_diff=0.0,
            )

        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        first_identity = self._record_identity(updated_records[0]) if updated_records else None
        self.apply_preview_filter(select_identity=first_identity)
        self.main_window.on_dataset_loaded()

        failed_messages = list(result.get('failed_messages', []))
        updated_count = int(result.get('updated_count', 0) or 0)
        rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        if updated_count:
            self.main_window.set_status_message(
                f'Applied AI output to {updated_count} selected frame(s); {rows_changed} metadata row(s) changed.'
                + (f' {len(failed_messages)} failed.' if failed_messages else '')
            )
        else:
            self.main_window.set_status_message('No AI output was applied.')
        if failed_messages:
            QMessageBox.warning(self, 'Apply AI Output', '\n'.join(failed_messages[:8]))

    def schedule_plot_refresh_from_preview(self) -> None:
        self.single_edit_plot_timer.start()

    def refresh_plot_from_preview(self) -> None:
        if hasattr(self, 'plot_panel'):
            self.plot_panel.set_dataframe(self.preview_panel.df)

    def _single_edit_needs_filter_rebuild(self, *, steering: float, throttle: float) -> bool:
        if self.filter_panel.speed_filter_enabled():
            min_speed, max_speed = self.filter_panel.speed_range()
            if throttle < min_speed or throttle > max_speed:
                return True
        if self.filter_panel.steering_filter_enabled():
            min_steering, max_steering = self.filter_panel.steering_range()
            if steering < min_steering or steering > max_steering:
                return True
        return False

    def select_all_preview_frames_for_bulk_edit(self) -> None:
        selected = self.preview_panel.select_all_records()
        count = len(self.preview_panel.selected_records())
        self.bulk_edit_panel.set_selected_count(count)
        self.main_window.set_status_message(
            f'Selected all {count} visible frame(s) for bulk edit.' if selected else 'No visible frame rows to select for bulk edit.'
        )

    def _update_record_field_in_loaded_data(self, identity: tuple[str, str, str, str], field_name: str, value: float) -> None:
        for df_attr in ['dataset_df', 'filtered_df']:
            df = getattr(self.state, df_attr)
            if isinstance(df, pd.DataFrame) and not df.empty:
                mask = self._record_mask(df, identity)
                if len(mask) == len(df) and mask.any():
                    df.loc[mask, field_name] = float(value)
        if not self.current_preview_source_df.empty:
            mask = self._record_mask(self.current_preview_source_df, identity)
            if len(mask) == len(self.current_preview_source_df) and mask.any():
                self.current_preview_source_df.loc[mask, field_name] = float(value)

    def _update_records_field_in_loaded_data(self, identities: list[tuple[str, str, str, str]], field_name: str, value: float) -> None:
        identity_set = set(identities)
        if not identity_set:
            return

        def update_df(df: pd.DataFrame) -> None:
            if not isinstance(df, pd.DataFrame) or df.empty:
                return

            def column_text(column: str) -> pd.Series:
                return self._column_text(df, column)

            row_keys = zip(
                column_text('session'),
                column_text('frame_id'),
                column_text('ts'),
                column_text('abs_image'),
            )
            mask = pd.Series([key in identity_set for key in row_keys], index=df.index, dtype=bool)
            if mask.any():
                df.loc[mask, field_name] = float(value)

        for df_attr in ['dataset_df', 'filtered_df']:
            update_df(getattr(self.state, df_attr))
        update_df(self.current_preview_source_df)

    def apply_bulk_steering_edit(self, steering: float) -> None:
        self._apply_bulk_control_edit(field_name='steering', field_label='steering', value=float(steering))

    def apply_bulk_speed_edit(self, speed: float) -> None:
        self._apply_bulk_control_edit(field_name='throttle', field_label='speed', value=float(speed))

    def _apply_bulk_control_edit(self, *, field_name: str, field_label: str, value: float) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        if not records:
            QMessageBox.information(self, 'Bulk Edit', 'Select one or more rows first.')
            return
        if not self.bulk_edit_panel.bulk_edit_confirmed():
            QMessageBox.information(
                self,
                'Bulk Edit',
                'Tick "Confirm Overwrite" before bulk editing.',
            )
            return

        count = len(records)
        confirm = QMessageBox.warning(
            self,
            f'Confirm Bulk {field_label.title()} Edit',
            f'This will overwrite {field_label} for {count} selected frame(s) with {value:.3f}.\n\n'
            'The other control value stays unchanged. This cannot be undone in piTrainer. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message(f'Bulk {field_label} edit cancelled.')
            return

        result = update_frame_controls_batch(
            self.state.records_root_path,
            records,
            steering=value if field_name == 'steering' else 0.0,
            throttle=value if field_name == 'throttle' else 0.0,
            update_steering=(field_name == 'steering'),
            update_throttle=(field_name == 'throttle'),
        )

        matched_key_set = {tuple(key) for key in result.get('matched_keys', [])}
        updated_identities = [
            self._record_identity(record)
            for record in records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]
        if updated_identities:
            self._update_records_field_in_loaded_data(updated_identities, field_name, value)

        failed_messages = list(result.get('failed_messages', []))
        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        first_identity = updated_identities[0] if updated_identities else None
        self.apply_preview_filter(select_identity=first_identity)

        updated_count = int(result.get('updated_count', 0))
        rows_changed = int(result.get('metadata_rows_changed', 0))
        if updated_count:
            self.main_window.set_status_message(
                f'Updated {field_label} for {updated_count} selected frame(s) with {rows_changed} metadata row(s) changed.'
                + (f' {len(failed_messages)} failed.' if failed_messages else '')
            )
        if failed_messages:
            QMessageBox.warning(self, f'Bulk {field_label.title()} Edit', '\n'.join(failed_messages[:8]))

    def refresh_from_state(self) -> None:
        self.current_preview_source_df = self._review_dataframe(self.state.filtered_df)
        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        self.apply_preview_filter()

    def start_preview_playback(self) -> None:
        active = self.preview_panel.start_autoplay()
        self.main_window.set_status_message('Frame playback started.' if active else 'Need at least 2 visible frames to play.')

    def stop_preview_playback(self) -> None:
        self.preview_panel.stop_autoplay()
        self.main_window.set_status_message('Frame playback stopped.')

    def restart_preview_playback(self) -> None:
        active = self.preview_panel.restart_autoplay()
        self.main_window.set_status_message(
            'Frame playback restarted.' if active else 'Need at least 1 visible frame to restart.'
        )

    def on_playback_speed_changed(self, fps: float) -> None:
        self.preview_panel.set_playback_fps(fps)

    def on_playback_state_changed(self, state: dict[str, float | int | bool]) -> None:
        self.playback_panel.set_playback_active(bool(state.get('active', False)))
        self.playback_panel.set_frame_position(int(state.get('current_index', 0)), int(state.get('total', 0)))

    def _remove_identities_from_dataframe(self, df: pd.DataFrame, identities: list[tuple[str, str, str, str]]) -> pd.DataFrame:
        if df.empty or not identities:
            return df.copy()
        remove_mask = pd.Series([False] * len(df), index=df.index)
        for identity in identities:
            mask = self._record_mask(df, identity)
            if len(mask) == len(df):
                remove_mask |= mask
        return df[~remove_mask].copy().reset_index(drop=True)

    def _hide_records_from_loaded_data(self, identities: list[tuple[str, str, str, str]]) -> None:
        for df_attr in ['dataset_df', 'filtered_df', 'train_df', 'val_df']:
            df = getattr(self.state, df_attr)
            if isinstance(df, pd.DataFrame):
                setattr(self.state, df_attr, self._remove_identities_from_dataframe(df, identities))
        self.current_preview_source_df = self._remove_identities_from_dataframe(self.current_preview_source_df, identities)

    def _active_session_names_for_visibility_actions(self) -> list[str]:
        selected = [str(session).strip() for session in self.state.selected_sessions if str(session).strip()]
        if selected:
            return selected
        if not self.state.dataset_df.empty and 'session' in self.state.dataset_df.columns:
            names = self.state.dataset_df['session'].fillna('').astype(str).str.strip().tolist()
            return [name for index, name in enumerate(names) if name and name not in names[:index]]
        return []

    def _reload_loaded_sessions_after_visibility_change(self, status_message: str) -> None:
        sessions = self._active_session_names_for_visibility_actions()
        if sessions:
            self.state.selected_sessions = sessions
            self.session_source_panel.set_selected_sessions(sessions)
            self._load_sessions(sessions)
        else:
            self.refresh_from_state()
        self.image_preview_panel.clear_preview()
        self.bulk_edit_panel.set_selected_count(0)
        self.main_window.set_status_message(status_message)

    def recover_last_hidden_frames(self) -> None:
        self.preview_panel.stop_autoplay()
        sessions = self._active_session_names_for_visibility_actions()
        count = self.data_control_panel.recover_count()
        result = recover_hidden_frames(self.state.records_root_path, sessions, recover_all=False, count=count)
        recovered_count = int(result.get('recovered_count', 0) or 0)
        metadata_rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))

        if recovered_count:
            self._reload_loaded_sessions_after_visibility_change(
                f"Recovered {recovered_count} hidden frame(s) with {metadata_rows_changed} metadata row(s) changed."
            )
            return
        QMessageBox.information(self, 'Recover Frames', '\n'.join(failed_messages[:8]) if failed_messages else 'No hidden frames were recovered.')
        self.main_window.set_status_message('No hidden frames were recovered.')

    def recover_all_hidden_frames(self) -> None:
        self.preview_panel.stop_autoplay()
        sessions = self._active_session_names_for_visibility_actions()
        result = recover_hidden_frames(self.state.records_root_path, sessions, recover_all=True)
        recovered_count = int(result.get('recovered_count', 0) or 0)
        metadata_rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))

        if recovered_count:
            self._reload_loaded_sessions_after_visibility_change(
                f"Recovered all hidden frames: {recovered_count} frame(s), {metadata_rows_changed} metadata row(s) changed."
            )
            return
        QMessageBox.information(self, 'Recover All', '\n'.join(failed_messages[:8]) if failed_messages else 'No hidden frames were recovered.')
        self.main_window.set_status_message('No hidden frames were recovered.')

    def purge_hidden_frames_shortcut(self) -> None:
        self.preview_panel.stop_autoplay()
        sessions = self._active_session_names_for_visibility_actions()
        if not sessions:
            QMessageBox.information(self, 'Permanent Delete', 'Load or select a session first.')
            return

        confirm = QMessageBox.warning(
            self,
            'Delete Hidden Frames Permanently?',
            'This permanently deletes hidden rows and unreferenced image files from the loaded/selected sessions.\n\n'
            'This cannot be undone. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message('Permanent delete cancelled.')
            return

        result = purge_hidden_frames(self.state.records_root_path, sessions)
        purged_count = int(result.get('purged_count', 0) or 0)
        rows_removed = int(result.get('metadata_rows_removed', 0) or 0)
        image_files_deleted = int(result.get('image_files_deleted', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))
        skipped_files = list(result.get('skipped_files', []))

        if purged_count:
            self._reload_loaded_sessions_after_visibility_change(
                f"Permanent delete: {purged_count} hidden frame(s), {rows_removed} metadata row(s), {image_files_deleted} image file(s)."
            )
            if skipped_files:
                QMessageBox.information(
                    self,
                    'Permanent Delete',
                    'Delete finished, but some files were kept:\n' + '\n'.join(skipped_files[:8]),
                )
            return
        QMessageBox.information(self, 'Permanent Delete', '\n'.join(failed_messages[:8]) if failed_messages else 'No hidden frames were deleted permanently.')
        self.main_window.set_status_message('No hidden frames were deleted permanently.')

    def delete_selected_frame(self) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        if not records:
            QMessageBox.information(self, 'Hide Selected', 'Select one or more rows first.')
            return
        if not self.data_control_panel.deletion_confirmed():
            QMessageBox.information(
                self,
                'Hide Selected',
                'Tick "Confirm Hide" in 2 Hide & Recover before hiding frames. '
                'Images stay on disk.',
            )
            return

        identities = [self._record_identity(record) for record in records]
        result = hide_frames_from_training(self.state.records_root_path, records)
        hidden_count = int(result.get('hidden_count', 0) or 0)
        metadata_rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))

        if hidden_count:
            self._hide_records_from_loaded_data(identities)
            self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
            self.apply_preview_filter()
            self.image_preview_panel.clear_preview()
            self.bulk_edit_panel.set_selected_count(0)
            self.main_window.on_dataset_loaded()
            self.main_window.set_status_message(
                f"Hidden {hidden_count} selected frame(s) from training. "
                f"Changed {metadata_rows_changed} metadata row(s). Image files were kept."
                + (f" {len(failed_messages)} failed." if failed_messages else '')
            )
        if failed_messages:
            QMessageBox.warning(self, 'Hide Selected', '\n'.join(failed_messages[:8]))
