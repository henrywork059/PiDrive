from __future__ import annotations

def build_small_cnn(img_h: int, img_w: int):
    import tensorflow as tf

    inp = tf.keras.Input(shape=(img_h, img_w, 3), name="image")
    x = tf.keras.layers.Conv2D(16, 5, strides=2, activation="relu")(inp)
    x = tf.keras.layers.Conv2D(24, 5, strides=2, activation="relu")(x)
    x = tf.keras.layers.Conv2D(32, 3, strides=2, activation="relu")(x)
    x = tf.keras.layers.Conv2D(48, 3, strides=2, activation="relu")(x)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.2)(x)

    steer = tf.keras.layers.Dense(1, name="steering")(x)
    thr = tf.keras.layers.Dense(1, name="throttle")(x)

    model = tf.keras.Model(inp, {"steering": steer, "throttle": thr}, name="picar_small_cnn")
    return model

def compile_model(model, lr: float):
    import tensorflow as tf
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=float(lr)),
        loss={"steering": "mse", "throttle": "mse"},
        metrics={"steering": ["mae"], "throttle": ["mae"]},
    )
    return model
