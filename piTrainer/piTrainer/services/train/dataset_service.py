from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.augmentation_service import boolean_series, normalize_horizontal_flip_labels
from ..data.visibility_service import HIDDEN_FLAG_KEYS, without_hidden_rows


def _series_or_default(df: pd.DataFrame, column: str, default, dtype):
    if column in df.columns:
        return df[column].to_numpy(dtype)
    return np.full(len(df), default, dtype=dtype)


# Keep every visibility and flip-label dependency; omit unrelated review metadata.
_DATASET_COLUMNS = frozenset((*HIDDEN_FLAG_KEYS, 'training_label', 'abs_image', 'steering',
    'throttle', 'aug_flip_lr', 'aug_brightness_delta', 'aug_contrast_factor',
    'aug_saturation_factor', 'aug_hue_delta', 'source_steering', 'source_throttle',
    'source_speed', 'speed', 'frame_id', 'source_frame_id', 'flip_steering_inverted',
    'flip_label_source', 'flip_label_warning'))


def _prepare_dataset_rows(df):
    if df is not None and df.columns.is_unique:
        df = df.loc[:, [column for column in df.columns if column in _DATASET_COLUMNS]]
    return normalize_horizontal_flip_labels(without_hidden_rows(df))


def make_tf_dataset(df: pd.DataFrame, img_h: int, img_w: int, batch_size: int, shuffle: bool, augment: bool):
    import tensorflow as tf

    df = _prepare_dataset_rows(df)
    paths = df['abs_image'].astype(str).to_numpy()
    steering = df['steering'].to_numpy(np.float32)
    throttle = df['throttle'].to_numpy(np.float32)
    flip_lr = boolean_series(df['aug_flip_lr'], default=False).to_numpy(np.bool_) if 'aug_flip_lr' in df.columns else np.full(len(df), False, dtype=np.bool_)
    brightness = _series_or_default(df, 'aug_brightness_delta', 0.0, np.float32)
    contrast = _series_or_default(df, 'aug_contrast_factor', 1.0, np.float32)
    saturation = _series_or_default(df, 'aug_saturation_factor', 1.0, np.float32)
    hue = _series_or_default(df, 'aug_hue_delta', 0.0, np.float32)

    dataset = tf.data.Dataset.from_tensor_slices((paths, steering, throttle, flip_lr, brightness, contrast, saturation, hue))
    if shuffle:
        dataset = dataset.shuffle(min(len(df), 5000), reshuffle_each_iteration=True)

    def _load(path, steer, thr, flip, bright, contrast_factor, saturation_factor, hue_delta):
        image_bytes = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image_bytes, channels=3)
        image = tf.image.resize(image, (img_h, img_w), antialias=True)
        image = tf.cast(image, tf.float32) / 255.0

        image = tf.cond(flip, lambda: tf.image.flip_left_right(image), lambda: image)
        image = tf.image.adjust_brightness(image, bright)
        image = tf.image.adjust_contrast(image, contrast_factor)
        image = tf.image.adjust_saturation(image, saturation_factor)
        image = tf.image.adjust_hue(image, hue_delta)
        image = tf.clip_by_value(image, 0.0, 1.0)

        if augment:
            image = tf.image.random_brightness(image, max_delta=0.08)
            image = tf.image.random_contrast(image, lower=0.9, upper=1.1)
            image = tf.clip_by_value(image, 0.0, 1.0)

        outputs = {
            'steering': tf.expand_dims(steer, axis=-1),
            'throttle': tf.expand_dims(thr, axis=-1),
        }
        return image, outputs

    options = tf.data.Options()
    # Faster input pipeline for local image folders. Order is not meaningful once
    # samples are shuffled, so allow TensorFlow to overlap decode/resize work.
    options.experimental_deterministic = not bool(shuffle or augment)
    dataset = dataset.with_options(options)
    dataset = dataset.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(max(1, int(batch_size))).prefetch(tf.data.AUTOTUNE)
    return dataset
