from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMessageBox

from ..app_state import AppState
from ..panels.data.data_actions_panel import DataActionsPanel
from ..panels.data.data_control_panel import DataControlPanel
from ..panels.data.data_plot_panel import DataPlotPanel
from ..panels.data.dataset_stats_panel import DatasetStatsPanel
from ..panels.data.frame_filter_panel import FrameFilterPanel
from ..panels.data.image_preview_panel import ImagePreviewPanel
from ..panels.data.merge_sessions_panel import MergeSessionsPanel
from ..panels.data.overlay_control_panel import OverlayControlPanel
from ..panels.data.playback_control_panel import PlaybackControlPanel
from ..panels.data.preview_panel import PreviewPanel
from ..panels.data.root_path_panel import RootPathPanel
from ..panels.data.session_list_panel import SessionListPanel
from ..services.data.delete_service import delete_frame_from_session
from ..services.data.filter_service import filter_preview_dataframe
from ..services.data.merge_service import merge_sessions
from ..services.data.record_loader_service import build_filtered_dataframe, load_records_dataframe
from ..services.data.session_service import list_sessions
from ..services.data.stats_service import calculate_basic_stats
from .dock_page import DockPage


class DataPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.current_preview_source_df = pd.DataFrame()
        super().__init__('data')

        self.root_path_panel = RootPathPanel(self.state, self.refresh_sessions)
        self.session_list_panel = SessionListPanel(self.state, self.load_selected_sessions)
        self.merge_sessions_panel = MergeSessionsPanel(self.merge_selected_sessions)
        self.filter_panel = FrameFilterPanel(self.apply_preview_filter, self.clear_preview_filter)
        self.overlay_panel = OverlayControlPanel(self.on_overlay_options_changed)
        self.stats_panel = DatasetStatsPanel()
        self.image_preview_panel = ImagePreviewPanel()
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
        self.data_actions_panel = DataActionsPanel(
            refresh_callback=self.refresh_sessions,
            load_callback=self.load_selected_sessions,
            clear_filter_callback=self.clear_preview_filter,
            shortcuts_callback=self.main_window.show_shortcuts,
        )
        self.data_control_panel = DataControlPanel(delete_frame_callback=self.delete_selected_frame)
        self.build_default_layout()
        self.restore_layout()
        self.preview_panel.set_playback_fps(self.playback_panel.playback_fps())

    def build_default_layout(self) -> None:
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()

        root_dock = self.add_panel('root_path', 'Records Root', self.root_path_panel, Qt.LeftDockWidgetArea)
        session_dock = self.add_panel('sessions', 'Sessions', self.session_list_panel, Qt.LeftDockWidgetArea)
        merge_dock = self.add_panel('merge_sessions', 'Merge Sessions', self.merge_sessions_panel, Qt.LeftDockWidgetArea)
        filter_dock = self.add_panel('frame_filter', 'Frame Filter', self.filter_panel, Qt.LeftDockWidgetArea)
        overlay_dock = self.add_panel('overlay_controls', 'Overlay Controls', self.overlay_panel, Qt.LeftDockWidgetArea)
        playback_dock = self.add_panel('playback_control', 'Playback Control', self.playback_panel, Qt.LeftDockWidgetArea)
        action_dock = self.add_panel('data_actions', 'Data Actions', self.data_actions_panel, Qt.LeftDockWidgetArea)
        control_dock = self.add_panel('data_control', 'Data Control', self.data_control_panel, Qt.LeftDockWidgetArea)
        preview_dock = self.add_panel('record_preview', 'Record Preview', self.preview_panel, Qt.RightDockWidgetArea)
        image_dock = self.add_panel('image_preview', 'Image Preview', self.image_preview_panel, Qt.RightDockWidgetArea)
        plot_dock = self.add_panel('data_plot', 'Data Plot', self.plot_panel, Qt.RightDockWidgetArea)
        stats_dock = self.add_panel('stats', 'Dataset Stats', self.stats_panel, Qt.RightDockWidgetArea)

        self.splitDockWidget(root_dock, session_dock, Qt.Vertical)
        self.splitDockWidget(session_dock, merge_dock, Qt.Vertical)
        self.splitDockWidget(merge_dock, filter_dock, Qt.Vertical)
        self.splitDockWidget(filter_dock, overlay_dock, Qt.Vertical)
        self.splitDockWidget(overlay_dock, playback_dock, Qt.Vertical)
        self.splitDockWidget(playback_dock, action_dock, Qt.Vertical)
        self.splitDockWidget(action_dock, control_dock, Qt.Vertical)

        self.splitDockWidget(root_dock, preview_dock, Qt.Horizontal)
        self.splitDockWidget(preview_dock, image_dock, Qt.Horizontal)
        self.splitDockWidget(image_dock, plot_dock, Qt.Vertical)
        self.splitDockWidget(plot_dock, stats_dock, Qt.Vertical)

        self.resizeDocks(
            [root_dock, session_dock, merge_dock, filter_dock, overlay_dock, playback_dock, action_dock, control_dock],
            [110, 280, 150, 230, 170, 150, 130, 100],
            Qt.Vertical,
        )
        self.resizeDocks([image_dock, plot_dock, stats_dock], [360, 300, 180], Qt.Vertical)
        self.resizeDocks([root_dock, preview_dock, image_dock], [300, 560, 380], Qt.Horizontal)

    def refresh_sessions(self) -> None:
        self.state.available_sessions = list_sessions(self.state.records_root_path)
        self.session_list_panel.set_sessions(self.state.available_sessions)
        self.main_window.set_status_message(
            f"Found {len(self.state.available_sessions)} session(s) under {self.state.records_root_path}."
        )

    def load_selected_sessions(self) -> None:
        selected = self.session_list_panel.selected_sessions()
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

    def merge_selected_sessions(self) -> None:
        selected = self.session_list_panel.selected_sessions()
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
            f"\n\nSource sessions: {', '.join(selected)}"
            f"\nTarget session: {merged_name}",
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
            self.session_list_panel.set_selected_sessions([target_session])
            self._load_sessions([target_session])
        else:
            self.session_list_panel.set_selected_sessions(selected)
            self.main_window.set_status_message(message)

        QMessageBox.information(self, 'Merge Sessions', message)

    def apply_preview_filter(self) -> None:
        filtered_preview = filter_preview_dataframe(
            self.current_preview_source_df,
            text=self.filter_panel.filter_text(),
            mode=self.filter_panel.selected_mode(),
            speed_range=self.filter_panel.speed_range() if self.filter_panel.speed_filter_enabled() else None,
            steering_range=self.filter_panel.steering_range() if self.filter_panel.steering_filter_enabled() else None,
        )
        self.preview_panel.set_dataframe(filtered_preview)
        self.plot_panel.set_dataframe(filtered_preview)
        if filtered_preview.empty:
            self.image_preview_panel.clear_preview()
        self.main_window.set_status_message(f'Showing {len(filtered_preview)} preview frame(s).')

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
        if not record:
            self.image_preview_panel.clear_preview()
            return
        self.image_preview_panel.set_record(record)

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
        record = self.preview_panel.selected_record()
        if not record:
            QMessageBox.information(self, 'Delete Selected Frame', 'Select one frame from Record Preview first.')
            return

        session_name = str(record.get('session', ''))
        frame_id = str(record.get('frame_id', ''))
        image_path = str(record.get('abs_image', ''))
        ts = str(record.get('ts', ''))
        confirm = QMessageBox.question(
            self,
            'Delete Selected Frame',
            f"Delete frame '{frame_id}' from session '{session_name}'? This removes the JSONL row and image file.",
        )
        if confirm != QMessageBox.Yes:
            return

        ok, message = delete_frame_from_session(
            self.state.records_root_path,
            session_name=session_name,
            frame_id=frame_id,
            image_path=image_path,
            ts=ts,
        )
        if ok:
            self.load_selected_sessions()
            self.main_window.set_status_message(message)
            QMessageBox.information(self, 'Delete Selected Frame', message)
        else:
            QMessageBox.warning(self, 'Delete Selected Frame', message)
