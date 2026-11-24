"""Cross-component manifest compatibility; dummy bytes, no model inference or hardware."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_helper(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise ImportError(relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STEERING_EXPORT = load_helper("steering_export", "piTrainer/piTrainer/utils/model_manifest.py")
YOLO_EXPORT = load_helper("yolo_export", "CustomTrainer/custom_trainer/services/model_manifest.py")
RUNTIMES = {
    "PiSD": load_helper("pisd_manifest", "PiSD/pisd/core/model_manifest.py"),
    "PiServer": load_helper("piserver_manifest", "PiServer/piserver/core/model_manifest.py"),
}


class CrossComponentManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.model = Path(self.directory.name) / "sample.tflite"
        self.model.write_bytes(b"dummy-model-not-an-interpreter")

    def publish(self, exporter, kind, **kwargs):
        manifest = exporter.make_manifest(
            self.model, model_kind=kind, width=160, height=120, **kwargs
        )
        exporter.write_manifest(self.model, manifest)
        return manifest

    def test_steering_export_accepted_by_both_runtime_readers(self):
        expected = self.publish(STEERING_EXPORT, "steering_control", training_seed=27)
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name):
                observed, message = reader.inspect_manifest(
                    self.model, expected_kind="steering_control", input_size=(160, 120)
                )
                self.assertEqual(observed, expected)
                self.assertIn("verified", message.lower())

    def test_yolo_export_type_and_class_order_preserved(self):
        expected = self.publish(YOLO_EXPORT, "yolo_detection", class_names=["road", "cone"])
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name):
                observed, _ = reader.inspect_manifest(
                    self.model, expected_kind="yolo_detection", input_size=(160, 120)
                )
                self.assertEqual(observed, expected)
                self.assertEqual(observed["class_names"], ["road", "cone"])
                with self.assertRaises(ValueError):
                    reader.inspect_manifest(self.model, expected_kind="steering_control")

    def test_steering_export_rejected_as_yolo(self):
        self.publish(STEERING_EXPORT, "steering_control")
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name), self.assertRaises(ValueError):
                reader.inspect_manifest(self.model, expected_kind="yolo_detection")

    def test_tampering_and_geometry_mismatch_rejected(self):
        self.publish(STEERING_EXPORT, "steering_control")
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name, fault="geometry"), self.assertRaises(ValueError):
                reader.inspect_manifest(self.model, input_size=(120, 160))
        self.model.write_bytes(b"changed")
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name, fault="checksum"), self.assertRaises(ValueError):
                reader.inspect_manifest(self.model, expected_kind="steering_control")

    def test_missing_sidecar_is_legacy_not_verified(self):
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name):
                observed, message = reader.inspect_manifest(self.model)
                self.assertIsNone(observed)
                self.assertIn("legacy", message.lower())

    def test_malformed_sidecar_is_not_legacy(self):
        STEERING_EXPORT.manifest_path(self.model).write_text("{", encoding="utf-8")
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name), self.assertRaises(ValueError):
                reader.inspect_manifest(self.model)


if __name__ == "__main__":
    unittest.main()
