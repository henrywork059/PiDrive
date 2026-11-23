"""R42 honest artifact summaries: marker parsing, path verification and UI smoke."""
from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path

from custom_trainer.services.model_manifest import make_manifest, write_manifest
from custom_trainer.services.task_result_summary import TaskResult, verified_output


class TaskResultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = self.root / "model name.pt"
        self.model.write_bytes(b"nonempty weights")
        self.dataset = self.root / "test dataset.yaml"
        self.dataset.write_text("path: images\n", encoding="utf-8")

    def begin(self, kind="val", mode="native"):
        return TaskResult.begin(mode, kind, str(self.model), str(self.dataset), self.root)

    def put_output(self, name="runs/val1", file="results.csv"):
        folder = self.root / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / file).write_bytes(b"metrics")
        return folder

    def test_immutable_model_and_dataset_at_launch(self):
        run = self.begin()
        self.assertEqual(run.model, str(self.model))
        self.assertEqual(run.dataset, str(self.dataset))
        self.assertIn(self.model.name, run.display_text())

    def test_relative_model_paths_resolve_against_worker_cwd(self):
        run = TaskResult.begin("native", "val", self.model.name, self.dataset.name, self.root)
        self.assertEqual(run.model, str(self.model))

    def test_native_validation_metrics_and_exact_output(self):
        out = self.put_output()
        run = self.begin()
        run.observe("[save-dir] runs/val1")
        run.observe("[metrics] precision=0.7 | mAP50=0.6")
        run.finish(0)
        self.assertEqual(run.state, "Succeeded")
        self.assertEqual(run.metrics, "precision=0.7 | mAP50=0.6")
        self.assertEqual(run.verified_path(), out)
        self.assertIn("Native-model validation", run.display_text())

    def test_exported_validation_distinct_from_native(self):
        run = self.begin(mode="exported")
        self.assertIn("Exported-model validation", run.display_text())
        self.assertNotIn("Native-model validation", run.display_text())

    def test_prediction_folder_requires_nonempty_image(self):
        out = self.root / "predict"
        out.mkdir()
        (out / "notes.txt").write_text("not an image")
        run = self.begin(kind="predict")
        run.observe(f"[save-dir] {out}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        self.assertIsNone(run.verified_path())

    def test_prediction_image_succeeds(self):
        out = self.put_output("predict", "img.jpg")
        run = self.begin(kind="predict", mode="exported")
        run.observe(f"[save-dir] {out}")
        run.finish(0)
        self.assertEqual(run.state, "Succeeded")
        self.assertEqual(run.verified_path(), out)
        self.assertIn("Exported-model prediction", run.display_text())

    def test_export_single_file_requires_nonempty_bytes(self):
        output = self.root / "out.onnx"
        output.write_bytes(b"")
        run = self.begin(kind="export", mode="export")
        run.observe(f"[export] {output}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        output.write_bytes(b"good model")
        self.assertIsNone(run.verified_path())  # Failed run must never enable Open Location.

    def test_input_model_cannot_be_reported_as_exported_result(self):
        run = self.begin(kind="export", mode="export")
        run.observe(f"[export] {self.model}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        self.assertIn("equals the input", run.reason)

    def test_prediction_source_cannot_be_reported_as_output(self):
        source = self.put_output("input_images", "frame.jpg")
        run = TaskResult.begin("native", "predict", str(self.model), str(source), self.root)
        run.observe(f"[save-dir] {source}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")

    def test_validation_requires_directory(self):
        file = self.root / "results.csv"
        file.write_text("valid")
        run = self.begin()
        run.observe(f"[save-dir] {file}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")

    def test_stop_request_displays_stopping_before_completion(self):
        run = self.begin()
        run.request_stop()
        self.assertEqual(run.state, "Stopping")
        run.finish(0)
        self.assertEqual(run.state, "Cancelled")

    def test_export_success_shows_exact_file(self):
        output = self.root / "model.onnx"
        output.write_bytes(b"good model")
        run = self.begin(kind="export", mode="export")
        run.observe(f"[export] {output}")
        run.finish(0)
        self.assertEqual(run.state, "Succeeded")
        self.assertEqual(run.verified_path(), output)

    def test_export_folder_requires_nonempty_contents(self):
        folder = self.root / "openvino_model"
        folder.mkdir()
        run = self.begin(kind="export", mode="export")
        run.observe(f"[export] {folder}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        (folder / "weights.bin").write_bytes(b"weights")
        other = self.begin(kind="export", mode="export")
        other.observe(f"[export] {folder}")
        other.finish(0)
        self.assertEqual(other.state, "Succeeded")

    def test_tflite_export_checks_sidecar_checksum(self):
        model = self.root / "net.tflite"
        model.write_bytes(b"tflite bytes")
        run = self.begin(kind="export", mode="export")
        run.observe(f"[export] {model}")
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        manifest = make_manifest(model, model_kind="yolo_detection", width=320,
                                 height=320, class_names=["object"])
        write_manifest(model, manifest)
        other = self.begin(kind="export", mode="export")
        other.observe(f"[export] {model}")
        other.finish(0)
        self.assertEqual(other.state, "Succeeded")
        model.write_bytes(b"tampered")
        self.assertIsNone(other.verified_path())

    def test_manifest_marker_does_not_override_exported_artifact(self):
        model = self.root / "net.onnx"
        model.write_bytes(b"model")
        run = self.begin(kind="export", mode="export")
        run.observe(f"[export] {model}")
        run.observe(f"[export] Model manifest: {model}.manifest.json")
        self.assertEqual(run.output_path, str(model))

    def test_nonzero_exit_is_failed_even_if_output_exists(self):
        out = self.put_output()
        run = self.begin()
        run.observe(f"[save-dir] {out}")
        run.observe("[metrics] precision=0.8")
        run.finish(1)
        self.assertEqual(run.state, "Failed")
        self.assertIsNone(run.verified_path())

    def test_stop_is_cancelled_even_if_exit_zero(self):
        out = self.put_output()
        run = self.begin()
        run.observe(f"[save-dir] {out}")
        run.request_stop()
        run.finish(0)
        self.assertEqual(run.state, "Cancelled")
        self.assertIsNone(run.verified_path())

    def test_save_dir_only_not_completion(self):
        run = self.begin()
        run.observe("[save-dir] runs/not-yet-created")
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        self.assertIn("neither a completed output nor validation metrics", run.reason)

    def test_metrics_without_output_succeeds_without_open_location(self):
        run = self.begin()
        run.observe("[metrics] mAP50=0.9")
        run.finish(0)
        self.assertEqual(run.state, "Succeeded")
        self.assertIsNone(run.verified_path())
        self.assertIn("mAP50=0.9", run.display_text())
        self.assertIn("Reported output path (unconfirmed)", run.display_text())

    def test_validation_without_metrics_or_files_is_failure(self):
        run = self.begin()
        run.finish(0)
        self.assertEqual(run.state, "Failed")
        self.assertIsNone(run.verified_path())

    def test_missing_validation_metrics_show_unknown(self):
        out = self.put_output()
        run = self.begin()
        run.observe(f"[save-dir] {out}")
        run.finish(0)
        self.assertIn("Reported metrics: Unknown", run.display_text())

    def test_failure_carries_cli_error(self):
        run = self.begin()
        run.observe("[error] model input mismatch")
        run.finish(2)
        self.assertIn("input mismatch", run.reason)
        self.assertEqual(run.state, "Failed")

    def test_paths_with_spaces_roundtrip(self):
        out = self.put_output("results with spaces", "summary.json")
        run = self.begin()
        run.observe(f"[save-dir] {out}")
        run.finish(0)
        self.assertEqual(run.verified_path(), out)

    def test_nonexistent_output_never_verified(self):
        self.assertIsNone(verified_output(self.root / "nope", "val"))

    def test_finished_output_deleted_blocks_reopen(self):
        out = self.put_output()
        run = self.begin()
        run.observe(f"[save-dir] {out}")
        run.finish(0)
        self.assertIsNotNone(run.verified_path())
        (out / "results.csv").unlink()
        self.assertIsNone(run.verified_path())

    def test_unknown_model_is_honestly_labelled(self):
        run = TaskResult.begin("native", "val", "", "", self.root)
        self.assertIn("Model: Unknown", run.display_text())
        self.assertIn("Not verified", run.display_text())

    def test_output_not_reported_is_unknown(self):
        run = self.begin()
        self.assertIn("Reported output path (unconfirmed): Unknown", run.display_text())

    def test_start_end_time_distinct(self):
        run = self.begin()
        self.assertTrue(run.started_at)
        self.assertFalse(run.finished_at)
        run.finish(4)
        self.assertTrue(run.finished_at)

    def test_file_remains_unmodified_after_summary(self):
        before = self.model.read_bytes()
        run = self.begin()
        run.observe("[metrics] val=0.3")
        run.finish(1)
        self.assertEqual(self.model.read_bytes(), before)

    def test_new_run_has_no_stale_metrics_or_path(self):
        first = self.begin()
        first.observe("[metrics] mAP50=0.5")
        first.observe("[save-dir] first")
        second = self.begin()
        self.assertEqual(second.metrics, "")
        self.assertEqual(second.output_path, "")

    def test_modified_python_files_parse(self):
        root = Path(__file__).resolve().parents[1] / "custom_trainer"
        for file in [
            "services/task_result_summary.py",
            "ui/widgets/task_result_panel.py",
            "ui/pages/validate_page.py",
            "ui/pages/export_validate_page.py",
            "ui/pages/export_page.py",
            "ui/main_window.py",
        ]:
            with self.subTest(file=file):
                ast.parse((root / file).read_text(encoding="utf-8"), filename=file)


class OptionalQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PySide6 not available")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])

    def test_open_button_disabled_without_verified_output(self):
        from custom_trainer.ui.widgets.task_result_panel import TaskResultPanel
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            panel = TaskResultPanel()
            run = TaskResult.begin("native", "val", "best.pt", "dataset.yaml", root)
            panel.show_result(run)
            self.assertFalse(panel.open_button.isEnabled())
            out = root / "val"
            out.mkdir()
            (out / "results.csv").write_text("results")
            run.observe(f"[save-dir] {out}")
            run.finish(0)
            panel.show_result(run)
            self.assertTrue(panel.open_button.isEnabled())
            (out / "results.csv").unlink()
            self.assertIsNone(run.verified_path())
            panel.close()

    def test_failed_export_never_enables_open(self):
        from custom_trainer.ui.widgets.task_result_panel import TaskResultPanel
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            panel = TaskResultPanel()
            run = TaskResult.begin("export", "export", "best.pt", "", root)
            artifact = root / "model.onnx"
            artifact.write_bytes(b"")
            run.observe(f"[export] {artifact}")
            run.finish(0)
            panel.show_result(run)
            self.assertFalse(panel.open_button.isEnabled())
            self.assertEqual(run.state, "Failed")
            panel.close()


if __name__ == "__main__":
    unittest.main()
