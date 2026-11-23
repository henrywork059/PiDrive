"""R41 annotation efficiency and non-destructive per-frame edit regressions."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from custom_trainer.services.annotation_history import BoxHistory, clone_boxes, make_snapshot
from custom_trainer.services.yolo_io import PixelBox


def box(class_id=1, dx=0.0):
    return PixelBox(class_id, dx, 2.0, dx + 12.0, 24.0)


class HistoryTests(unittest.TestCase):
    def test_empty_history_has_no_undo(self):
        history = BoxHistory()
        self.assertFalse(history.can_undo)
        self.assertIsNone(history.undo([], None))

    def test_draw_undo_redo(self):
        history = BoxHistory()
        current = [box()]
        self.assertTrue(history.record([], None, current, 0))
        prior, selected = history.undo(current, 0)
        self.assertEqual(prior, [])
        self.assertIsNone(selected)
        updated, selected = history.redo(prior, selected)
        self.assertEqual(updated, current)
        self.assertEqual(selected, 0)

    def test_delete_restores_selection(self):
        history = BoxHistory()
        before = [box(), box(2, 20)]
        history.record(before, 1, [before[0]], None)
        restored, selected = history.undo([before[0]], None)
        self.assertEqual(restored, before)
        self.assertEqual(selected, 1)

    def test_class_relabel_undo(self):
        history = BoxHistory()
        start, changed = [box(1)], [box(3)]
        history.record(start, 0, changed, 0)
        prior, selected = history.undo(changed, 0)
        self.assertEqual(prior[0].class_id, 1)
        self.assertEqual(selected, 0)

    def test_move_undo_redo(self):
        history = BoxHistory()
        start = [box(dx=3)]
        moved = [box(dx=30)]
        self.assertTrue(history.record(start, 0, moved, 0))
        original, index = history.undo(moved, 0)
        self.assertEqual(original[0].x1, 3)
        again, index = history.redo(original, index)
        self.assertEqual(again[0].x1, 30)

    def test_noop_does_not_pollute_history(self):
        history = BoxHistory()
        self.assertFalse(history.record([box()], 0, [box()], 0))
        self.assertFalse(history.can_undo)

    def test_new_edit_invalidates_redo(self):
        history = BoxHistory()
        history.record([], None, [box()], 0)
        original, selected = history.undo([box()], 0)
        self.assertTrue(history.can_redo)
        history.record(original, selected, [box(2)], 0)
        self.assertFalse(history.can_redo)

    def test_capacity_is_bounded(self):
        history = BoxHistory(capacity=3)
        for i in range(9):
            history.record([box(dx=i)], 0, [box(dx=i+1)], 0)
        current = [box(dx=9)]
        count = 0
        while history.can_undo:
            current, selected = history.undo(current, 0)
            count += 1
        self.assertEqual(count, 3)
        self.assertEqual(current[0].x1, 6)

    def test_per_image_clear(self):
        history = BoxHistory()
        history.record([], None, [box()], 0)
        history.clear()
        self.assertFalse(history.can_undo)
        self.assertFalse(history.can_redo)

    def test_snapshot_detaches_mutable_box_references(self):
        original = [box()]
        snap = make_snapshot(original, 0)
        original[0].x1 = 99
        self.assertEqual(snap.boxes[0][1], 0)

    def test_restore_detaches_mutable_box_references(self):
        history = BoxHistory()
        before = [box()]
        history.record(before, 0, [box(2)], 0)
        first, _ = history.undo([box(2)], 0)
        first[0].x1 = 100
        redo, _ = history.redo(first, 0)
        self.assertEqual(redo[0].class_id, 2)

    def test_invalid_selection_is_cleared(self):
        self.assertIsNone(make_snapshot([box()], 22).selected)

    def test_clone_boxes_is_deep(self):
        before = [box()]
        after = clone_boxes(before)
        after[0].x1 = 90
        self.assertEqual(before[0].x1, 0)


class OptionalRealQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('PySide6 not installed')
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        from custom_trainer.ui.widgets.annotation_canvas import AnnotationCanvas
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / 'test.png'
        pixmap = QPixmap(240, 180)
        pixmap.fill(Qt.darkGray)
        self.assertTrue(pixmap.save(str(self.image)))
        self.canvas = AnnotationCanvas(lambda: 0)
        self.canvas.resize(480, 360)
        self.canvas.set_scene(self.image, [box(0)])
        self.canvas.show()
        self.app.processEvents()
        self.addCleanup(self.canvas.close)

    def test_undo_class_and_movement(self):
        self.canvas.selected_index = 0
        self.assertTrue(self.canvas.set_selected_class_id(3))
        self.assertTrue(self.canvas.nudge_selected(10, 0))
        self.assertEqual(self.canvas.boxes[0].x1, 10)
        self.assertTrue(self.canvas.undo_edit())
        self.assertEqual(self.canvas.boxes[0].x1, 0)
        self.assertTrue(self.canvas.undo_edit())
        self.assertEqual(self.canvas.boxes[0].class_id, 0)
        self.assertTrue(self.canvas.redo_edit())
        self.assertEqual(self.canvas.boxes[0].class_id, 3)

    def test_quick_deploy_replacement_is_reversible(self):
        self.assertTrue(self.canvas.replace_boxes([box(2, 20)]))
        self.assertEqual(self.canvas.boxes[0].class_id, 2)
        self.assertTrue(self.canvas.undo_edit())
        self.assertEqual(self.canvas.boxes[0].class_id, 0)

    def test_scene_switch_clears_history_and_zoom(self):
        self.canvas.replace_boxes([box(2)])
        self.canvas.set_zoom(3)
        self.canvas.set_scene(self.image, [box(1)])
        self.assertFalse(self.canvas.history.can_undo)
        self.assertEqual(self.canvas.zoom_factor, 1)

    def test_zoom_pan_bounds_and_preview_minimum(self):
        self.assertEqual(self.canvas.minimumSize().width(), 360)
        self.canvas.set_zoom(12)
        self.assertEqual(self.canvas.zoom_factor, 8)
        self.canvas.pan_offset.setX(100000)
        self.canvas._clamp_pan()
        self.assertLess(self.canvas.pan_offset.x(), 2000)
        self.canvas.reset_zoom()
        self.assertEqual(self.canvas.pan_offset.x(), 0)

    def test_marking_shortcut_does_not_swallow_text_input(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from custom_trainer.state import AppState
        from custom_trainer.ui.pages.marking_page import MarkingPage

        page = MarkingPage(AppState(), lambda message: None, lambda message: None)
        page.show()
        self.app.processEvents()
        page.root_edit.setFocus()
        self.app.processEvents()
        self.assertTrue(page._shortcut_target_is_text_input())
        self.assertFalse(any(item.isEnabled() for item in page._shortcuts))
        page.root_edit.clear()
        QTest.keyClicks(page.root_edit, 'adsw123')
        self.assertEqual(page.root_edit.text(), 'adsw123')
        page.class_editor.setFocus()
        self.app.processEvents()
        QTest.keyClicks(page.class_editor, 'ws')
        self.assertTrue(page.class_editor.toPlainText().endswith('ws'))
        page.close()


if __name__ == '__main__':
    unittest.main()
