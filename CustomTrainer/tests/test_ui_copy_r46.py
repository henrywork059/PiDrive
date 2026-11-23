"""R46 concise action and empty-state smoke tests using stdlib AST only."""
from __future__ import annotations
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_trainer"


def source(path: str) -> str:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    ast.parse(text, filename=str(file))
    return text


class EmptyStatesR46(unittest.TestCase):
    def test_native_validate_missing_model_is_actionable(self):
        text = source("ui/pages/validate_page.py")
        self.assertIn("Choose a trained .pt model first.", text)
        self.assertIn("then Run Validation.", text)

    def test_exported_validate_names_distinct_model_and_action(self):
        text = source("ui/pages/export_validate_page.py")
        self.assertIn("Export or browse to a model first.", text)
        self.assertIn("then Run Exported Validation.", text)

    def test_both_preview_panels_describe_no_source_and_missing_directory(self):
        for path in ("ui/pages/validate_page.py", "ui/pages/export_validate_page.py"):
            with self.subTest(page=path):
                text = source(path)
                self.assertIn("No preview source. Choose images, then Run Prediction.", text)
                self.assertIn("Preview source missing. Browse to an existing image folder.", text)

    def test_busy_operations_say_wait_or_stop(self):
        for path in ("ui/pages/validate_page.py", "ui/pages/export_validate_page.py"):
            with self.subTest(page=path):
                text = source(path)
                self.assertIn("Stop it or wait before starting another.", text)
                self.assertIn("self.worker", text)

    def test_no_predictions_says_run_prediction(self):
        for path in ("ui/pages/validate_page.py", "ui/pages/export_validate_page.py"):
            with self.subTest(page=path):
                self.assertIn("No predictions yet. Run Prediction to create preview frames.", source(path))

    def test_pi_deploy_is_copy_bundle_not_live_motor_deploy(self):
        text = source("ui/pages/pi_deploy_page.py")
        self.assertIn("Pi deployment bundle", text)
        self.assertIn("Bundle saved for copying to the Pi:", text)
        self.assertIn("Export a .tflite model first", text)

    def test_r42_verified_result_panel_is_intact(self):
        for path in ("ui/pages/validate_page.py", "ui/pages/export_validate_page.py"):
            self.assertIn("TaskResultPanel(self)", source(path))
        self.assertIn("TaskResultPanel(self)", source("ui/pages/export_page.py"))

    def test_component_version_advances_without_new_scheme(self):
        text = source("ui/main_window.py")
        self.assertIn("CustomTrainer 0_2_17", text)


if __name__ == "__main__":
    unittest.main()
