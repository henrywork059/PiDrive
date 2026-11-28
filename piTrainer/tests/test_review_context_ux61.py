import unittest
from piTrainer.services.data.review_context import bulk_preview, prediction_pair, comparison_text

class ReviewContextTests(unittest.TestCase):
    def test_preview_exact_rows_and_missing_labels(self):
        rows=[{'session':'A','frame_id':'f1','steering':.25},
              {'session':'B','frame_id':'f1','steering':float('nan')},
              {'session':'C','frame_id':'f3','steering':.3}]
        text=bulk_preview(rows,'steering',-.5,limit=2)
        self.assertIn('A / f1: 0.250 → -0.500',text)
        self.assertIn('B / f1: Unknown → -0.500',text)
        self.assertIn('1 more selected',text)
        self.assertNotIn('C / f3',text)
        self.assertEqual(rows[0]['steering'],.25)
    def test_missing_predictions_not_zero_or_nan(self):
        for row in ({},{'pred_steering':float('nan'),'pred_throttle':.5},
                    {'pred_steering':None,'pred_speed':0}):
            self.assertIsNone(prediction_pair(row))
            self.assertIn('unavailable',comparison_text(row))
    def test_live_label_delta_changes_without_mutating_prediction(self):
        row={'steering':.5,'throttle':.25,'pred_steering':.25,'pred_speed':.5}
        self.assertIn('Δ AI−label -0.250/0.250',comparison_text(row))
        row['steering']=.25
        self.assertIn('Δ AI−label 0.000/0.250',comparison_text(row))
        self.assertEqual(row['pred_steering'],.25)


from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QMainWindow, QTabWidget, QWidget, QLineEdit, QVBoxLayout
from piTrainer.main_window import MainWindow
from unittest.mock import patch
from types import SimpleNamespace
import pandas as pd
from piTrainer.panels.data.image_preview_panel import ImagePreviewPanel
from piTrainer.panels.data.bulk_edit_panel import BulkEditPanel
from piTrainer.panels.data.preview_panel import PreviewPanel
from piTrainer.pages.data_page_filter_edit import DataPageFilterEditMixin

class NativeReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_compare_tracks_same_source_after_sort_and_filter(self):
        image=ImagePreviewPanel()
        table=PreviewPanel(selection_callback=image.set_record)
        self.addCleanup(image.close)
        self.addCleanup(table.close)
        rows=[dict(session='A',frame_id='f1',ts='1',abs_image='a.jpg',steering=.5,throttle=.25,pred_steering=.25,pred_throttle=.5),
              dict(session='B',frame_id='f1',ts='2',abs_image='b.jpg',steering=-.5,throttle=.25,pred_steering=-.25,pred_throttle=.5)]
        frame=pd.DataFrame(rows)
        table.set_dataframe(frame)
        identity=table.record_identity(rows[1])
        table.select_record_identity(identity)
        self.assertEqual(image.current_record['session'],'B')
        self.assertIn('0.250/0.250',image.comparison_label.text())
        table.model.sort(0,Qt.DescendingOrder)
        self.assertEqual(image.current_record['session'],'B')
        image.show()
        self.app.processEvents()
        image.compare_check.setFocus()
        QTest.keyClick(image.compare_check,Qt.Key_Space)
        self.assertFalse(image.compare_check.isChecked())
        self.assertTrue(image.comparison_label.isHidden())
        QTest.keyClick(image.compare_check,Qt.Key_Space)
        self.assertTrue(image.compare_check.isChecked())
        table.set_dataframe(frame.iloc[:1])
        self.assertEqual(image.current_record['session'],'A')
        self.assertIn('-0.250/0.250',image.comparison_label.text())
        table.set_dataframe(frame.iloc[:0])
        self.assertIn('Select a frame',image.comparison_label.text())

    def test_visible_preprocess_scope_and_sorted_position(self):
        from piTrainer.pages.preprocess_page import PreprocessPage
        from piTrainer.panels.preprocess.preprocess_filter_panel import PreprocessFilterPanel
        from piTrainer.app_state import AppState
        state = AppState()
        rows = [dict(session='A', frame_id='f1', ts='1', abs_image='a.jpg', steering=.5, throttle=.2),
                dict(session='B', frame_id='f1', ts='2', abs_image='b.jpg', steering=-.5, throttle=.2)]
        state.dataset_df = pd.DataFrame(rows)
        state.filtered_df = state.dataset_df.copy()
        table = PreviewPanel()
        self.addCleanup(table.close)
        table.set_dataframe(state.dataset_df)
        filters = PreprocessFilterPanel(state)
        self.addCleanup(filters.close)
        harness = SimpleNamespace(state=state, filter_panel=filters,
            main_window=SimpleNamespace(data_page=SimpleNamespace(preview_panel=table)))
        table.select_record_identity(table.record_identity(rows[0]))
        table.model.sort(table.model.columns.index('steering'), Qt.AscendingOrder)
        self.assertIn('row 2/2', table.summary_label.text())
        self.assertEqual(table.selected_record()['session'], 'A')
        before = PreprocessPage._source_identity(harness)
        table.update_record_values(table.record_identity(rows[0]), {'steering': .6})
        self.assertNotEqual(before, PreprocessPage._source_identity(harness))
        table.set_dataframe(state.dataset_df.iloc[:0])
        self.assertTrue(PreprocessPage._source_df(harness).empty)
        self.assertEqual(len(state.filtered_df), 2)
        filters.source_combo.setCurrentText('All loaded rows')
        self.assertEqual(len(PreprocessPage._source_df(harness)), 2)

    def test_live_bulk_preview_is_read_only_and_tracks_selection(self):
        actions = []
        panel = BulkEditPanel(actions.append, actions.append)
        self.addCleanup(panel.close)
        rows = [dict(session='A', frame_id='f1', steering=.1, throttle=.2),
                dict(session='B', frame_id='f1', steering=-.3, throttle=None),
                dict(session='C', frame_id='f2', steering=.5, throttle=.4)]
        panel.set_selected_records(rows)
        panel.steering_spin.setValue(.7)
        panel.speed_slider.setValue(400)
        text = panel.change_preview.text()
        self.assertIn('3 selected', text)
        self.assertIn('A / f1: S 0.100 → 0.700; T 0.200 → 0.400', text)
        self.assertIn('B / f1: S -0.300 → 0.700; T Unknown → 0.400', text)
        self.assertIn('1 more selected', text)
        self.assertFalse(panel.apply_steering_btn.isEnabled())
        self.assertEqual(actions, [])
        self.assertEqual(rows[0]['steering'], .1)
        panel.set_selected_records(rows[1:2])
        self.assertNotIn('A / f1', panel.change_preview.text())
        panel.set_selected_count(0)
        self.assertIn('Select visible frames', panel.change_preview.text())
        self.assertEqual(actions, [])

    def test_bulk_cancel_names_exact_rows_and_never_writes(self):
        selected=[dict(session='A',frame_id='f1',steering=.1),dict(session='B',frame_id='f1',steering=.2)]
        shell=SimpleNamespace(preview_panel=SimpleNamespace(stop_autoplay=lambda:None,selected_records=lambda:selected),
            bulk_edit_panel=SimpleNamespace(bulk_edit_confirmed=lambda:True),
            state=SimpleNamespace(dataset_df=pd.DataFrame(selected+[dict(session='C',frame_id='f1')])),
            main_window=SimpleNamespace(set_status_message=lambda _:None))
        with patch('piTrainer.pages.data_page_filter_edit.QMessageBox.warning',return_value=QMessageBox.No) as confirm, patch('piTrainer.pages.data_page_filter_edit.update_frame_controls_batch') as write:
            DataPageFilterEditMixin._apply_bulk_control_edit(shell,field_name='steering',field_label='steering',value=.7)
        message=confirm.call_args.args[2]
        self.assertIn('2 selected visible',message)
        self.assertIn('A / f1: 0.100 → 0.700',message)
        self.assertIn('B / f1: 0.200 → 0.700',message)
        self.assertNotIn('C / f1',message)
        write.assert_not_called()


