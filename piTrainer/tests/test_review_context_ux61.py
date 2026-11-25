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
