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
import pandas as pd
from unittest.mock import patch
from piTrainer.app_state import TrainConfig, ExportConfig
from piTrainer.services.export.export_service import export_model_artifacts
from piTrainer.utils.model_manifest import inspect_manifest, manifest_path
import test_recording_to_export_f10 as recording_fixture


class RealTfliteExportTests(unittest.TestCase):
    def test_real_dataset_projection_matches_legacy_pixels_and_labels(self):
        from piTrainer.services.train import dataset_service as ds
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            rng = np.random.default_rng(52)
            for i in range(5):
                path = str(Path(tmp) / f"{i}.jpg")
                tf.io.write_file(path, tf.io.encode_jpeg(
                    rng.integers(0, 256, (24, 32, 3), dtype=np.uint8)))
                paths.append(path)
            df = pd.DataFrame({
                "abs_image": paths, "frame_id": ["a", "b", "c", "d", "e"],
                "source_frame_id": ["", "a", "", "c", ""],
                "steering": [.3, .3, .2, .2, .8],
                "throttle": [.4, .7, .6, .3, .9],
                "aug_flip_lr": [False, True, False, True, False],
                "source_steering": [None, None, None, .2, None],
                "source_throttle": [None, .4, None, .6, None],
                "aug_brightness_delta": [0, .05, 0, -.03, 0],
                "aug_contrast_factor": [1, 1.1, .95, 1, 1],
                "aug_saturation_factor": [1, .9, 1, 1.05, 1],
                "aug_hue_delta": [0, 0, .02, -.03, 0],
                "hidden": [False, False, False, False, True],
                "unused_metadata": [{"source": i} for i in range(5)],
            })
            def legacy(frame):
                return ds.normalize_horizontal_flip_labels(ds.without_hidden_rows(frame))
            def batches():
                dataset = ds.make_tf_dataset(df, 12, 16, 3, shuffle=False, augment=False)
                return list(dataset.as_numpy_iterator())
            with patch.object(ds, "_prepare_dataset_rows", side_effect=legacy):
                expected = batches()
            actual = batches()
            self.assertEqual([len(batch[0]) for batch in actual], [3, 1])
            self.assertEqual(len(actual), len(expected))
            for (img, labels), (ref_img, ref_labels) in zip(actual, expected):
                np.testing.assert_array_equal(img, ref_img)
                for key in ("steering", "throttle"):
                    np.testing.assert_array_equal(labels[key], ref_labels[key])
            np.testing.assert_allclose(np.concatenate([y["steering"] for _,y in actual]).ravel(),
                                       [.3, -.3, .2, -.2])
            np.testing.assert_allclose(np.concatenate([y["throttle"] for _,y in actual]).ravel(),
                                       [.4, .4, .6, .6])

    def test_nonconstant_real_interpreter_thread_and_delegate_parity(self):
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root))
        from tools.benchmark_tflite_threads import compare

        @tf.function(input_signature=[tf.TensorSpec([1, 12, 16, 3], tf.float32)],
                     autograph=False)
        def synthetic_control(image):
            # Nonconstant two-value output, binary-exact input and reductions.
            # This is an operation fixture, not a trained driving model.
            return tf.reduce_sum(image[:, :, :, :2], axis=[1, 2]) / 256.0

        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "nonconstant.tflite"
            converter = tf.lite.TFLiteConverter.from_concrete_functions(
                [synthetic_control.get_concrete_function()])
            model.write_bytes(converter.convert())
            inputs = np.random.default_rng(37).integers(
                0, 256, (8, 12, 16, 3), dtype=np.uint8).astype(np.float32) / 256
            probe = tf.lite.Interpreter(model_path=str(model))
            probe.allocate_tensors()
            i, = probe.get_input_details()
            o, = probe.get_output_details()
            values = []
            for image in inputs:
                probe.set_tensor(i["index"], image[None, ...])
                probe.invoke()
                values.append(probe.get_tensor(o["index"]).tobytes())
            self.assertGreater(len(set(values)), 1)
            default = compare(tf.lite.Interpreter, model, inputs)
            self.assertTrue(all(x["complete"] and x["exact_output_parity"] for x in default["summary"]))
            report = {"model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                      "inputs_sha256": hashlib.sha256(inputs.tobytes()).hexdigest(),
                      "default_delegates": default, "fixture": "nonconstant synthetic control",
                      "tensorflow": tf.__version__, "deployment_authorized": False}
            resolver = getattr(getattr(tf.lite.experimental, "OpResolverType", None),
                               "BUILTIN_WITHOUT_DEFAULT_DELEGATES", None)
            if resolver is None:
                report["builtin_only"] = {"supported": False, "reason": "Resolver unavailable"}
            else:
                def builtin_only(**kwargs):
                    return tf.lite.Interpreter(
                        experimental_op_resolver_type=resolver, **kwargs)
                try:
                    comparison = compare(builtin_only, model, inputs)
                except (TypeError, ValueError, RuntimeError) as exc:
                    report["builtin_only"] = {"supported": False, "reason": str(exc)}
                else:
                    expected = next(r["output_sha256"] for row in default["rounds"]
                                    for r in row["results"] if r["threads"] is None)
                    exact = all(r.get("output_sha256") == expected
                                for row in comparison["rounds"] for r in row["results"])
                    report["builtin_only"] = {"supported": True, "cross_mode_exact_parity": exact,
                                              "comparison": comparison}
                    self.assertTrue(exact, "Built-in-only output differs from default delegate output")
            report_path = Path(os.environ.get("PIDRIVE_THREAD_REPORT", str(Path(tmp) / "threads.json")))
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.with_name("nonconstant.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")

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
