"""Native Qt accessibility and TFLite file-selection regressions."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget
import pandas as pd
from types import SimpleNamespace
from piTrainer.main_window import MainWindow

from piTrainer.app_state import AppState
from piTrainer.panels.validation.validation_config_panel import ValidationConfigPanel
from piTrainer.panels.train.train_config_panel import TrainConfigPanel
from piTrainer.panels.export.model_status_panel import ModelStatusPanel
from piTrainer.pages.export_page import ExportPage
from piTrainer.panels.export_validation.export_validation_config_panel import ExportValidationConfigPanel


class ValidationControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_named_controls_keyboard_selection(self):
        state=AppState()
        for panel, expected in (
            (ValidationConfigPanel(state), ('model_source_combo','model_path_edit','dataset_source_combo','batch_spin','max_rows_spin')),
            (ExportValidationConfigPanel(state), ('tflite_path_edit','dataset_source_combo','batch_spin','max_rows_spin')),
        ):
            self.addCleanup(panel.close)
            panel.show()
            self.app.processEvents()
            for field in expected:
                self.assertTrue(getattr(panel,field).accessibleName().strip(),field)
            combo=panel.dataset_source_combo
            combo.setFocus()
            QTest.keyClick(combo,Qt.Key_Down)
            self.assertEqual(combo.currentText(),'Validation split')

    def test_workflow_markers_preserve_six_tabs_and_reflect_selected_inputs(self):
        shell=QMainWindow()
        self.addCleanup(shell.close)
        shell.state=AppState()
        shell.tabs=QTabWidget(shell)
        titles=['1 Data','2 Preprocess','3 Train','4 Validate','5 Export','6 TFLite Check']
        for title in titles:
            shell.tabs.addTab(QWidget(),title)
        validation=ValidationConfigPanel(shell.state)
        check=ExportValidationConfigPanel(shell.state)
        self.addCleanup(validation.close)
        self.addCleanup(check.close)
        shell.validation_page=SimpleNamespace(config_panel=validation)
        shell.export_validation_page=SimpleNamespace(config_panel=check)
        def refresh():
            MainWindow.refresh_workflow_readiness(shell)
        refresh()
        self.assertTrue(all(shell.tabs.tabToolTip(i).startswith('Needs input') for i in range(6)))
        shell.state.filtered_df=pd.DataFrame([{'frame_id':'fixture'}])
        shell.state.model=object()
        refresh()
        self.assertTrue(all(shell.tabs.tabToolTip(i).startswith('Inputs available') for i in range(5)))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.tflite'
            check.set_tflite_path(str(path))
            refresh()
            self.assertTrue(shell.tabs.tabToolTip(5).startswith('Needs input'))
            path.mkdir()
            refresh()
            self.assertTrue(shell.tabs.tabToolTip(5).startswith('Needs input'))
            path.rmdir()
            path.write_bytes(b'fixture')
            refresh()
            self.assertIn('file validity not implied',shell.tabs.tabToolTip(5))
            shell.export_validation_page.last_result = {'rows_used': 1}
            refresh()
            self.assertIn('previous result available',shell.tabs.tabToolTip(5))
            path.unlink()
            refresh()
            self.assertTrue(shell.tabs.tabToolTip(5).startswith('Needs input'))
            validation.model_source_combo.setCurrentText('Load .keras / .h5 model')
            keras = Path(tmp) / 'fixture.keras'
            validation.model_path_edit.setText(str(keras))
            refresh()
            self.assertTrue(shell.tabs.tabToolTip(3).startswith('Needs input'))
            keras.write_bytes(b'fixture')
            refresh()
            self.assertTrue(shell.tabs.tabToolTip(3).startswith('Inputs available'))
        validation.dataset_source_combo.setCurrentText('Validation split')
        refresh()
        self.assertTrue(shell.tabs.tabToolTip(3).startswith('Needs input'))
        self.assertEqual([shell.tabs.tabText(i) for i in range(6)],titles)

    def test_training_fields_have_names_and_native_keyboard_input(self):
        state = AppState()
        panel = TrainConfigPanel(state)
        self.addCleanup(panel.close)
        panel.show()
        self.app.processEvents()
        for name in ('img_h', 'img_w', 'val_ratio', 'split_mode', 'seed', 'model_size',
                     'dropout_rate', 'steering_loss_weight', 'throttle_loss_weight', 'clipnorm',
                     'l2_reg', 'batch_size', 'epochs', 'learning_rate', 'early_stopping_patience',
                     'reduce_lr_patience', 'reduce_lr_factor', 'compute_device', 'review_sample_count'):
            self.assertTrue(getattr(panel, name).accessibleName().strip(), name)
        panel.img_h.setFocus()
        previous = panel.img_h.value()
        QTest.keyClick(panel.img_h, Qt.Key_Up)
        self.assertEqual(panel.img_h.value(), previous + 1)
        panel.push_to_state()
        self.assertEqual(state.train_config.img_h, previous + 1)

    def test_export_status_uses_bound_run_not_mutable_split(self):
        state = AppState()
        state.model = object()
        state.train_df = pd.DataFrame([{'frame_id': 'new'}])
        state.history = {'loss': [1.0]}
        panel = ModelStatusPanel()
        self.addCleanup(panel.close)
        run = {'run_id': 'a'*32, 'train_rows': 13, 'validation_rows': 7, 'metrics': {'epochs_ran': 4}}
        train = SimpleNamespace(provenance_for_model=lambda model: (run, Path('.')) if model is state.model else None)
        shell = SimpleNamespace(state=state, model_status_panel=panel, main_window=SimpleNamespace(train_page=train))
        ExportPage.refresh_from_state(shell)
        self.assertEqual(panel.train_rows.text(), '13')
        self.assertEqual(panel.val_rows.text(), '7')
        self.assertEqual(panel.epochs_ran.text(), '4')
        self.assertEqual(panel.run_id.toolTip(), 'a'*32)
        train.provenance_for_model = lambda model: None
        ExportPage.refresh_from_state(shell)
        self.assertEqual(panel.train_rows.text(), 'Unknown')
        self.assertEqual(panel.run_id.text(), 'Unknown')

    def test_latest_ignores_empty_path_and_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=AppState()
            state.export_config.out_dir=tmp
            panel=ExportValidationConfigPanel(state)
            self.addCleanup(panel.close)
            (Path(tmp)/'folder.tflite').mkdir()
            target=Path(tmp)/'actual.tflite'
            target.write_bytes(b'fixture')
            panel.fill_from_export_dir()
            self.assertEqual(Path(panel.tflite_path()),target)
            state.last_exported_tflite_path=str(Path(tmp)/'folder.tflite')
            panel.fill_from_export_dir()
            self.assertEqual(Path(panel.tflite_path()),target)
            validation=ValidationConfigPanel(state)
            self.addCleanup(validation.close)
            (Path(tmp)/'z.keras').mkdir()
            actual=Path(tmp)/'a.keras'
            actual.write_bytes(b'fixture')
            validation.fill_from_export_dir()
            self.assertEqual(Path(validation.model_path()),actual)


if __name__=='__main__':
    unittest.main()
