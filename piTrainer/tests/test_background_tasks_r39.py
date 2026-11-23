"""R39 regression tests: honest output reporting and worker lifecycle."""
from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path

from piTrainer.services.task_outputs import confirmed_dataset_paths, confirmed_model_paths


class OutputConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative: str, data: str = 'content'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8')
        return path

    def test_model_and_sidecar_are_both_reported(self):
        model = self.write('trained.keras')
        self.write('trained.keras.manifest.json', '{"schema_version":1}')
        self.assertEqual(confirmed_model_paths((model,)), (str(model), str(model) + '.manifest.json'))

    def test_empty_model_list_is_failure(self):
        with self.assertRaises(RuntimeError):
            confirmed_model_paths(())

    def test_missing_model_is_failure_even_with_manifest(self):
        self.write('missing.keras.manifest.json')
        with self.assertRaises(RuntimeError):
            confirmed_model_paths((self.root / 'missing.keras',))

    def test_missing_manifest_is_failure(self):
        model = self.write('unverified.keras')
        with self.assertRaises(RuntimeError):
            confirmed_model_paths((model,))

    def test_zero_byte_model_is_failure(self):
        model = self.write('empty.keras', '')
        self.write('empty.keras.manifest.json')
        with self.assertRaises(RuntimeError):
            confirmed_model_paths((model,))

    def test_zero_byte_manifest_is_failure(self):
        model = self.write('empty_manifest.tflite')
        self.write('empty_manifest.tflite.manifest.json', '')
        with self.assertRaises(RuntimeError):
            confirmed_model_paths((model,))

    def test_multiple_models_preserve_all_paths(self):
        models = [self.write(name) for name in ('model.keras', 'model.tflite')]
        for model in models:
            self.write(model.name + '.manifest.json')
        self.assertEqual(len(confirmed_model_paths(models)), 4)

    def test_model_paths_are_absolute(self):
        model = self.write('model.keras')
        self.write('model.keras.manifest.json')
        self.assertTrue(all(Path(p).is_absolute() for p in confirmed_model_paths((model,))))

    def test_complete_dataset_reports_folder_and_three_files(self):
        folder = self.root / 'preprocessed'
        for name in ('preprocessed_records.csv', 'preprocessed_records.jsonl', 'preprocess_recipe.json'):
            self.write('preprocessed/' + name)
        confirmed = confirmed_dataset_paths(folder)
        self.assertEqual(len(confirmed), 4)
        self.assertEqual(confirmed[0], str(folder))
        self.assertTrue(all(Path(p).exists() for p in confirmed))

    def test_uncreated_dataset_folder_is_failure(self):
        with self.assertRaises(RuntimeError):
            confirmed_dataset_paths(self.root / 'missing')

    def test_missing_dataset_jsonl_is_failure(self):
        self.write('preprocessed/preprocessed_records.csv')
        self.write('preprocessed/preprocess_recipe.json')
        with self.assertRaises(RuntimeError):
            confirmed_dataset_paths(self.root / 'preprocessed')

    def test_zero_byte_recipe_is_failure(self):
        self.write('preprocessed/preprocessed_records.csv')
        self.write('preprocessed/preprocessed_records.jsonl')
        self.write('preprocessed/preprocess_recipe.json', '')
        with self.assertRaises(RuntimeError):
            confirmed_dataset_paths(self.root / 'preprocessed')

    def test_affected_python_modules_parse(self):
        package = Path(__file__).resolve().parents[1] / 'piTrainer'
        paths = (
            'services/background_task.py',
            'services/task_outputs.py',
            'services/train/worker.py',
            'services/export/export_service.py',
            'panels/common/task_progress_panel.py',
            'pages/preprocess_page.py',
            'pages/train_page.py',
            'pages/validation_page.py',
            'pages/export_page.py',
            'pages/export_validation_page.py',
            'main_window.py',
        )
        for path in paths:
            with self.subTest(path=path):
                ast.parse((package / path).read_text(encoding='utf-8'), filename=path)


class OptionalQtWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('PySide6 is not installed')
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_worker_emits_success_and_step(self):
        from piTrainer.services.background_task import BackgroundTaskWorker
        successes, failures, steps = [], [], []

        def operation(report):
            report('Step 1 of 2', 50)
            return {'completed': True}

        worker = BackgroundTaskWorker(operation)
        worker.succeeded.connect(successes.append)
        worker.failed.connect(failures.append)
        worker.step_changed.connect(lambda step, pct: steps.append((step, pct)))
        worker.start()
        self.assertTrue(worker.wait(5000))
        self.app.processEvents()
        self.assertEqual(successes, [{'completed': True}])
        self.assertEqual(failures, [])
        self.assertIn(('Step 1 of 2', 50), steps)

    def test_worker_failure_does_not_emit_success(self):
        from piTrainer.services.background_task import BackgroundTaskWorker
        successes, failures = [], []

        def operation(report):
            report('Converting', None)
            raise RuntimeError('converter failed')

        worker = BackgroundTaskWorker(operation)
        worker.succeeded.connect(successes.append)
        worker.failed.connect(failures.append)
        worker.start()
        self.assertTrue(worker.wait(5000))
        self.app.processEvents()
        self.assertEqual(successes, [])
        self.assertEqual(failures, ['converter failed'])

    def test_progress_states_distinguish_outcomes(self):
        from piTrainer.panels.common.task_progress_panel import TaskProgressPanel
        panel = TaskProgressPanel()
        panel.begin('Test')
        self.assertEqual(panel.progress.minimum(), 0)
        self.assertEqual(panel.progress.maximum(), 0)
        panel.set_step('Half done', 50)
        self.assertEqual(panel.progress.value(), 50)
        panel.fail('incomplete')
        self.assertEqual(panel.step_label.text(), 'Failed')
        self.assertIn('No completed output', panel.result_label.text())
        panel.cancel('user stopped')
        self.assertEqual(panel.step_label.text(), 'Cancelled')
        panel.succeed('All done', ('/tmp/output',))
        self.assertIn('/tmp/output', panel.result_label.text())


if __name__ == '__main__':
    unittest.main()
