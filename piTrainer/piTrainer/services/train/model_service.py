from __future__ import annotations


def _kernel_regularizer(value: float):
    if float(value or 0.0) <= 0.0:
        return None
    import tensorflow as tf
    return tf.keras.regularizers.l2(float(value))


def build_small_cnn(img_h: int, img_w: int, dropout_rate: float = 0.2, l2_reg: float = 0.0):
    import tensorflow as tf

    kernel_regularizer = _kernel_regularizer(l2_reg)
    inputs = tf.keras.Input(shape=(img_h, img_w, 3), name="image")
    x = tf.keras.layers.Conv2D(16, 5, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(inputs)
    x = tf.keras.layers.Conv2D(24, 5, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Conv2D(32, 3, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Conv2D(48, 3, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dense(128, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Dropout(float(dropout_rate))(x)
    steering = tf.keras.layers.Dense(1, name="steering", kernel_regularizer=kernel_regularizer)(x)
    throttle = tf.keras.layers.Dense(1, name="throttle", kernel_regularizer=kernel_regularizer)(x)
    return tf.keras.Model(inputs, {"steering": steering, "throttle": throttle}, name="picar_small_cnn")


def build_medium_cnn(img_h: int, img_w: int, dropout_rate: float = 0.3, l2_reg: float = 0.0):
    import tensorflow as tf

    kernel_regularizer = _kernel_regularizer(l2_reg)
    inputs = tf.keras.Input(shape=(img_h, img_w, 3), name="image")
    x = tf.keras.layers.Conv2D(24, 5, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(inputs)
    x = tf.keras.layers.Conv2D(32, 5, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Conv2D(48, 3, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Conv2D(64, 3, strides=2, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Conv2D(64, 3, strides=1, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dense(192, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    x = tf.keras.layers.Dropout(float(dropout_rate))(x)
    x = tf.keras.layers.Dense(96, activation="relu", kernel_regularizer=kernel_regularizer)(x)
    steering = tf.keras.layers.Dense(1, name="steering", kernel_regularizer=kernel_regularizer)(x)
    throttle = tf.keras.layers.Dense(1, name="throttle", kernel_regularizer=kernel_regularizer)(x)
    return tf.keras.Model(inputs, {"steering": steering, "throttle": throttle}, name="picar_medium_cnn")


def build_model(img_h: int, img_w: int, model_size: str = 'Small CNN', dropout_rate: float = 0.2, l2_reg: float = 0.0):
    if str(model_size) == 'Medium CNN':
        return build_medium_cnn(img_h, img_w, dropout_rate, l2_reg)
    return build_small_cnn(img_h, img_w, dropout_rate, l2_reg)


def compile_model(model, learning_rate: float, steering_loss_weight: float = 1.0, throttle_loss_weight: float = 1.0, clipnorm: float = 0.0):
    import tensorflow as tf

    optimizer_kwargs = {'learning_rate': float(learning_rate)}
    if float(clipnorm or 0.0) > 0.0:
        optimizer_kwargs['clipnorm'] = float(clipnorm)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(**optimizer_kwargs),
        loss={"steering": "mse", "throttle": "mse"},
        loss_weights={"steering": float(steering_loss_weight), "throttle": float(throttle_loss_weight)},
        metrics={"steering": ["mae"], "throttle": ["mae"]},
    )
    return model
