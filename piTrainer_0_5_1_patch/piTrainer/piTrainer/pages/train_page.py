from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

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
from ..ui.layout_widgets import make_scrollable_stack, make_workflow_tabs


REQUIRED_TRAIN_COLUMNS = ("abs_image", "steering", "throttle")


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

        workflow_tabs = make_workflow_tabs([
            (
                '1 Setup',
                make_scrollable_stack([
                    ('Split Summary', self.split_summary_panel, True),
                    ('Training Controls', self.control_panel, True),
                ], object_name='trainSetupWorkflowScrollArea', intro='Prepare the split, start training, then watch the frame review and history/log tabs.'),
            ),
            (
                '2 Config',
                make_scrollable_stack([
                    ('Training Config', self.config_panel, False),
                ], object_name='trainConfigWorkflowScrollArea', intro='Change model and schedule settings here. Keep defaults unless you are intentionally experimenting.'),
            ),
        ], object_name='trainWorkflowTabs')

        progress_stack = make_workflow_tabs([
            ('History', self.history_panel, 'Training loss and metric curves.'),
            ('Log', self.log_panel, 'Detailed training messages and errors.'),
        ], object_name='trainProgressTabs')

        right_stack = self.make_vertical_splitter([
            self.make_panel_frame('review', 'Epoch Frame Review', self.epoch_review_panel),
            self.make_panel_frame('progress', 'Training History / Log', progress_stack),
        ], sizes=[640, 260], object_name='right_stack', stretch=[5, 2], minimums=[220, 140])

        workspace = self.make_horizontal_splitter([
            self.make_panel_frame('workflow_controls', 'Training Workflow', workflow_tabs),
            right_stack,
        ], sizes=[320, 1040], object_name='main_workspace', stretch=[1, 3], minimums=[260, 420])

        self.set_workspace_widget(
            workspace,
            step='3 of 5',
            title='Train',
            summary='Prepare the train/validation split, start model training, and watch epoch examples plus the live log.',
            next_step='Next: click the green Start Training button when the split summary looks correct.',
        )

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

    @staticmethod
    def _missing_training_columns(df: pd.DataFrame) -> list[str]:
        return [column for column in REQUIRED_TRAIN_COLUMNS if column not in df.columns]

    @staticmethod
    def _usable_training_rows(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        missing = TrainPage._missing_training_columns(df)
        if missing:
            return pd.DataFrame()
        cleaned = df.copy()
        cleaned['abs_image'] = cleaned['abs_image'].fillna('').astype(str)
        cleaned = cleaned[cleaned['abs_image'].str.len() > 0].copy()
        if cleaned.empty:
            return cleaned.reset_index(drop=True)
        exists_mask = cleaned['abs_image'].map(lambda value: Path(str(value)).exists())
        cleaned = cleaned[exists_mask].copy()
        if cleaned.empty:
            return cleaned.reset_index(drop=True)
        cleaned['steering'] = pd.to_numeric(cleaned['steering'], errors='coerce')
        cleaned['throttle'] = pd.to_numeric(cleaned['throttle'], errors='coerce')
        cleaned = cleaned[cleaned['steering'].notna() & cleaned['throttle'].notna()].copy()
        cleaned['steering'] = cleaned['steering'].clip(-1.0, 1.0).astype('float32')
        cleaned['throttle'] = cleaned['throttle'].clip(-1.0, 1.0).astype('float32')
        return cleaned.reset_index(drop=True)

    def _prepare_training_inputs(self) -> tuple[pd.DataFrame, pd.DataFrame] | None:
        if self.state.filtered_df.empty:
            self.log_panel.append_line('No active rows to train. Load sessions on the Data page first, or confirm a non-empty Preprocess result.')
            self.main_window.set_status_message('No training data loaded.')
            return None

        missing = self._missing_training_columns(self.state.filtered_df)
        if missing:
            self.log_panel.append_line('Cannot start training. Active dataset is missing required column(s): ' + ', '.join(missing))
            self.main_window.set_status_message('Training data is missing required columns.')
            return None

        # Always refresh the split at the moment training starts. This avoids stale
        # empty splits after loading new PiSD V7 sessions or confirming preprocessing.
        self.prepare_split()

        train_df = self._usable_training_rows(self.state.train_df)
        val_df = self._usable_training_rows(self.state.val_df)

        if train_df.empty and not self.state.train_df.empty:
            self.log_panel.append_line(
                'Prepared training rows exist, but none have readable image files and numeric steering/speed labels.'
            )
        if train_df.empty:
            active_rows = self._usable_training_rows(self.state.filtered_df)
            if not active_rows.empty:
                self.log_panel.append_line(
                    'Training split produced no usable train rows, so piTrainer will train from all active usable rows.'
                )
                train_df = active_rows
                val_df = pd.DataFrame(columns=active_rows.columns)

        if train_df.empty:
            self.log_panel.append_line(
                'Cannot start training. No usable rows remain after checking image paths, steering, and speed labels.'
            )
            self.main_window.set_status_message('No usable training rows.')
            return None

        dropped_train = len(self.state.train_df) - len(train_df)
        dropped_val = max(0, len(self.state.val_df) - len(val_df))
        if dropped_train > 0 or dropped_val > 0:
            self.log_panel.append_line(
                f'Skipped unusable rows before training: train={dropped_train}, val={dropped_val}. '
                'Rows are skipped when the image path is missing/unreadable or labels are not numeric.'
            )

        self.state.train_df = train_df
        self.state.val_df = val_df
        self.refresh_from_state()
        return train_df, val_df

    def start_training(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.log_panel.append_line('Training is already running.')
            return
        self.config_panel.push_to_state()

        prepared = self._prepare_training_inputs()
        if prepared is None:
            return
        train_df, val_df = prepared

        self.history_panel.clear_history()
        self.epoch_review_panel.clear_review()
        self.log_panel.append_line(
            f'Starting training worker with {len(train_df)} train row(s) and {len(val_df)} validation row(s)...'
        )
        self.control_panel.set_running(True)

        self.worker = TrainingWorker(train_df, val_df, self.state.train_config)
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
