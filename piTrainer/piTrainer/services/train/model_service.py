from __future__ import annotations



def build_small_cnn(img_h: int, img_w: int):
    import tensorflow as tf

    inputs = tf.keras.Input(shape=(img_h, img_w, 3), name="image")
    x = tf.keras.layers.Conv2D(16, 5, strides=2, activation="relu")(inputs)
    x = tf.keras.layers.Conv2D(24, 5, strides=2, activation="relu")(x)
    x = tf.keras.layers.Conv2D(32, 3, strides=2, activation="relu")(x)
    x = tf.keras.layers.Conv2D(48, 3, strides=2, activation="relu")(x)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    steering = tf.keras.layers.Dense(1, name="steering")(x)
    throttle = tf.keras.layers.Dense(1, name="throttle")(x)
    return tf.keras.Model(inputs, {"steering": steering, "throttle": throttle}, name="picar_small_cnn")



def compile_model(model, learning_rate: float):
    import tensorflow as tf

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=float(learning_rate)),
        loss={"steering": "mse", "throttle": "mse"},
        metrics={"steering": ["mae"], "throttle": ["mae"]},
    )
    return model
