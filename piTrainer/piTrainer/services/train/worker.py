from __future__ import annotations

import random

import numpy as np
from PySide6.QtCore import QThread, Signal

from ...app_state import TrainConfig
from .dataset_service import make_tf_dataset
from .model_service import build_model, compile_model


class TrainingWorker(QThread):
    log_message = Signal(str)
    progress_changed = Signal(int)
    epoch_metrics = Signal(dict)
    error_message = Signal(str)
    training_finished = Signal(object, dict)

    def __init__(self, train_df, val_df, config: TrainConfig) -> None:
        super().__init__()
        self.train_df = train_df.copy()
        self.val_df = val_df.copy()
        self.config = TrainConfig(**vars(config))
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        try:
            import tensorflow as tf
        except Exception as exc:  # noqa: BLE001
            self.error_message.emit(f"TensorFlow import failed: {exc}")
            return

        try:
            if self.train_df.empty:
                raise RuntimeError("Training dataframe is empty.")

            seed = int(getattr(self.config, 'seed', 42) or 42)
            random.seed(seed)
            np.random.seed(seed)
            tf.keras.utils.set_random_seed(seed)
            self.log_message.emit(f'Set training random seed to {seed}.')

            self.log_message.emit("Building TensorFlow datasets...")
            train_ds = make_tf_dataset(
                self.train_df,
                img_h=self.config.img_h,
                img_w=self.config.img_w,
                batch_size=self.config.batch_size,
                shuffle=self.config.shuffle,
                augment=self.config.augment,
            )
            val_ds = None
            if not self.val_df.empty:
                val_ds = make_tf_dataset(
                    self.val_df,
                    img_h=self.config.img_h,
                    img_w=self.config.img_w,
                    batch_size=self.config.batch_size,
                    shuffle=False,
                    augment=False,
                )

            self.log_message.emit(f"Building model ({self.config.model_size})...")
            model = build_model(self.config.img_h, self.config.img_w, self.config.model_size)
            model = compile_model(model, self.config.learning_rate)

            worker = self
            monitor = 'val_loss' if val_ds is not None else 'loss'

            class EpochCallback(tf.keras.callbacks.Callback):
                def on_epoch_end(self, epoch, logs=None):  # noqa: N802
                    logs = logs or {}
                    payload = {"epoch": int(epoch) + 1}
                    for key, value in logs.items():
                        try:
                            payload[key] = float(value)
                        except Exception:  # noqa: BLE001
                            continue
                    worker.epoch_metrics.emit(payload)
                    progress = int(((epoch + 1) / max(1, worker.config.epochs)) * 100)
                    worker.progress_changed.emit(progress)
                    worker.log_message.emit(
                        "Epoch "
                        f"{epoch + 1}/{worker.config.epochs} — "
                        + ", ".join(f"{k}={v:.5f}" for k, v in payload.items() if k != "epoch")
                    )
                    if worker._stop_requested:
                        self.model.stop_training = True

            callbacks = [EpochCallback()]
            if getattr(self.config, 'early_stopping', False):
                callbacks.append(
                    tf.keras.callbacks.EarlyStopping(
                        monitor=monitor,
                        patience=max(1, int(getattr(self.config, 'early_stopping_patience', 4) or 4)),
                        restore_best_weights=True,
                    )
                )
                self.log_message.emit(
                    f'Enabled early stopping on {monitor} with patience '
                    f"{max(1, int(getattr(self.config, 'early_stopping_patience', 4) or 4))}."
                )
            if getattr(self.config, 'reduce_lr_on_plateau', False):
                callbacks.append(
                    tf.keras.callbacks.ReduceLROnPlateau(
                        monitor=monitor,
                        patience=max(1, int(getattr(self.config, 'reduce_lr_patience', 2) or 2)),
                        factor=float(getattr(self.config, 'reduce_lr_factor', 0.5) or 0.5),
                        min_lr=1e-6,
                        verbose=0,
                    )
                )
                self.log_message.emit(
                    f'Enabled reduce-on-plateau on {monitor} with patience '
                    f"{max(1, int(getattr(self.config, 'reduce_lr_patience', 2) or 2))} and factor "
                    f"{float(getattr(self.config, 'reduce_lr_factor', 0.5) or 0.5):.2f}."
                )

            history = model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=self.config.epochs,
                verbose=0,
                callbacks=callbacks,
            )
            self.training_finished.emit(model, history.history)
        except Exception as exc:  # noqa: BLE001
            self.error_message.emit(str(exc))
