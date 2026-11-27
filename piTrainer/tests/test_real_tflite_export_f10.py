"""F10 real CPU TensorFlow conversion, no training or hardware actuation."""
import tempfile
import sys
import os
import json
import hashlib
import subprocess
from io import BytesIO
import unittest
from pathlib import Path
import numpy as np
import tensorflow as tf
from piTrainer.app_state import TrainConfig, ExportConfig
from piTrainer.services.export.export_service import export_model_artifacts
from piTrainer.utils.model_manifest import inspect_manifest, manifest_path
import test_recording_to_export_f10 as recording_fixture


class RealTfliteExportTests(unittest.TestCase):
    def test_named_heads_export_in_runtime_order(self):
        inputs = tf.keras.Input(shape=(12, 16, 3), name="image")
        pooled = tf.keras.layers.GlobalAveragePooling2D()(inputs)
        throttle = tf.keras.layers.Dense(1, name="throttle", kernel_initializer="zeros",
            bias_initializer=tf.keras.initializers.Constant(.65))(pooled)
        steering = tf.keras.layers.Dense(1, name="steering", kernel_initializer="zeros",
            bias_initializer=tf.keras.initializers.Constant(-.25))(pooled)
        model = tf.keras.Model(inputs, {"throttle": throttle, "steering": steering})
        # Reuse the real mixed on-disk recorder fixture, then create synthetic
        # run metadata for this deterministic untrained conversion (not a real training result).
        fixture = recording_fixture.RecordingContractTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        active = recording_fixture.build_filtered_dataframe(
            recording_fixture.load_records_dataframe(fixture.root, fixture.names), False)
        recipe = {'mirror_enabled': True, 'require_images': True}
        expanded, _ = recording_fixture.apply_preprocessing_recipe(active, recipe)
        train = TrainConfig(img_w=16, img_h=12, seed=27)
        train_df, val_df = recording_fixture.split_dataframe(expanded, train)
        self.assertFalse(set(train_df.abs_image) & set(val_df.abs_image))
        run = recording_fixture.finish_run(recording_fixture.create_run_snapshot(
            train_df, val_df, train, recipe, fixture.names), 'succeeded', {'loss': [.5]})
        with tempfile.TemporaryDirectory() as tmp:
            config = ExportConfig(out_dir=tmp, base_name="ordered_fixture",
                                  export_keras=False, export_tflite=True, quantize_int8=False)
            artifact, = export_model_artifacts(model, config, train_df, train, experiment_record=run)
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
            self.assertEqual(manifest['experiment']['run_id'], run['run_id'])
            self.assertEqual(manifest['experiment']['source_group_count'], 3)
            self.assertNotIn(str(fixture.root), str(manifest['experiment']))
            # Import only runtime model services, never the hardware launchers.
            root = Path(__file__).resolve().parents[2]
            # Real interpreter, exact prepared tensor fixture, five paired trials.
            # This deterministic export is deliberately not a trained driving model.
            report_path = Path(os.environ.get("PIDRIVE_THREAD_REPORT", str(Path(tmp) / "threads.json")))
            tensor_path = Path(tmp) / "prepared.npy"
            tensors = np.random.default_rng(27).integers(0, 256, (8, 12, 16, 3), dtype=np.uint8).astype(np.float32) / 255
            np.save(tensor_path, tensors, allow_pickle=False)
            subprocess.run([sys.executable, str(root / "tools/benchmark_tflite_threads.py"),
                            "--model", artifact.path, "--inputs", str(tensor_path),
                            "--rounds", "5", "--warmup", "10", "--invocations", "100",
                            "--threads", "1", "2", "4", "--output", str(report_path)], check=True)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["model_sha256"], hashlib.sha256(Path(artifact.path).read_bytes()).hexdigest())
            self.assertTrue(all(row["complete"] and row["exact_output_parity"] for row in report["summary"]))
            self.assertFalse(report["deployment_authorized"])
            sys.path[:0] = [str(root / 'PiSD'), str(root / 'PiServer')]
            from pisd.services.ai_drive_service import AIDriveService
            from piserver.services.model_service import ModelService
            model_bytes = Path(artifact.path).read_bytes()
            metadata_bytes = manifest_path(Path(artifact.path)).read_bytes()
            class Upload(BytesIO):
                def __init__(self, data, filename):
                    super().__init__(data)
                    self.filename = filename
                def save(self, target):
                    Path(target).write_bytes(self.read())
            filename = 'transferred.tflite'
            pisd = AIDriveService(Path(tmp) / 'pisd')
            self.addCleanup(pisd.close)
            self.assertTrue(pisd.upload_model(filename, BytesIO(model_bytes), BytesIO(metadata_bytes))['ok'])
            loaded = pisd.load_model(filename)
            self.assertTrue(loaded['ok'], loaded)
            self.assertEqual(pisd.status()['model_manifest'], manifest)
            np.testing.assert_allclose(pisd._predict_from_jpeg((fixture.current / 'frames/0.jpg').read_bytes()),
                                       [-.25, .65], atol=1e-5)
            server = ModelService(Path(tmp) / 'server')
            ok, message = server.save_uploaded_model(Upload(model_bytes, filename),
                Upload(metadata_bytes, filename + '.manifest.json'))
            self.assertTrue(ok, message)
            ok, message = server.load_model(filename)
            self.assertTrue(ok, message)
            self.assertEqual(server.get_model_metadata()['manifest'], manifest)
            np.testing.assert_allclose(server.predict_uv_from_frame(np.zeros((12, 16, 3), dtype=np.uint8)),
                                       [-.25, .65], atol=1e-5)
            # Rejected replacement cannot erase the active model/provenance.
            self.assertFalse(pisd.upload_model('bad.tflite', BytesIO(b'tampered'), BytesIO(metadata_bytes))['ok'])
            ok, _ = server.save_uploaded_model(Upload(b'tampered', 'bad.tflite'),
                Upload(metadata_bytes, 'bad.tflite.manifest.json'))
            self.assertFalse(ok)
            self.assertEqual(pisd.status()['model_manifest'], manifest)
            self.assertEqual(server.get_model_metadata()['manifest'], manifest)
            self.assertTrue(pisd.delete_model(filename)['ok'])
            self.assertIsNone(pisd.status()['model_manifest'])
            ok, _ = server.delete_model(filename)
            self.assertTrue(ok)
            self.assertIsNone(server.get_model_metadata()['manifest'])
