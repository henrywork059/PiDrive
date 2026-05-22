from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from ..app_state import AppState
from ..panels.data.bulk_edit_panel import BulkEditPanel
from ..panels.data.data_control_panel import DataControlPanel
from ..panels.data.data_plot_panel import DataPlotPanel
from ..panels.data.dataset_stats_panel import DatasetStatsPanel
from ..panels.data.frame_filter_panel import FrameFilterPanel
from ..panels.data.image_preview_panel import ImagePreviewPanel
from ..panels.data.merge_sessions_panel import MergeSessionsPanel
from ..panels.data.overlay_control_panel import OverlayControlPanel
from ..panels.data.playback_control_panel import PlaybackControlPanel
from ..panels.data.preview_panel import PreviewPanel
from ..panels.data.session_source_panel import SessionSourcePanel
from ..services.data.delete_service import delete_frame_from_session
from ..services.data.edit_service import update_frame_controls
from ..services.data.filter_service import filter_preview_dataframe
from ..services.data.merge_service import merge_sessions
from ..services.data.record_loader_service import build_filtered_dataframe, load_records_dataframe
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
        super().__init__('data')

        self.session_source_panel = SessionSourcePanel(self.state, self.refresh_sessions, self.load_selected_sessions)
        self.session_list_panel = self.session_source_panel
        self.bulk_edit_panel = BulkEditPanel(
            apply_steering_callback=self.apply_bulk_steering_edit,
            apply_speed_callback=self.apply_bulk_speed_edit,
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
        self.playback_panel = PlaybackControlPanel(
            play_callback=self.start_preview_playback,
            stop_callback=self.stop_preview_playback,
            restart_callback=self.restart_preview_playback,
            speed_change_callback=self.on_playback_speed_changed,
        )
        self.plot_panel = DataPlotPanel()
        self.data_control_panel = DataControlPanel(delete_frame_callback=self.delete_selected_frame)
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
                ], object_name='dataLoadWorkflowScrollArea', intro='Start here: choose a PiSD/piTrainer records root, scan sessions, select sessions, then load them.'),
            ),
            (
                '2 Manage',
                make_scrollable_stack([
                    ('Data Control', self.data_control_panel, True),
                    ('Frame Filter', self.filter_panel, True),
                ], object_name='dataManageWorkflowScrollArea', intro='Manage the loaded dataset: confirm delete actions once, delete selected frame rows, and filter frames before review or training.'),
            ),
            (
                '3 Review',
                make_scrollable_stack([
                    ('Bulk Edit Selected Frames', self.bulk_edit_panel, True, 'Apply one steering or speed value to selected Record Preview rows after confirmation.'),
                    ('Merge Sessions', self.merge_sessions_panel, False),
                    ('Overlay Controls', self.overlay_panel, False),
                ], object_name='dataReviewWorkflowScrollArea', intro='Review loaded sessions and overlays. Use Bulk Edit only when selected frame labels should be changed together; Merge Sessions stays collapsed by default.'),
            ),
        ], object_name='dataWorkflowTabs')

        review_tabs = make_workflow_tabs([
            (
                '1 Records',
                self.preview_panel,
                'Switch here to inspect, multi-select, and delete labelled frame rows.',
            ),
            (
                '2 Stats',
                self.stats_panel,
                'Switch here to check the loaded dataset summary.',
            ),
            (
                '3 Plot',
                self.plot_panel,
                'Switch here to review steering, speed, mode, and session distributions.',
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
            self.make_panel_frame('image_preview', 'Image Preview + Playback + V7 Overlay', visual_review),
        ], object_name='main_workspace', **splitter_args('three_panel_workspace'))

        self.set_workspace_widget(
            workspace,
            step='1 of 5',
            title='Data',
            summary='Load sessions, manage bad frames, review labels, and confirm the V7 overlay before preparing a dataset.',
            next_step='Load Selected',
            next_callback=lambda: self.reveal_widget(
                self.session_source_panel.load_btn,
                message='Focused the green Load Selected button.'
            ),
            next_tooltip='Click to focus the green Load Selected button in Data Workflow > 1 Load > Session Source.',
        )

    @staticmethod
    def _record_identity(record) -> tuple[str, str, str, str]:
        return PreviewPanel.record_identity(record)

    @staticmethod
    def _record_mask(df: pd.DataFrame, identity: tuple[str, str, str, str]):
        if df.empty:
            return pd.Series([], dtype=bool)

        def column_text(column: str) -> pd.Series:
            if column in df.columns:
                return df[column].fillna('').astype(str)
            return pd.Series([''] * len(df), index=df.index, dtype=str)

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
        self.current_preview_source_df = filtered.copy()

        stats = calculate_basic_stats(filtered)
        self.stats_panel.set_stats(stats)
        self.apply_preview_filter()
        self.main_window.on_dataset_loaded()

    def focus_record(self, record: dict | None) -> bool:
        if not record:
            return False
        session = str(record.get('session', '')).strip()
        if not session:
            return False

        current_sessions = set(self.state.dataset_df.get('session', pd.Series(dtype=str)).astype(str).tolist()) if not self.state.dataset_df.empty else set()
        need_reload = session not in current_sessions
        self.state.selected_sessions = [session]
        self.session_source_panel.set_selected_sessions([session])
        if need_reload:
            self._load_sessions([session])

        identity = self._record_identity(record)
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
            'Create a new merged session by copying records and images from the selected sessions?'
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
        if not record:
            self.image_preview_panel.clear_preview()
            return
        self.image_preview_panel.set_record(record)

    def on_image_record_edited(self, record: dict) -> None:
        if not record:
            return
        self.preview_panel.stop_autoplay()
        identity = self._record_identity(record)
        steering = float(record.get('steering', 0.0) or 0.0)
        throttle = float(record.get('throttle', 0.0) or 0.0)

        ok, message = update_frame_controls(
            self.state.records_root_path,
            session_name=str(record.get('session', '')),
            frame_id=str(record.get('frame_id', '')),
            image_path=str(record.get('abs_image', '')),
            ts=str(record.get('ts', '')),
            steering=steering,
            throttle=throttle,
        )
        if not ok:
            self.main_window.set_status_message(message)
            return

        for df_attr in ['dataset_df', 'filtered_df']:
            df = getattr(self.state, df_attr)
            if isinstance(df, pd.DataFrame) and not df.empty:
                mask = self._record_mask(df, identity)
                if len(mask) == len(df) and mask.any():
                    df.loc[mask, 'steering'] = steering
                    df.loc[mask, 'throttle'] = throttle
        if not self.current_preview_source_df.empty:
            mask = self._record_mask(self.current_preview_source_df, identity)
            if len(mask) == len(self.current_preview_source_df) and mask.any():
                self.current_preview_source_df.loc[mask, 'steering'] = steering
                self.current_preview_source_df.loc[mask, 'throttle'] = throttle

        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        self.apply_preview_filter(select_identity=identity)
        self.main_window.set_status_message(message)



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

    def apply_bulk_steering_edit(self, steering: float) -> None:
        self._apply_bulk_control_edit(field_name='steering', field_label='steering', value=float(steering))

    def apply_bulk_speed_edit(self, speed: float) -> None:
        self._apply_bulk_control_edit(field_name='throttle', field_label='speed', value=float(speed))

    def _apply_bulk_control_edit(self, *, field_name: str, field_label: str, value: float) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        if not records:
            QMessageBox.information(self, 'Bulk Edit Selected Frames', 'Select one or more frame rows from Record Preview first.')
            return
        if not self.bulk_edit_panel.bulk_edit_confirmed():
            QMessageBox.information(
                self,
                'Bulk Edit Selected Frames',
                'Tick "I understand this will overwrite selected frame labels" before applying a bulk edit.',
            )
            return

        count = len(records)
        confirm = QMessageBox.warning(
            self,
            f'Confirm Bulk {field_label.title()} Edit',
            f'This will overwrite {field_label} for {count} selected frame(s) with {value:.3f}.\n\n'
            'Only this field will be changed. The other control value will be kept from each existing row.\n'
            'This writes to session labels.jsonl/records.jsonl and is not automatically undoable. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message(f'Bulk {field_label} edit cancelled.')
            return

        updated_identities: list[tuple[str, str, str, str]] = []
        failed_messages: list[str] = []
        for record in records:
            identity = self._record_identity(record)
            current_steering = float(record.get('steering', 0.0) or 0.0)
            current_speed = float(record.get('throttle', 0.0) or 0.0)
            steering = value if field_name == 'steering' else current_steering
            speed = value if field_name == 'throttle' else current_speed
            ok, message = update_frame_controls(
                self.state.records_root_path,
                session_name=str(record.get('session', '')),
                frame_id=str(record.get('frame_id', '')),
                image_path=str(record.get('abs_image', '')),
                ts=str(record.get('ts', '')),
                steering=steering,
                throttle=speed,
                update_steering=(field_name == 'steering'),
                update_throttle=(field_name == 'throttle'),
            )
            if ok:
                updated_identities.append(identity)
                self._update_record_field_in_loaded_data(identity, field_name, value)
            else:
                failed_messages.append(message)

        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        first_identity = updated_identities[0] if updated_identities else None
        self.apply_preview_filter(select_identity=first_identity)

        if updated_identities:
            self.main_window.set_status_message(
                f'Updated {field_label} for {len(updated_identities)} selected frame(s).'
                + (f' {len(failed_messages)} failed.' if failed_messages else '')
            )
        if failed_messages:
            QMessageBox.warning(self, f'Bulk {field_label.title()} Edit', '\n'.join(failed_messages[:8]))

    def refresh_from_state(self) -> None:
        self.current_preview_source_df = self.state.filtered_df.copy()
        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        self.apply_preview_filter()

    def start_preview_playback(self) -> None:
        active = self.preview_panel.start_autoplay()
        self.main_window.set_status_message('Frame playback started.' if active else 'Need at least 2 filtered frames to play.')

    def stop_preview_playback(self) -> None:
        self.preview_panel.stop_autoplay()
        self.main_window.set_status_message('Frame playback stopped.')

    def restart_preview_playback(self) -> None:
        active = self.preview_panel.restart_autoplay()
        self.main_window.set_status_message(
            'Frame playback restarted.' if active else 'Need at least 1 filtered frame to restart.'
        )

    def on_playback_speed_changed(self, fps: float) -> None:
        self.preview_panel.set_playback_fps(fps)

    def on_playback_state_changed(self, state: dict[str, float | int | bool]) -> None:
        self.playback_panel.set_playback_active(bool(state.get('active', False)))
        self.playback_panel.set_frame_position(int(state.get('current_index', 0)), int(state.get('total', 0)))

    def delete_selected_frame(self) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        if not records:
            QMessageBox.information(self, 'Delete Selected Frame(s)', 'Select one or more frame rows from Record Preview first.')
            return
        if not self.data_control_panel.deletion_confirmed():
            QMessageBox.information(
                self,
                'Delete Selected Frame(s)',
                'Tick "I confirm frame delete actions" in Data Workflow > 2 Manage > Data Control before deleting. '
                'After it is ticked, Delete will not open this confirmation popup each time.',
            )
            return

        deleted_messages: list[str] = []
        failed_messages: list[str] = []
        for record in records:
            session_name = str(record.get('session', ''))
            frame_id = str(record.get('frame_id', ''))
            image_path = str(record.get('abs_image', ''))
            ts = str(record.get('ts', ''))
            ok, message = delete_frame_from_session(
                self.state.records_root_path,
                session_name=session_name,
                frame_id=frame_id,
                image_path=image_path,
                ts=ts,
            )
            if ok:
                deleted_messages.append(message)
            else:
                failed_messages.append(message)

        if deleted_messages:
            self.load_selected_sessions()
            self.main_window.set_status_message(
                f"Deleted {len(deleted_messages)} selected frame(s)."
                + (f" {len(failed_messages)} failed." if failed_messages else '')
            )
        if failed_messages:
            QMessageBox.warning(self, 'Delete Selected Frame(s)', '\n'.join(failed_messages[:8]))
