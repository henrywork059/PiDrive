from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.train.split_summary_panel import SplitSummaryPanel
from ..panels.train.train_config_panel import TrainConfigPanel
from ..panels.train.train_control_panel import TrainControlPanel
from ..panels.train.train_epoch_review_panel import TrainEpochReviewPanel
from ..panels.train.train_history_panel import TrainHistoryPanel
from ..services.export.export_service import save_keras_model
from ..services.train.split_service import split_dataframe
from ..services.train.worker import TrainingWorker
from ..utils.path_utils import ensure_dir, safe_filename
from .dock_page import DockPage


class TrainPage(DockPage):
    def __init__(self, state: AppState, main_window) -> None:
        self.state = state
        self.main_window = main_window
        self.worker: TrainingWorker | None = None
        super().__init__('train')

        self.split_summary_panel = SplitSummaryPanel()
        self.config_panel = TrainConfigPanel(self.state)
        self.control_panel = TrainControlPanel(
            prepare_callback=self.prepare_split,
            start_callback=self.start_training,
            stop_callback=self.stop_training,
            save_model_callback=self.save_trained_model,
        )
        self.history_panel = TrainHistoryPanel()
        self.epoch_review_panel = TrainEpochReviewPanel()
        self.log_panel = LogPanel('Training Log')
        self.build_default_layout()
        self.restore_layout()

    def build_default_layout(self) -> None:
        self.clear_docks()
        summary_dock = self.add_panel('summary', 'Split Summary', self.split_summary_panel, Qt.LeftDockWidgetArea)
        config_dock = self.add_panel('config', 'Training Config', self.config_panel, Qt.LeftDockWidgetArea)
        control_dock = self.add_panel('control', 'Training Controls', self.control_panel, Qt.LeftDockWidgetArea)
        review_dock = self.add_panel('review', 'Epoch Frame Review', self.epoch_review_panel, Qt.RightDockWidgetArea)
        history_dock = self.add_panel('history', 'Training History', self.history_panel, Qt.RightDockWidgetArea)
        log_dock = self.add_panel('log', 'Training Log', self.log_panel, Qt.BottomDockWidgetArea)
        self.splitDockWidget(summary_dock, config_dock, Qt.Vertical)
        self.splitDockWidget(config_dock, control_dock, Qt.Vertical)
        self.splitDockWidget(summary_dock, review_dock, Qt.Horizontal)
        self.splitDockWidget(review_dock, history_dock, Qt.Vertical)
        self.splitDockWidget(history_dock, log_dock, Qt.Vertical)
        self.resizeDocks([summary_dock, config_dock, control_dock], [170, 430, 150], Qt.Vertical)
        self.resizeDocks([review_dock, history_dock, log_dock], [360, 230, 160], Qt.Vertical)
        self.resizeDocks([summary_dock, review_dock], [340, 780], Qt.Horizontal)

    def refresh_from_state(self) -> None:
        self.split_summary_panel.set_counts(
            total_rows=len(self.state.filtered_df),
            train_rows=len(self.state.train_df),
            val_rows=len(self.state.val_df),
            sessions=len(set(self.state.filtered_df.get('session', []))) if not self.state.filtered_df.empty else 0,
            model_ready=self.state.model is not None,
        )
        self.history_panel.set_history(self.state.history)

    def prepare_split(self) -> None:
        self.config_panel.push_to_state()
        train_df, val_df = split_dataframe(self.state.filtered_df, self.state.train_config)
        self.state.train_df = train_df
        self.state.val_df = val_df
        self.refresh_from_state()
        self.log_panel.append_line(
            f"Prepared split ({self.state.train_config.split_mode}): train={len(train_df)} rows, val={len(val_df)} rows."
        )
        self.main_window.set_status_message('Prepared training split.')

    def start_training(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.log_panel.append_line('Training is already running.')
            return
        self.config_panel.push_to_state()
        if self.state.filtered_df.empty:
            self.log_panel.append_line('No data loaded. Load sessions on the Data page first.')
            return
        if self.state.train_df.empty and self.state.val_df.empty:
            self.prepare_split()
        self.history_panel.clear_history()
        self.epoch_review_panel.clear_review()
        self.log_panel.append_line('Starting training worker...')
        self.control_panel.set_running(True)

        self.worker = TrainingWorker(self.state.train_df, self.state.val_df, self.state.train_config)
        self.worker.log_message.connect(self.log_panel.append_line)
        self.worker.progress_changed.connect(self.control_panel.set_progress)
        self.worker.epoch_metrics.connect(self.history_panel.append_epoch_metrics)
        self.worker.epoch_review.connect(self.epoch_review_panel.set_review)
        self.worker.error_message.connect(self._on_training_error)
        self.worker.training_finished.connect(self._on_training_finished)
        self.worker.start()

    def stop_training(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.log_panel.append_line('Stop requested. Training will stop after the current epoch.')

    def save_trained_model(self) -> None:
        if self.state.model is None:
            self.log_panel.append_line('No trained model available to save yet.')
            self.main_window.set_status_message('No trained model available to save.')
            return
        out_dir = ensure_dir(self.state.out_dir_path)
        base_name = safe_filename(self.state.export_config.base_name or 'picar_model', default='picar_model')
        candidate = out_dir / f'{base_name}_trained.keras'
        if candidate.exists():
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            candidate = out_dir / f'{base_name}_trained_{stamp}.keras'
        save_keras_model(self.state.model, candidate)
        self.state.last_saved_model_path = str(candidate)
        self.log_panel.append_line(f'Saved trained model: {candidate}')
        self.main_window.validation_page.config_panel.set_saved_model_path(str(candidate))
        self.main_window.validation_page.refresh_from_state()
        self.main_window.set_status_message('Saved trained model and linked it to Validation.')

    def _on_training_error(self, message: str) -> None:
        self.state.last_error = message
        self.control_panel.set_running(False)
        self.log_panel.append_line(f'ERROR: {message}')
        self.main_window.set_status_message('Training failed.')

    def _on_training_finished(self, model, history: dict) -> None:
        self.state.model = model
        self.state.history = history
        self.control_panel.set_running(False)
        self.control_panel.set_progress(100)
        self.history_panel.set_history(history)
        self.log_panel.append_line('Training finished successfully.')
        self.refresh_from_state()
        self.main_window.on_training_finished()

    def shutdown_worker(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(1500)
