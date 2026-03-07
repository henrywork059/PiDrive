from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Signal

from ...app_state import TrainConfig
from .dataset_service import make_tf_dataset
from .model_service import build_model, compile_model


class TrainingWorker(QThread):
    log_message = Signal(str)
    progress_changed = Signal(int)
    epoch_metrics = Signal(dict)
    epoch_review = Signal(dict)
    error_message = Signal(str)
    training_finished = Signal(object, dict)

    def __init__(self, train_df, val_df, config: TrainConfig) -> None:
        super().__init__()
        self.train_df = train_df.copy()
        self.val_df = val_df.copy()
        self.config = TrainConfig(**vars(config))
        self._stop_requested = False
        self._review_rows = None
        self._review_x = None

    def request_stop(self) -> None:
        self._stop_requested = True

    def _prepare_review_batch(self):
        if self.train_df.empty or 'abs_image' not in self.train_df.columns:
            self._review_rows = None
            self._review_x = None
            return
        review_df = self.train_df[self.train_df['abs_image'].astype(str).map(lambda p: Path(p).exists())].copy().reset_index(drop=True)
        if review_df.empty:
            self._review_rows = None
            self._review_x = None
            return
        sample_size = min(24, len(review_df))
        if len(review_df) > sample_size:
            review_df = review_df.sample(n=sample_size, random_state=int(getattr(self.config, 'seed', 42) or 42)).reset_index(drop=True)
        from PIL import Image

        images = []
        for path in review_df['abs_image'].astype(str):
            with Image.open(path) as image:
                image = image.convert('RGB').resize((self.config.img_w, self.config.img_h))
                arr = np.asarray(image, dtype=np.float32) / 255.0
                images.append(arr)
        self._review_rows = review_df
        self._review_x = np.stack(images, axis=0) if images else None

    def _build_epoch_review_payload(self, model, epoch: int) -> dict | None:
        if self._review_rows is None or self._review_x is None or len(self._review_rows) == 0:
            return None
        predictions = model.predict(self._review_x, batch_size=min(16, len(self._review_rows)), verbose=0)
        if isinstance(predictions, dict):
            steering_pred = np.asarray(predictions.get('steering')).reshape(-1)
            throttle_pred = np.asarray(predictions.get('throttle')).reshape(-1)
        else:
            steering_pred = np.asarray(predictions[0]).reshape(-1)
            throttle_pred = np.asarray(predictions[1]).reshape(-1)
        steering_true = self._review_rows['steering'].astype(float).to_numpy(np.float32)
        throttle_true = self._review_rows['throttle'].astype(float).to_numpy(np.float32)
        combined_error = np.abs(steering_pred - steering_true) + np.abs(throttle_pred - throttle_true)
        best_idx = int(np.argmin(combined_error))
        worst_idx = int(np.argmax(combined_error))

        def build_item(idx: int) -> dict:
            row = self._review_rows.iloc[idx]
            return {
                'session': str(row.get('session', '')),
                'frame_id': str(row.get('frame_id', '')),
                'abs_image': str(row.get('abs_image', '')),
                'steering_true': float(steering_true[idx]),
                'steering_pred': float(steering_pred[idx]),
                'throttle_true': float(throttle_true[idx]),
                'throttle_pred': float(throttle_pred[idx]),
                'combined_error': float(combined_error[idx]),
            }

        return {'epoch': int(epoch), 'best': build_item(best_idx), 'worst': build_item(worst_idx)}

    def run(self) -> None:
        try:
            import tensorflow as tf
        except Exception as exc:
            self.error_message.emit(f"TensorFlow import failed: {exc}")
            return

        try:
            if self.train_df.empty:
                raise RuntimeError("Training dataframe is empty.")

            seed = int(getattr(self.config, 'seed', 42) or 42)
            random.seed(seed); np.random.seed(seed); tf.keras.utils.set_random_seed(seed)
            self.log_message.emit(f'Set training random seed to {seed}.')

            self.log_message.emit("Building TensorFlow datasets...")
            train_ds = make_tf_dataset(self.train_df, img_h=self.config.img_h, img_w=self.config.img_w, batch_size=self.config.batch_size, shuffle=self.config.shuffle, augment=self.config.augment)
            val_ds = None
            if not self.val_df.empty:
                val_ds = make_tf_dataset(self.val_df, img_h=self.config.img_h, img_w=self.config.img_w, batch_size=self.config.batch_size, shuffle=False, augment=False)

            self._prepare_review_batch()
            if self._review_rows is not None:
                self.log_message.emit(f'Prepared {len(self._review_rows)} review frame(s) for epoch best/worst inspection.')

            self.log_message.emit(f"Building model ({self.config.model_size})...")
            model = build_model(self.config.img_h, self.config.img_w, self.config.model_size, float(getattr(self.config, 'dropout_rate', 0.2) or 0.2))
            model = compile_model(model, self.config.learning_rate, float(getattr(self.config, 'steering_loss_weight', 1.0) or 1.0), float(getattr(self.config, 'throttle_loss_weight', 1.0) or 1.0))

            worker = self
            monitor = 'val_loss' if val_ds is not None else 'loss'

            class EpochCallback(tf.keras.callbacks.Callback):
                def on_epoch_end(self, epoch, logs=None):
                    logs = logs or {}
                    payload = {"epoch": int(epoch) + 1}
                    for key, value in logs.items():
                        try:
                            payload[key] = float(value)
                        except Exception:
                            continue
                    worker.epoch_metrics.emit(payload)
                    progress = int(((epoch + 1) / max(1, worker.config.epochs)) * 100)
                    worker.progress_changed.emit(progress)
                    worker.log_message.emit(
                        "Epoch " f"{epoch + 1}/{worker.config.epochs} — " + ", ".join(f"{k}={v:.5f}" for k, v in payload.items() if k != "epoch")
                    )
                    review_payload = worker._build_epoch_review_payload(self.model, int(epoch) + 1)
                    if review_payload is not None:
                        worker.epoch_review.emit(review_payload)
                    if worker._stop_requested:
                        self.model.stop_training = True

            callbacks = [EpochCallback()]
            if getattr(self.config, 'early_stopping', False):
                callbacks.append(tf.keras.callbacks.EarlyStopping(monitor=monitor, patience=max(1, int(getattr(self.config, 'early_stopping_patience', 4) or 4)), restore_best_weights=True))
                self.log_message.emit(f'Enabled early stopping on {monitor} with patience {max(1, int(getattr(self.config, "early_stopping_patience", 4) or 4))}.')
            if getattr(self.config, 'reduce_lr_on_plateau', False):
                callbacks.append(tf.keras.callbacks.ReduceLROnPlateau(monitor=monitor, patience=max(1, int(getattr(self.config, 'reduce_lr_patience', 2) or 2)), factor=float(getattr(self.config, 'reduce_lr_factor', 0.5) or 0.5), min_lr=1e-6, verbose=0))
                self.log_message.emit(f'Enabled reduce-on-plateau on {monitor} with patience {max(1, int(getattr(self.config, "reduce_lr_patience", 2) or 2))} and factor {float(getattr(self.config, "reduce_lr_factor", 0.5) or 0.5):.2f}.')

            history = model.fit(train_ds, validation_data=val_ds, epochs=self.config.epochs, verbose=0, callbacks=callbacks)
            self.training_finished.emit(model, history.history)
        except Exception as exc:
            self.error_message.emit(str(exc))
