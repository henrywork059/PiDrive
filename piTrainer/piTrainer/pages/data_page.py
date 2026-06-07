from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

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
from ..ui.formatting import get_density_profile, splitter_args
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs
from .data_page_deploy import DataPageDeployMixin
from .data_page_filter_edit import DataPageFilterEditMixin
from .data_page_playback import DataPagePlaybackMixin
from .data_page_sessions import DataPageSessionMixin
from .data_page_support import DataPageSupportMixin
from .data_page_visibility import DataPageVisibilityMixin
from .dock_page import DockPage


class DataPage(
    DataPageSessionMixin,
    DataPageFilterEditMixin,
    DataPageDeployMixin,
    DataPagePlaybackMixin,
    DataPageVisibilityMixin,
    DataPageSupportMixin,
    DockPage,
):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.current_preview_source_df = pd.DataFrame()
        self.last_focus_redirected_to_source = False
        self.last_focus_source_frame_id = ''
        super().__init__('data')

        self.session_source_panel = SessionSourcePanel(
            self.state,
            self.refresh_sessions,
            self.load_selected_sessions,
            self.on_session_selection_changed,
        )
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
                '4 Review',
                make_scrollable_stack([
                    ('Bulk Edit', self.bulk_edit_panel, True, 'Overwrite steering or speed for selected rows.'),
                    ('Merge Sessions', self.merge_sessions_panel, False),
                    ('Overlays', self.overlay_panel, False),
                ], object_name='dataReviewWorkflowScrollArea', intro='Edit labels, merge sessions, and check overlays.'),
            ),
            (
                '5 Deploy',
                make_scrollable_stack([
                    ('Model Deploy', self.model_deploy_panel, True),
                ], object_name='dataDeployWorkflowScrollArea', intro='Run model output on visible frames and compare labels.'),
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
            summary='Load sessions, hide/recover rows, filter, review labels, deploy models, and check overlays.',
            next_step='Load Selected',
            next_callback=lambda: self.reveal_widget(
                self.session_source_panel.load_btn,
                message='Focused the green Load Selected button.'
            ),
            next_tooltip='Focus Load Selected in 1 Load.',
        )
