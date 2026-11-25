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

    def test_portable_run_claim_survives_renamed_model_transfer(self):
        claim = {"run_id": "a"*32, "preprocessing_sha256": "b"*64,
                 "identity_label_sha256": "c"*64, "train_rows": 10,
                 "validation_rows": 4, "source_group_count": 2}
        expected = self.publish(STEERING_EXPORT, "steering_control", experiment=claim)
        target = self.model.with_name("renamed-on-pi.tflite")
        target.write_bytes(self.model.read_bytes())
        STEERING_EXPORT.manifest_path(target).write_bytes(STEERING_EXPORT.manifest_path(self.model).read_bytes())
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name):
                observed, _ = reader.inspect_manifest(target, expected_kind="steering_control")
                self.assertEqual(observed, expected)
                for key, bad in (("run_id", "../bad"), ("train_rows", True), ("preprocessing_sha256", "secret/path")):
                    malformed = dict(expected, experiment=dict(claim, **{key: bad}))
                    with self.assertRaises(ValueError):
                        reader.validate_manifest(malformed)
        target.write_bytes(b"tampered")
        for reader in RUNTIMES.values():
            with self.assertRaises(ValueError):
                reader.inspect_manifest(target)

    def test_nonsteering_manifest_rejected_by_active_runtimes(self):
        # Construct foreign-family metadata with the active reader's own helper;
        # no dependency on the retired CustomTrainer component.
        for name, reader in RUNTIMES.items():
            with self.subTest(runtime=name):
                self.publish(reader, "yolo_detection", class_names=["cone"])
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
