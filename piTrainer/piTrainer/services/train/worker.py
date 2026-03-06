from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ...app_state import TrainConfig
from .dataset_service import make_tf_dataset
from .model_service import build_small_cnn, compile_model


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

            self.log_message.emit("Building model...")
            model = build_small_cnn(self.config.img_h, self.config.img_w)
            model = compile_model(model, self.config.learning_rate)

            worker = self

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
