from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ..app_state import AppState
from ..panels.data.dataset_stats_panel import DatasetStatsPanel
from ..panels.data.image_preview_panel import ImagePreviewPanel
from ..panels.data.preview_panel import PreviewPanel
from ..panels.data.root_path_panel import RootPathPanel
from ..panels.data.session_list_panel import SessionListPanel
from ..services.data.record_loader_service import build_filtered_dataframe, load_records_dataframe
from ..services.data.session_service import list_sessions
from ..services.data.stats_service import calculate_basic_stats
from .dock_page import DockPage


class DataPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        super().__init__('data')

        self.root_path_panel = RootPathPanel(self.state, self.refresh_sessions)
        self.session_list_panel = SessionListPanel(self.state, self.load_selected_sessions)
        self.stats_panel = DatasetStatsPanel()
        self.image_preview_panel = ImagePreviewPanel()
        self.preview_panel = PreviewPanel(selection_callback=self.image_preview_panel.set_image_path)
        self.set_workspace_widget(self.preview_panel)
        self.build_default_layout()
        self.restore_layout()

    def build_default_layout(self) -> None:
        for dock in self.findChildren(QDockWidget):
            self.removeDockWidget(dock)
            dock.deleteLater()
        root_dock = self.add_panel('root_path', 'Records Root', self.root_path_panel, Qt.LeftDockWidgetArea)
        session_dock = self.add_panel('sessions', 'Sessions', self.session_list_panel, Qt.LeftDockWidgetArea)
        stats_dock = self.add_panel('stats', 'Dataset Stats', self.stats_panel, Qt.RightDockWidgetArea)
        image_dock = self.add_panel('image_preview', 'Image Preview', self.image_preview_panel, Qt.RightDockWidgetArea)
        self.splitDockWidget(root_dock, session_dock, Qt.Vertical)
        self.splitDockWidget(stats_dock, image_dock, Qt.Vertical)
        self.resizeDocks([root_dock, session_dock], [170, 560], Qt.Vertical)
        self.resizeDocks([stats_dock, image_dock], [180, 560], Qt.Vertical)
        self.resizeDocks([root_dock, stats_dock], [260, 360], Qt.Horizontal)

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

        stats = calculate_basic_stats(filtered)
        self.stats_panel.set_stats(stats)
        self.preview_panel.set_dataframe(filtered)
        if filtered.empty:
            self.image_preview_panel.clear_preview()
        self.main_window.on_dataset_loaded()
