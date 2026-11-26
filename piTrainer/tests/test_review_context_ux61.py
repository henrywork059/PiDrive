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
from PySide6.QtWidgets import QApplication, QMessageBox
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
