from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMessageBox

from ..app_state import AppState
from ..panels.data.data_control_panel import DataControlPanel
from ..panels.data.dataset_stats_panel import DatasetStatsPanel
from ..panels.data.frame_filter_panel import FrameFilterPanel
from ..panels.data.image_preview_panel import ImagePreviewPanel
from ..panels.data.preview_panel import PreviewPanel
from ..panels.data.root_path_panel import RootPathPanel
from ..panels.data.session_list_panel import SessionListPanel
from ..services.data.delete_service import delete_frame_from_session
from ..services.data.filter_service import filter_preview_dataframe
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
        self.filter_panel = FrameFilterPanel(self.apply_preview_filter, self.clear_preview_filter)
        self.stats_panel = DatasetStatsPanel()
        self.image_preview_panel = ImagePreviewPanel()
        self.preview_panel = PreviewPanel(selection_callback=self.image_preview_panel.set_image_path)
        self.data_control_panel = DataControlPanel(
            delete_frame_callback=self.delete_selected_frame,
            shortcuts_callback=self.main_window.show_shortcuts,
            autoplay_callback=self.toggle_autoplay,
        )
        self.set_workspace_widget(self.preview_panel)
        self.build_default_layout()
        self.restore_layout()

    def build_default_layout(self) -> None:
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()
        root_dock = self.add_panel('root_path', 'Records Root', self.root_path_panel, Qt.LeftDockWidgetArea)
        session_dock = self.add_panel('sessions', 'Sessions', self.session_list_panel, Qt.LeftDockWidgetArea)
        filter_dock = self.add_panel('frame_filter', 'Frame Filter', self.filter_panel, Qt.LeftDockWidgetArea)
        control_dock = self.add_panel('data_control', 'Data Control', self.data_control_panel, Qt.LeftDockWidgetArea)
        stats_dock = self.add_panel('stats', 'Dataset Stats', self.stats_panel, Qt.RightDockWidgetArea)
        image_dock = self.add_panel('image_preview', 'Image Preview', self.image_preview_panel, Qt.RightDockWidgetArea)
        self.splitDockWidget(root_dock, session_dock, Qt.Vertical)
        self.splitDockWidget(session_dock, filter_dock, Qt.Vertical)
        self.splitDockWidget(filter_dock, control_dock, Qt.Vertical)
        self.splitDockWidget(stats_dock, image_dock, Qt.Vertical)
        self.resizeDocks([root_dock, session_dock, filter_dock, control_dock], [130, 360, 170, 150], Qt.Vertical)
        self.resizeDocks([stats_dock, image_dock], [180, 560], Qt.Vertical)
        self.resizeDocks([root_dock, stats_dock], [320, 360], Qt.Horizontal)

    def refresh_sessions(self) -> None:
        self.state.available_sessions = list_sessions(self.state.records_root_path)
        self.session_list_panel.set_sessions(self.state.available_sessions)
        self.main_window.set_status_message(
            f"Found {len(self.state.available_sessions)} session(s) under {self.state.records_root_path}."
        )

    def load_selected_sessions(self) -> None:
        selected = self.session_list_panel.selected_sessions()
        self.state.selected_sessions = selected
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

    def apply_preview_filter(self) -> None:
        filtered_preview = filter_preview_dataframe(
            self.current_preview_source_df,
            text=self.filter_panel.filter_text(),
            mode=self.filter_panel.selected_mode(),
        )
        self.preview_panel.set_dataframe(filtered_preview)
        if filtered_preview.empty:
            self.image_preview_panel.clear_preview()
        self.main_window.set_status_message(f"Showing {len(filtered_preview)} preview frame(s).")

    def clear_preview_filter(self) -> None:
        self.filter_panel.reset()
        self.apply_preview_filter()

    def toggle_autoplay(self) -> None:
        active = self.preview_panel.toggle_autoplay()
        self.data_control_panel.set_autoplay_active(active)
        self.main_window.set_status_message('Frame autoplay started.' if active else 'Frame autoplay stopped.')

    def delete_selected_frame(self) -> None:
        self.preview_panel.stop_autoplay()
        self.data_control_panel.set_autoplay_active(False)
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
