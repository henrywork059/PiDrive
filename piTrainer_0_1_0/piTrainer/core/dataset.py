from __future__ import annotations
import numpy as np
import pandas as pd

def make_tf_dataset(df: pd.DataFrame, img_h: int, img_w: int, batch: int, shuffle: bool, augment: bool):
    import tensorflow as tf

    paths = df["abs_image"].astype(str).to_numpy()
    y_steer = df["steering"].to_numpy(np.float32)
    y_thr = df["throttle"].to_numpy(np.float32)

    ds = tf.data.Dataset.from_tensor_slices((paths, y_steer, y_thr))
    if shuffle:
        ds = ds.shuffle(min(len(df), 5000), reshuffle_each_iteration=True)

    def _load(path, steer, thr):
        img_bytes = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img_bytes, channels=3)
        img = tf.image.resize(img, (img_h, img_w), antialias=True)
        img = tf.cast(img, tf.float32) / 255.0

        if augment:
            img = tf.image.random_brightness(img, max_delta=0.08)
            img = tf.image.random_contrast(img, lower=0.9, upper=1.1)

        y = {"steering": tf.expand_dims(steer, -1), "throttle": tf.expand_dims(thr, -1)}
        return img, y

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch).prefetch(tf.data.AUTOTUNE)
    return ds

def session_split(df: pd.DataFrame, val_ratio: float, seed: int = 42):
    # Split by session to prevent leakage.
    if df.empty or "session" not in df.columns:
        return df, df

    sessions = sorted(df["session"].unique().tolist())
    rng = np.random.default_rng(seed)
    rng.shuffle(sessions)

    n_val = max(1, int(len(sessions) * float(val_ratio)))
    val_sessions = set(sessions[:n_val])
    df_val = df[df["session"].isin(val_sessions)].copy()
    df_train = df[~df["session"].isin(val_sessions)].copy()
    return df_train.reset_index(drop=True), df_val.reset_index(drop=True)
