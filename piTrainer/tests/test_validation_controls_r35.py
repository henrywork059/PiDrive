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
from piTrainer.utils.model_manifest import make_manifest, write_manifest

from piTrainer.app_state import AppState
from piTrainer.panels.validation.validation_config_panel import ValidationConfigPanel
from piTrainer.panels.train.train_config_panel import TrainConfigPanel
from piTrainer.panels.export.model_status_panel import ModelStatusPanel
from piTrainer.pages.export_page import ExportPage
from piTrainer.panels.train.train_history_panel import TrainHistoryPanel
from piTrainer.panels.train.train_comparison_panel import TrainComparisonPanel
from piTrainer.panels.validation.validation_plot_panel import ValidationPlotPanel
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
        self.assertTrue(shell.tabs.tabToolTip(0).startswith('Done'))
        self.assertTrue(shell.tabs.tabToolTip(2).startswith('Done'))
        self.assertTrue(all(shell.tabs.tabToolTip(i).startswith('Inputs available') for i in (1, 3, 4)))
        shell.preprocess_page = SimpleNamespace(_preprocess_applied=True)
        refresh()
        self.assertTrue(shell.tabs.tabToolTip(1).startswith('Done'))
        shell.preprocess_page._preprocess_applied = False
        refresh()
        self.assertTrue(shell.tabs.tabToolTip(1).startswith('Inputs available'))
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

    def test_confirmed_export_marker_belongs_to_model_and_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = object()
            path = Path(tmp) / 'export.tflite'
            manifest = Path(str(path) + '.manifest.json')
            shell = SimpleNamespace(_confirmed_export_model=model,
                                    _confirmed_export_paths=(str(path), str(manifest)))
            self.assertFalse(ExportPage.has_confirmed_export_for(shell, model))
            path.write_bytes(b'model')
            manifest.write_bytes(b'{}')
            self.assertTrue(ExportPage.has_confirmed_export_for(shell, model))
            self.assertFalse(ExportPage.has_confirmed_export_for(shell, object()))
            manifest.unlink()
            self.assertFalse(ExportPage.has_confirmed_export_for(shell, model))

    def test_single_run_inspection_shows_local_validation_receipts(self):
        panel = TrainComparisonPanel(lambda: None)
        self.addCleanup(panel.close)
        run = {'run_id':'a'*32, 'status':'succeeded'}
        panel.set_records([run], [{'training_run_id':'a'*32, 'receipt_path':'local-check.json'},
                                  {'training_run_id':'b'*32, 'receipt_path':'unrelated.json'}])
        self.assertGreater(panel.table.rowCount(), 0)
        row = panel.table.rowCount() - 1
        self.assertIn('local-check.json', panel.table.item(row, 1).text())
        self.assertNotIn('unrelated.json', panel.table.item(row, 1).text())
        panel.set_records([run], [])
        self.assertIn('Unknown', panel.table.item(panel.table.rowCount()-1, 1).text())

    def test_portable_model_inspection_shows_exact_hash_without_replacing_local_run(self):
        panel = TrainComparisonPanel(lambda: None)
        self.addCleanup(panel.close)
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / 'portable.tflite'
            model.write_bytes(b'fixture')
            run_id = 'a' * 32
            claim = {'run_id':run_id, 'preprocessing_sha256':'b'*64,
                     'identity_label_sha256':'c'*64, 'train_rows':13,
                     'validation_rows':7, 'source_group_count':2}
            manifest = make_manifest(model, model_kind='steering_control', width=160,
                                     height=120, experiment=claim)
            write_manifest(model, manifest)
            digest = manifest['model_sha256']
            local = {'run_id':run_id, 'status':'succeeded', 'train_rows':99}
            panel.set_records([local], [
                {'training_run_id':run_id, 'model_sha256':'e'*64, 'receipt_path':'other-model.json'},
                {'training_run_id':None, 'model_sha256':digest, 'validation_id':'d'*32,
                 'receipt_path':'exact-model.json'}])
            panel.inspect_model_path(str(model))
            values = {panel.table.item(i,0).text(): panel.table.item(i,1).text()
                      for i in range(panel.table.rowCount())}
            self.assertIn('Portable experiment claim', panel.info.text())
            self.assertEqual(values['Training rows'], '13')
            self.assertEqual(values['Source sessions'], 'Unknown')
            self.assertEqual(values['Source group count'], '2')
            self.assertEqual(values['Selected model SHA-256'], digest)
            self.assertIn('exact-model.json', values['Local checks of this file hash (latest 5)'])
            self.assertNotIn('other-model.json', values['Local checks of this file hash (latest 5)'])
            self.assertEqual(panel._records[run_id]['train_rows'], 99)
            self.assertEqual(panel.run_a.count(), 1)
            panel._render()
            self.assertNotIn('Portable experiment claim', panel.info.text())
            model.write_bytes(b'tampered')
            panel.inspect_model_path(str(model))
            self.assertEqual(panel.table.rowCount(), 0)
            self.assertIn('Unknown', panel.info.text())

    def test_plot_context_does_not_retain_old_run_or_model(self):
        history = TrainHistoryPanel()
        self.addCleanup(history.close)
        run = {'run_id': 'a'*32, 'status': 'succeeded', 'source_groups': [{'session':'recording-a'}],
               'split': {'identity_label_sha256':'e'*64}, 'preprocessing_sha256':'f'*64,
               'train_rows': 13, 'validation_rows': 7, 'artifacts': [{'model_path':'example.keras'}]}
        history.set_run_context(run)
        self.assertIn('Train: 13', history.context_label.text())
        self.assertIn('example.keras', history.context_label.text())
        self.assertTrue(history.copy_paths_btn.isEnabled())
        history.copy_paths_btn.click()
        self.assertIn('example.keras', QApplication.clipboard().text())
        self.assertIn('a'*32, history.context_label.toolTip())
        self.assertIn('e'*64, history.context_label.toolTip())
        self.assertIn('recording-a', history.context_label.toolTip())
        self.assertIn('f'*64, history.context_label.toolTip())
        history.append_epoch_metrics({'epoch':1, 'loss':1.0})
        history.append_epoch_metrics({'epoch':3, 'loss':0.5, 'val_loss':0.7})
        self.assertEqual(history.history['loss'], [1.0, None, 0.5])
        self.assertEqual(history.history['val_loss'], [None, None, 0.7])
        self.assertIn('dimensionless', history.figure.axes[0].get_ylabel())
        for line in history.figure.axes[0].lines:
            self.assertEqual(list(line.get_xdata()), [1, 2, 3])
        history.set_run_context(None)
        self.assertNotIn('example.keras', history.context_label.text())
        self.assertEqual(history.context_label.toolTip(), '')
        self.assertFalse(history.copy_paths_btn.isEnabled())
        panel = ValidationPlotPanel()
        self.addCleanup(panel.close)
        panel.set_result({'dataset_source':'Validation split', 'model_kind':'TFLite',
                          'model_path':'fixture.tflite', 'experiment_context':{'run_id':'b'*32, 'model_sha256':'c'*64},
                          'validation_receipt':{'id':'d'*32, 'path':'local-check.json', 'rows_sha256':'e'*64},
                          'rows_used':2, 'steering_mae':.1, 'throttle_mae':.2,
                          'steering_true':[0,.1], 'throttle_true':[.2,.3],
                          'steering_pred':[0,.2], 'throttle_pred':[.2,.4],
                          'steering_error':[0,.1], 'throttle_error':[0,.1]})
        self.assertIn('fixture.tflite', panel.summary_label.text())
        self.assertIn('local-check.json', panel.summary_label.text())
        self.assertTrue(panel.copy_paths_btn.isEnabled())
        panel.copy_paths_btn.click()
        self.assertEqual(QApplication.clipboard().text().splitlines(), ['fixture.tflite', 'local-check.json'])
        self.assertIn('c'*64, panel.summary_label.toolTip())
        self.assertIn('d'*32, panel.summary_label.toolTip())
        self.assertIn('e'*64, panel.summary_label.toolTip())
        self.assertIn('normalized', panel.figure.axes[0].get_xlabel())
        panel.plot_type_combo.setCurrentIndex(1)
        self.assertEqual(panel.figure.axes[0].get_ylabel(), 'Frame count')
        panel.plot_type_combo.setCurrentIndex(2)
        self.assertIn('frame', panel.figure.axes[0].get_xlabel())
        self.assertIn('e'*64, panel.summary_label.toolTip())
        panel.set_result(None)
        self.assertNotIn('fixture.tflite', panel.summary_label.text())
        self.assertEqual(panel.summary_label.toolTip(), '')
        self.assertFalse(panel.copy_paths_btn.isEnabled())

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
