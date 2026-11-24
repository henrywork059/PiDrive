"""R50: native Qt validation edit markers belong to one validation result.

Use synthetic records, no user files or model training, and no real GUI display.
"""
import unittest

from PySide6.QtWidgets import QApplication

from piTrainer.panels.validation.validation_frame_review_panel import (
    ValidationFrameReviewPanel,
)


def fixture_result():
    return {
        "rows_used": 3,
        "frame_ids": ["f01", "s_f01", "f01"],
        "sessions": ["session-a", "session-a", "session-b"],
        "timestamps": ["t01", "t02", "t03"],
        "abs_images": ["/not-real/a/f01.jpg", "/not-real/a/s_f01.jpg",
                       "/not-real/b/f01.jpg"],
        "source_frame_ids": ["", "f01", ""],
        "synthetic_variants": ["", "flip_lr", ""],
        "aug_flip_lr": [False, True, False],
        "modes": ["manual", "manual", "manual"],
        "steering_true": [0.2, -0.2, 0.3],
        "steering_pred": [0.1, -0.1, 0.2],
        "throttle_true": [0.5, 0.5, 0.6],
        "throttle_pred": [0.4, 0.4, 0.5],
        "combined_error": [0.2, 0.2, 0.2],
    }


class ValidationMarkerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_panel(self, callback=None):
        panel = ValidationFrameReviewPanel(edit_in_data_callback=callback)
        self.addCleanup(panel.close)
        self.addCleanup(panel.deleteLater)
        return panel

    @staticmethod
    def status_for(panel, session, frame_id):
        matching = [row for row in panel.all_rows if row["session"] == session
                    and row["frame_id"] == frame_id]
        if len(matching) != 1:
            raise AssertionError((session, frame_id, matching))
        return matching[0].get("_validation_edit_status")

    def test_edit_markers_survive_refresh_but_reset_on_next_validation(self):
        panel = self.make_panel()
        first = fixture_result()
        panel.set_result(first)
        self.assertIsNone(self.status_for(panel, "session-a", "f01"))
        panel.mark_edited_records({
            "session": "session-a", "frame_id": "f01",
            "abs_image": "/not-real/a/f01.jpg",
        })
        self.assertEqual(self.status_for(panel, "session-a", "f01"), "edited")
        self.assertEqual(self.status_for(panel, "session-a", "s_f01"), "mirrored")
        self.assertIsNone(self.status_for(panel, "session-b", "f01"))
        # refresh_from_state() passes the same result object; keep markers.
        panel.set_result(first)
        self.assertEqual(self.status_for(panel, "session-a", "f01"), "edited")
        self.assertEqual(self.status_for(panel, "session-a", "s_f01"), "mirrored")
        # A new run creates a new result mapping even for the same records.
        panel.set_result(fixture_result())
        for session, frame_id in (("session-a", "f01"), ("session-a", "s_f01"),
                                  ("session-b", "f01")):
            self.assertIsNone(self.status_for(panel, session, frame_id))
        # Edits after the fresh run still create new, correctly scoped markers.
        panel.mark_edited_records({"session": "session-b", "frame_id": "f01"})
        self.assertEqual(self.status_for(panel, "session-b", "f01"), "edited")
        self.assertIsNone(self.status_for(panel, "session-a", "f01"))
        panel.set_result(None)
        panel.set_result(fixture_result())
        self.assertIsNone(self.status_for(panel, "session-b", "f01"))

    def test_edit_in_data_targets_original_selected_identity_after_resort(self):
        edits = []
        panel = self.make_panel(callback=lambda record: edits.append(record))
        panel.set_result(fixture_result())
        mirrored = next(row for row in panel.rows if row["frame_id"] == "s_f01")
        identity = panel._row_identity(mirrored)
        self.assertTrue(panel._select_row_identity(identity))
        self.assertEqual(panel.selected_row()["frame_id"], "s_f01")
        panel._edit_current_frame()
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["session"], "session-a")
        self.assertEqual(edits[0]["source_frame_id"], "f01")
        self.assertEqual(panel._pending_restore_identity, identity)
        panel.sort_combo.setCurrentText("Best first")
        panel.restore_pending_selection()
        self.assertEqual(panel._row_identity(panel.selected_row()), identity)


if __name__ == "__main__":
    unittest.main()
