from __future__ import annotations

import numpy as np
import pandas as pd


def make_tf_dataset(df: pd.DataFrame, img_h: int, img_w: int, batch_size: int, shuffle: bool, augment: bool):
    import tensorflow as tf

    paths = df['abs_image'].astype(str).to_numpy()
    steering = df['steering'].to_numpy(np.float32)
    throttle = df['throttle'].to_numpy(np.float32)
    flip_lr = df.get('aug_flip_lr', pd.Series(False, index=df.index)).astype(bool).to_numpy(np.bool_)
    brightness = df.get('aug_brightness_delta', pd.Series(0.0, index=df.index)).to_numpy(np.float32)
    contrast = df.get('aug_contrast_factor', pd.Series(1.0, index=df.index)).to_numpy(np.float32)
    saturation = df.get('aug_saturation_factor', pd.Series(1.0, index=df.index)).to_numpy(np.float32)
    hue = df.get('aug_hue_delta', pd.Series(0.0, index=df.index)).to_numpy(np.float32)

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

    dataset = dataset.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return dataset
