from __future__ import annotations

import numpy as np
import pandas as pd



def make_tf_dataset(df: pd.DataFrame, img_h: int, img_w: int, batch_size: int, shuffle: bool, augment: bool):
    import tensorflow as tf

    paths = df["abs_image"].astype(str).to_numpy()
    steering = df["steering"].to_numpy(np.float32)
    throttle = df["throttle"].to_numpy(np.float32)

    dataset = tf.data.Dataset.from_tensor_slices((paths, steering, throttle))
    if shuffle:
        dataset = dataset.shuffle(min(len(df), 5000), reshuffle_each_iteration=True)

    def _load(path, steer, thr):
        image_bytes = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image_bytes, channels=3)
        image = tf.image.resize(image, (img_h, img_w), antialias=True)
        image = tf.cast(image, tf.float32) / 255.0
        if augment:
            image = tf.image.random_brightness(image, max_delta=0.08)
            image = tf.image.random_contrast(image, lower=0.9, upper=1.1)
        outputs = {
            "steering": tf.expand_dims(steer, axis=-1),
            "throttle": tf.expand_dims(thr, axis=-1),
        }
        return image, outputs

    dataset = dataset.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return dataset
