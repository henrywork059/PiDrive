from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..app_state import AppState
from ..panels.data.dataset_stats_panel import DatasetStatsPanel
from ..panels.data.preview_panel import PreviewPanel
from ..panels.data.root_path_panel import RootPathPanel
from ..panels.data.session_list_panel import SessionListPanel
from ..services.data.record_loader_service import build_filtered_dataframe, load_records_dataframe
from ..services.data.session_service import list_sessions
from ..services.data.stats_service import calculate_basic_stats


class DataPage(QWidget):
    def __init__(self, state: AppState, main_window) -> None:
        super().__init__()
        self.state = state
        self.main_window = main_window

        self.root_path_panel = RootPathPanel(self.state, self.refresh_sessions)
        self.session_list_panel = SessionListPanel(self.state, self.load_selected_sessions)
        self.stats_panel = DatasetStatsPanel()
        self.preview_panel = PreviewPanel()

        left = QVBoxLayout()
        left.addWidget(self.root_path_panel)
        left.addWidget(self.session_list_panel, 1)

        right = QVBoxLayout()
        right.addWidget(self.stats_panel)
        right.addWidget(self.preview_panel, 1)

        layout = QHBoxLayout(self)
        layout.addLayout(left, 1)
        layout.addLayout(right, 2)

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
        self.main_window.on_dataset_loaded()
