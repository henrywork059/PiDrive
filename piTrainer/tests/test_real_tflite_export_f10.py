"""F10 real CPU TensorFlow conversion, no training or hardware actuation."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import tensorflow as tf
from piTrainer.app_state import TrainConfig, ExportConfig
from piTrainer.services.export.export_service import export_model_artifacts
from piTrainer.utils.model_manifest import inspect_manifest


class RealTfliteExportTests(unittest.TestCase):
    def test_named_heads_export_in_runtime_order(self):
        inputs = tf.keras.Input(shape=(12, 16, 3), name="image")
        pooled = tf.keras.layers.GlobalAveragePooling2D()(inputs)
        throttle = tf.keras.layers.Dense(1, name="throttle", kernel_initializer="zeros",
            bias_initializer=tf.keras.initializers.Constant(.65))(pooled)
        steering = tf.keras.layers.Dense(1, name="steering", kernel_initializer="zeros",
            bias_initializer=tf.keras.initializers.Constant(-.25))(pooled)
        model = tf.keras.Model(inputs, {"throttle": throttle, "steering": steering})
        with tempfile.TemporaryDirectory() as tmp:
            config = ExportConfig(out_dir=tmp, base_name="ordered_fixture",
                                  export_keras=False, export_tflite=True, quantize_int8=False)
            train = TrainConfig(img_w=16, img_h=12, seed=27)
            artifact, = export_model_artifacts(model, config, None, train)
            manifest, _ = inspect_manifest(Path(artifact.path), expected_kind="steering_control",
                                          input_size=(16, 12))
            self.assertEqual(manifest["output"]["interpretation"], "steering_throttle")
            runtime = tf.lite.Interpreter(model_path=artifact.path, num_threads=1)
            runtime.allocate_tensors()
            input_detail, = runtime.get_input_details()
            output_detail, = runtime.get_output_details()
            self.assertEqual(tuple(input_detail["shape"]), (1, 12, 16, 3))
            runtime.set_tensor(input_detail["index"], np.ones((1, 12, 16, 3), dtype=np.float32))
            runtime.invoke()
            result = runtime.get_tensor(output_detail["index"])
            self.assertEqual(tuple(result.shape), (1, 2))
            np.testing.assert_allclose(result, [[-.25, .65]], atol=1e-5)
