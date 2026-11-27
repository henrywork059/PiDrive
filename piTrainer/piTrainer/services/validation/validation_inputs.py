from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..data.augmentation_service import boolean_series, normalize_horizontal_flip_labels


def _load_model(in_memory_model, model_source: str, model_path: str):
    if model_source == 'Current trained model':
        if in_memory_model is None:
            raise ValueError('No in-memory trained model is available. Train a model first or load a saved model file.')
        return in_memory_model

    chosen = Path(model_path).expanduser()
    if not chosen.exists():
        raise FileNotFoundError(f'Model file not found: {chosen}')

    import tensorflow as tf

    return tf.keras.models.load_model(chosen)

class PreparedImageSource:
    """Read-only ordered image source; decode only the requested contiguous batch.

    Retains paths and flip flags, not decoded images. No image cache, random
    augmentation, reordering, or change to PIL's established resize/normalize.
    """
    def __init__(self, paths, flips, img_h: int, img_w: int):
        self.paths = tuple(paths)
        self.flips = tuple(flips)
        if len(self.paths) != len(self.flips):
            raise ValueError("Image paths and flip flags must have equal lengths.")
        self.shape = (len(self.paths), int(img_h), int(img_w), 3)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, key):
        if not isinstance(key, slice):
            raise TypeError("Prepared image source requires a contiguous slice.")
        start, stop, step = key.indices(len(self))
        if step != 1:
            raise ValueError("Prepared image source requires a contiguous slice.")
        from PIL import Image
        flip_left_right = getattr(getattr(Image, 'Transpose', Image), 'FLIP_LEFT_RIGHT')
        h, w = self.shape[1:3]
        result = np.empty((max(0, stop-start), h, w, 3), dtype=np.float32)
        for out_index, index in enumerate(range(start, stop)):
            with Image.open(self.paths[index]) as image:
                image = image.convert('RGB')
                if self.flips[index]:
                    image = image.transpose(flip_left_right)
                image = image.resize((w, h))
                # Preserve the exact old expression; only the destination changes.
                result[out_index] = np.asarray(image, dtype=np.float32) / 255.0
        return result


def _prepare_input_source(dataset_df: pd.DataFrame, img_h: int, img_w: int, max_rows: int):
    rows = normalize_horizontal_flip_labels(dataset_df.copy())
    rows['source_row_number'] = rows.index.astype(int) + 1
    rows = rows[rows['abs_image'].astype(str).map(lambda p: Path(p).exists())].reset_index(drop=True)
    if max_rows and max_rows > 0:
        rows = rows.head(max_rows).reset_index(drop=True)
    if rows.empty:
        raise ValueError('No usable validation rows remain after filtering for existing image files.')
    flip_flags = boolean_series(rows['aug_flip_lr'], default=False).tolist() if 'aug_flip_lr' in rows.columns else [False] * len(rows)
    source = PreparedImageSource(rows['abs_image'].astype(str), flip_flags, img_h, img_w)
    steering_true = rows['steering'].astype(float).to_numpy(np.float32)
    throttle_true = rows['throttle'].astype(float).to_numpy(np.float32)
    return rows, source, steering_true, throttle_true


def _prepare_inputs(dataset_df: pd.DataFrame, img_h: int, img_w: int, max_rows: int):
    # Keras still receives a single tensor in its existing model.predict call;
    # avoid retaining a second full list of decoded images before stacking.
    rows, source, steering_true, throttle_true = _prepare_input_source(dataset_df, img_h, img_w, max_rows)
    return rows, source[:], steering_true, throttle_true

def _prediction_arrays(predictions) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(predictions, dict):
        steering_pred = np.asarray(predictions.get('steering')).reshape(-1)
        throttle_pred = np.asarray(predictions.get('throttle')).reshape(-1)
    elif isinstance(predictions, (list, tuple)) and len(predictions) >= 2:
        steering_pred = np.asarray(predictions[0]).reshape(-1)
        throttle_pred = np.asarray(predictions[1]).reshape(-1)
    else:
        pred = np.asarray(predictions)
        if pred.ndim == 2 and pred.shape[1] >= 2:
            steering_pred = pred[:, 0].reshape(-1)
            throttle_pred = pred[:, 1].reshape(-1)
        else:
            raise ValueError('Unsupported model prediction output shape for validation.')
    return steering_pred.astype(np.float32), throttle_pred.astype(np.float32)

