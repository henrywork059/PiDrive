from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.visibility_service import without_hidden_rows


def _series_or_default(df: pd.DataFrame, column: str, default, dtype):
    if column in df.columns:
        return df[column].to_numpy(dtype)
    return np.full(len(df), default, dtype=dtype)


def make_tf_dataset(df: pd.DataFrame, img_h: int, img_w: int, batch_size: int, shuffle: bool, augment: bool):
    import tensorflow as tf

    df = without_hidden_rows(df)
    paths = df['abs_image'].astype(str).to_numpy()
    steering = df['steering'].to_numpy(np.float32)
    throttle = df['throttle'].to_numpy(np.float32)
    flip_lr = _series_or_default(df, 'aug_flip_lr', False, np.bool_)
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
