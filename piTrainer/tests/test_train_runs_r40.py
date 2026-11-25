"""R40 regression tests for run provenance, comparison and model associations."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from piTrainer.services.preprocess.applied_binding import AppliedPreprocessBinding
from piTrainer.services.validation.validation_receipts import save_validation_receipt, load_validation_receipts, evaluated_rows_hash

from piTrainer.services.train.experiment_service import (
    attach_model_artifact, comparison_rows, create_run_snapshot, finish_run,
    inspect_model_experiment, load_runs, preprocessing_hash, run_record_path,
    save_run_record, summarize_metrics,
)


class ExperimentServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.train_df = pd.DataFrame([
            {"session": "s1", "frame_id": "f1", "abs_image": "a.jpg",
             "steering": 0.1, "throttle": 0.5},
            {"session": "s2", "frame_id": "f2", "abs_image": "b.jpg",
             "steering": -0.1, "throttle": 0.7},
        ])
        self.val_df = pd.DataFrame([
            {"session": "s1", "frame_id": "f3", "abs_image": "c.jpg",
             "steering": 0.25, "throttle": 0.4},
        ])
        self.config = SimpleNamespace(
            split_mode="By session", seed=17, val_ratio=0.25,
            model_size="Small CNN", learning_rate=0.002,
            batch_size=32, epochs=50, img_h=120, img_w=160,
        )

    def snapshot(self, recipe=None):
        return create_run_snapshot(
            self.train_df, self.val_df, self.config,
            recipe, ["s1", "s2"], "",
        )

    def successful(self):
        return finish_run(self.snapshot({"mirror_enabled": True}),
                          "succeeded", {"loss": [1.2, 0.7],
                                         "val_loss": [1.5, 0.9]})

    def test_validation_receipts_preserve_run_identity_and_actual_rows(self):
        run = self.successful()
        result = {"rows_used": 1, "sessions": ["s1"], "frame_ids": ["f1"],
                  "source_frame_ids": [""], "abs_images": ["a.jpg"], "aug_flip_lr": [False],
                  "steering_true": [.1], "throttle_true": [.5], "steering_mae": .03,
                  "dataset_source": "Validation split", "model_kind": "Current trained model",
                  "experiment_context": {"run_id": run["run_id"], "status": "Tracked in-memory training run."}}
        first, path = save_validation_receipt(self.root, result)
        before = path.read_bytes()
        second, other = save_validation_receipt(self.root, result)
        self.assertNotEqual(path, other)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(first["training_run_id"], run["run_id"])
        self.assertIsNone(first["model_sha256"])
        self.assertEqual(first["evaluated_rows_sha256"], second["evaluated_rows_sha256"])
        self.assertIsNone(first["metrics"]["throttle_rmse"])
        result["steering_true"] = [.2]
        self.assertNotEqual(evaluated_rows_hash(result), first["evaluated_rows_sha256"])
        result["experiment_context"] = {"status": "Unknown"}
        result["abs_images"] = []
        unknown, _ = save_validation_receipt(self.root, result)
        self.assertIsNone(unknown["training_run_id"])
        self.assertIsNone(unknown["evaluated_rows_sha256"])
        self.assertEqual(len(load_validation_receipts(self.root)), 3)
        path.write_text("{bad", encoding="utf-8")
        self.assertEqual(len(load_validation_receipts(self.root)), 2)

    def test_applied_recipe_and_saved_path_follow_exact_active_metadata(self):
        binding = AppliedPreprocessBinding()
        recipe = {"mirror_enabled": True, "image_width": 160}
        binding.capture(self.train_df, recipe)
        recipe["image_width"] = 320
        applied, path = binding.training_context(self.train_df.copy())
        self.assertEqual(applied["image_width"], 160)
        self.assertEqual(path, "")
        folder = self.root / "preprocessed"
        folder.mkdir()
        for name in ("preprocessed_records.csv", "preprocessed_records.jsonl", "preprocess_recipe.json"):
            (folder / name).write_text("fixture", encoding="utf-8")
        binding.note_saved(self.train_df, recipe, folder)
        self.assertEqual(binding.training_context(self.train_df)[1], "")
        binding.note_saved(self.train_df, applied, folder)
        self.assertEqual(binding.training_context(self.train_df)[1], str(folder.resolve()))
        edited = self.train_df.copy()
        edited.loc[0, "steering"] = -0.5
        self.assertEqual(binding.training_context(edited), (None, ""))
        (folder / "preprocess_recipe.json").unlink()
        self.assertEqual(binding.training_context(self.train_df)[1], "")
        binding.clear()
        self.assertEqual(binding.training_context(self.train_df), (None, ""))

    def test_stable_uuid_run_id(self):
        record = self.snapshot()
        self.assertEqual(len(record["run_id"]), 32)
        self.assertTrue(all(c in "0123456789abcdef" for c in record["run_id"]))

    def test_actual_train_validation_counts_and_groups(self):
        record = self.snapshot()
        self.assertEqual((record["train_rows"], record["validation_rows"]), (2, 1))
        self.assertEqual(record["source_groups"], [
            {"session": "s1", "train_rows": 1, "validation_rows": 1},
            {"session": "s2", "train_rows": 1, "validation_rows": 0},
        ])
        self.assertEqual(record["selected_sessions"], ["s1", "s2"])

    def test_split_seed_and_model_settings_captured(self):
        record = self.snapshot()
        self.assertEqual(record["split"]["mode"], "By session")
        self.assertEqual(record["split"]["seed"], 17)
        self.assertEqual(record["model_settings"]["epochs"], 50)

    def test_zero_configured_seed_records_existing_effective_fallback(self):
        self.config.seed = 0
        record = self.snapshot()
        self.assertEqual(record["split"]["configured_seed"], 0)
        self.assertEqual(record["split"]["seed"], 42)
        self.assertEqual(record["split"]["training_seed_effective"], 42)

    def test_sequential_split_seed_is_not_fabricated(self):
        self.config.split_mode = "Sequential rows"
        record = self.snapshot()
        self.assertIsNone(record["split"]["seed"])
        self.assertEqual(record["split"]["training_seed_effective"], 17)

    def test_recipe_hash_order_independent(self):
        self.assertEqual(preprocessing_hash({"b": 2, "a": 1}),
                         preprocessing_hash({"a": 1, "b": 2}))
        self.assertEqual(len(preprocessing_hash({"a": 1})), 64)

    def test_missing_preprocess_is_unknown_not_default(self):
        self.assertIsNone(self.snapshot()["preprocessing_sha256"])
        self.assertIsNone(preprocessing_hash({}))

    def test_source_identity_fingerprint_changes_with_labels(self):
        first = self.snapshot()["split"]["identity_label_sha256"]
        self.train_df.loc[0, "steering"] = -0.25
        self.assertNotEqual(first, self.snapshot()["split"]["identity_label_sha256"])

    def test_source_identity_fingerprint_order_invariant(self):
        first = self.snapshot()["split"]["identity_label_sha256"]
        self.train_df = self.train_df.iloc[::-1].reset_index(drop=True)
        self.assertEqual(first, self.snapshot()["split"]["identity_label_sha256"])

    def test_missing_source_session_not_fabricated(self):
        self.train_df = self.train_df.drop(columns=["session"])
        self.val_df = self.val_df.drop(columns=["session"])
        self.assertIsNone(self.snapshot()["source_groups"])

    def test_metrics_best_and_final_not_confused(self):
        m = summarize_metrics({"loss": [0.8, 0.4, 0.5],
                               "val_loss": [0.6, 0.2, 0.3]})
        self.assertEqual(m["epochs_ran"], 3)
        self.assertEqual(m["best_val_loss"], 0.2)
        self.assertEqual(m["final_val_loss"], 0.3)

    def test_missing_metrics_are_unknown(self):
        m = summarize_metrics({"loss": [1.0]})
        self.assertIsNone(m["final_val_loss"])
        self.assertIsNone(m["best_val_loss"])

    def test_failed_and_cancelled_are_not_success(self):
        for status in ("failed", "cancelled"):
            with self.subTest(status=status):
                r = finish_run(self.snapshot(), status, {"loss": [0.3]})
                self.assertEqual(r["status"], status)
                self.assertTrue(r["metrics_partial"])
                self.assertEqual(r["metrics"]["final_loss"], 0.3)

    def test_invalid_outcome_rejected(self):
        with self.assertRaises(ValueError):
            finish_run(self.snapshot(), "half-finished")

    def test_atomic_write_and_reload_stable_id(self):
        record = self.successful()
        path = save_run_record(self.root, record)
        self.assertEqual(path.name, record["run_id"] + ".json")
        self.assertEqual(load_runs(self.root)[0]["run_id"], record["run_id"])
        self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_existing_summary_updated_without_duplicate(self):
        record = self.successful()
        save_run_record(self.root, record)
        updated = dict(record, error="added details")
        save_run_record(self.root, updated)
        rows = load_runs(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error"], "added details")

    def test_invalid_run_id_prevents_path_traversal(self):
        with self.assertRaises(ValueError):
            run_record_path(self.root, "../other")

    def test_corrupt_history_is_skipped(self):
        path = run_record_path(self.root, self.snapshot()["run_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{bad json", encoding="utf-8")
        self.assertEqual(load_runs(self.root), [])

    def test_foreign_file_not_loaded_as_run(self):
        path = self.root / "training_runs" / "notes.json"
        path.parent.mkdir(parents=True)
        path.write_text("{}", encoding="utf-8")
        self.assertEqual(load_runs(self.root), [])

    def test_load_runs_newest_first(self):
        a, b = self.successful(), self.successful()
        a["started_at_utc"], b["started_at_utc"] = "2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00"
        save_run_record(self.root, a)
        save_run_record(self.root, b)
        self.assertEqual([r["run_id"] for r in load_runs(self.root)], [b["run_id"], a["run_id"]])

    def test_comparison_reports_unknown_without_fabrication(self):
        rows = dict((name, (a, b)) for name, a, b
                    in comparison_rows(self.snapshot(), None))
        self.assertEqual(rows["Final validation loss"], ("Unknown", "Unknown"))
        self.assertEqual(rows["Effective split seed"][0], "17")
        self.assertEqual(rows["Preprocessing SHA-256"], ("Unknown", "Unknown"))

    def test_successful_comparison_uses_observed_val_loss(self):
        a, b = self.successful(), finish_run(
            self.snapshot(), "succeeded", {"loss": [0.8], "val_loss": [0.1]})
        rows = dict((name, (x, y)) for name, x, y in comparison_rows(a, b))
        self.assertEqual(rows["Best validation loss"], ("0.9", "0.1"))
        self.assertNotEqual(rows["Run ID"][0], rows["Run ID"][1])

    def test_legacy_model_sidecar_absent_is_unknown(self):
        path = self.root / "old.keras"
        path.write_bytes(b"model")
        record, note = inspect_model_experiment(path)
        self.assertIsNone(record)
        self.assertIn("Unknown", note)

    def test_artifact_sidecar_and_history_are_linked(self):
        record = self.successful()
        save_run_record(self.root, record)
        model = self.root / "trained.keras"
        model.write_bytes(b"model")
        with patch(
            "piTrainer.services.train.experiment_service.inspect_manifest",
            return_value=({"model_sha256": "a" * 64}, "verified"),
        ):
            linked, sidecar = attach_model_artifact(self.root, record, model)
            self.assertTrue(sidecar.is_file())
            self.assertEqual(load_runs(self.root)[0]["artifacts"], linked["artifacts"])
            restored, reason = inspect_model_experiment(model)
        self.assertEqual(restored["run_id"], record["run_id"])
        self.assertIn("Verified", reason)
        self.assertEqual(restored["model_binding"]["model_sha256"], "a" * 64)

    def test_duplicate_artifact_sidecar_fails_closed(self):
        record = self.successful()
        model = self.root / "trained.keras"
        model.write_bytes(b"model")
        with patch(
            "piTrainer.services.train.experiment_service.inspect_manifest",
            return_value=({"model_sha256": "a" * 64}, "verified"),
        ):
            attach_model_artifact(self.root, record, model)
            with self.assertRaises(FileExistsError):
                attach_model_artifact(self.root, record, model)

    def test_model_path_mismatch_is_unknown(self):
        record = self.successful()
        model = self.root / "trained.keras"
        model.write_bytes(b"model")
        with patch(
            "piTrainer.services.train.experiment_service.inspect_manifest",
            return_value=({"model_sha256": "a" * 64}, "verified"),
        ):
            _, sidecar = attach_model_artifact(self.root, record, model)
            data = json.loads(sidecar.read_text())
            data["model_binding"]["model_path"] = str(self.root / "other.keras")
            sidecar.write_text(json.dumps(data), encoding="utf-8")
            result, note = inspect_model_experiment(model)
        self.assertIsNone(result)
        self.assertIn("Unknown", note)

    def test_failed_run_cannot_be_linked_to_model(self):
        record = finish_run(self.snapshot(), "failed", {"loss": [0.2]})
        model = self.root / "trained.keras"
        model.write_bytes(b"model")
        with patch(
            "piTrainer.services.train.experiment_service.inspect_manifest",
            return_value=({"model_sha256": "a" * 64}, "verified"),
        ):
            with self.assertRaises(ValueError):
                attach_model_artifact(self.root, record, model)


if __name__ == "__main__":
    unittest.main()