class ShortcutHarness(QMainWindow):
    """Real Qt controls and production bindings; callbacks cannot modify user data."""
    show_shortcuts = MainWindow.show_shortcuts
    _make_shortcuts_button = MainWindow._make_shortcuts_button
    next_tab = MainWindow.next_tab
    previous_tab = MainWindow.previous_tab

    def __init__(self):
        super().__init__()
        self.actions = []
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.data_page = QWidget()
        self.editor = QLineEdit()
        QVBoxLayout(self.data_page).addWidget(self.editor)
        self.data_page.refresh_sessions = lambda: self.actions.append('refresh')
        self.data_page.load_selected_sessions = lambda: self.actions.append('load')
        self.data_page.delete_selected_frame = lambda: self.actions.append('hide')
        self.data_page.purge_hidden_frames_shortcut = lambda: self.actions.append('purge')
        self.data_page.session_list_panel = SimpleNamespace(
            select_all=lambda: self.actions.append('select'),
            clear_all=lambda: self.actions.append('clear'))
        self.train_page = QWidget()
        self.train_page.prepare_split = lambda: self.actions.append('split')
        self.train_page.start_training = lambda: self.actions.append('train')
        self.train_page.stop_training = lambda: self.actions.append('stop')
        self.export_page = QWidget()
        self.export_page.export_model = lambda: self.actions.append('export')
        self.export_validation_page = QWidget()
        self.export_validation_page.validate_export = lambda: self.actions.append('validate')
        for page, name in (
            (self.data_page, '1 Data'), (QWidget(), '2 Preprocess'),
            (self.train_page, '3 Train'), (QWidget(), '4 Validate'),
            (self.export_page, '5 Export'), (self.export_validation_page, '6 TFLite Check'),
        ):
            self.tabs.addTab(page, name)
        self.help_button = self._make_shortcuts_button()
        self.statusBar().addPermanentWidget(self.help_button)
        MainWindow._setup_shortcuts(self)

    def reset_current_page_layout(self):
        self.actions.append('reset')


class NativeShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_context_help_button_and_f1_leave_text_entry_and_actions_unchanged(self):
        shell = ShortcutHarness()
        self.addCleanup(shell.close)
        self.addCleanup(shell.deleteLater)
        shell.resize(900, 600)
        shell.show()
        shell.activateWindow()
        self.app.processEvents()
        shell.editor.setFocus()
        self.app.processEvents()
        QTest.keyClicks(shell.editor, 'one two')
        self.assertEqual(shell.editor.text(), 'one two')
        self.assertEqual(shell.actions, [])
        with patch('piTrainer.main_window.QMessageBox.information') as info:
            QTest.mouseClick(shell.help_button, Qt.LeftButton)
            self.assertEqual(info.call_count, 1)
            data_help = info.call_args.args[2]
            self.assertIn('Confirm Hide', data_help)
            self.assertIn('Permanent purge', data_help)
            self.assertIn('Previous / next frame', data_help)
            self.assertIn('Play / Stop / Restart', data_help)
            shell.tabs.setCurrentIndex(2)
            shell.tabs.tabBar().setFocus()
            self.app.processEvents()
            QTest.keyClick(shell.tabs.tabBar(), Qt.Key_F1)
            self.assertEqual(info.call_count, 2)
            train_help = info.call_args.args[2]
            self.assertIn('Ctrl+R → Start training', train_help)
            self.assertNotIn('Permanent purge', train_help)
            self.assertIn('Global navigation', train_help)
        self.assertEqual(shell.actions, [])
