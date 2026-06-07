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

def _prepare_inputs(dataset_df: pd.DataFrame, img_h: int, img_w: int, max_rows: int):
    rows = normalize_horizontal_flip_labels(dataset_df.copy())
    rows['source_row_number'] = rows.index.astype(int) + 1
    rows = rows[rows['abs_image'].astype(str).map(lambda p: Path(p).exists())].reset_index(drop=True)
    if max_rows and max_rows > 0:
        rows = rows.head(max_rows).reset_index(drop=True)
    if rows.empty:
        raise ValueError('No usable validation rows remain after filtering for existing image files.')

    from PIL import Image

    flip_flags = boolean_series(rows['aug_flip_lr'], default=False).tolist() if 'aug_flip_lr' in rows.columns else [False] * len(rows)
    flip_left_right = getattr(getattr(Image, 'Transpose', Image), 'FLIP_LEFT_RIGHT')

    images = []
    for index, path in enumerate(rows['abs_image'].astype(str)):
        with Image.open(path) as image:
            image = image.convert('RGB')
            if flip_flags[index]:
                image = image.transpose(flip_left_right)
            image = image.resize((img_w, img_h))
            arr = np.asarray(image, dtype=np.float32) / 255.0
            images.append(arr)
    x = np.stack(images, axis=0)
    steering_true = rows['steering'].astype(float).to_numpy(np.float32)
    throttle_true = rows['throttle'].astype(float).to_numpy(np.float32)
    return rows, x, steering_true, throttle_true

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

