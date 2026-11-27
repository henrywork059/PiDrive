"""R46 source-level copy regression. No Qt/TensorFlow imports required."""
from __future__ import annotations
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "piTrainer"


def source(path: str) -> str:
    file = APP / path
    data = file.read_text(encoding="utf-8")
    ast.parse(data, filename=str(file))
    return data


class UserCopyR46(unittest.TestCase):
    def test_data_no_sessions_points_to_browse_and_refresh(self):
        text = source("panels/data/session_source_panel.py")
        self.assertIn("No sessions loaded. Choose a records root, then Refresh.", text)
        self.assertIn("No sessions found. Choose another folder, then Refresh.", text)
        self.assertIn("QPushButton('Browse')", text)
        self.assertIn("QPushButton('Refresh')", text)

    def test_export_no_trained_model_points_to_train(self):
        text = source("pages/export_page.py")
        self.assertIn("No model to export. Open Train and complete training first.", text)

    def test_export_busy_copy_does_not_claim_success(self):
        text = source("pages/export_page.py")
        self.assertIn("Export in progress. Wait for completion", text)
        self.assertIn("self.task_runner.active", text)

    def test_export_failure_explicitly_warns_unconfirmed_files(self):
        text = source("pages/export_page.py")
        self.assertIn("Export failed. Review Export Log, then retry; partial files are not confirmed.", text)
        self.assertIn("on_failure=failed", text)

    def test_tflite_check_no_rows_or_missing_model_is_actionable(self):
        text = source("pages/export_validation_page.py")
        self.assertIn("No rows in this dataset. Load sessions in Data", text)
        self.assertIn("No exported .tflite model selected. Export first or browse", text)
        self.assertIn("No TFLite check yet. Choose a .tflite model, then Run TFLite Check.", text)

    def test_tflite_check_failure_points_to_log_not_dummy_success(self):
        text = source("pages/export_validation_page.py")
        self.assertIn("TFLite check failed. Review the Check Log, then retry.", text)
        self.assertIn("self.task_runner", text)

    def test_forward_version_preserves_existing_patcher(self):
        text = source("version.py")
        app = re.search(r'APP_VERSION\s*=\s*"((?:0\.11|1\.0)\.\d+)"', text)
        patch = re.search(r'PATCH_VERSION\s*=\s*"piTrainer_((?:0_11|1_0)_\d+)"', text)
        self.assertIsNotNone(app)
        self.assertIsNotNone(patch)
        parts = tuple(map(int, app.group(1).split(".")))
        self.assertTrue(parts[:2] == (1, 0) or (parts[:2] == (0, 11) and parts[2] >= 9))
        self.assertEqual(app.group(1).replace(".", "_"), patch.group(1))


if __name__ == "__main__":
    unittest.main()
