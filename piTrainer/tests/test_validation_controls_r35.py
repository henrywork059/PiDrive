"""Native Qt accessibility and TFLite file-selection regressions."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from piTrainer.app_state import AppState
from piTrainer.panels.validation.validation_config_panel import ValidationConfigPanel
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


if __name__=='__main__':
    unittest.main()
