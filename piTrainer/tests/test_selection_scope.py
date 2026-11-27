"""R37 hardware-free selection-scope tests; Qt selection test runs when PySide6 is installed."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from piTrainer.services.data.delete_service import count_hidden_frames
from piTrainer.services.data.selection_scope import (
    selected_visible_impact,
    summarize_selection,
)


def active_examples() -> pd.DataFrame:
    return pd.DataFrame([
        {'session': 's1', 'frame_id': 'f1', 'is_synthetic': False},
        {'session': 's1', 'frame_id': 'f2', 'is_synthetic': 'false'},
        {'session': 's1', 'frame_id': 's_f1', 'is_synthetic': True, 'source_frame_id': 'f1'},
        {'session': 's1', 'frame_id': 'f3', 'synthetic_variant': 'flip_lr'},
        {'session': 's2', 'frame_id': 'f4', 'synthetic_variant': 'original'},
    ])


class ScopeTests(unittest.TestCase):
    def test_visible_selected_active_hidden_generated_are_distinct(self):
        data = active_examples()
        preview = data.iloc[[0, 1]].copy()
        scope = summarize_selection(data, preview, [preview.iloc[1].to_dict()], hidden_count=3)
        self.assertEqual((scope.visible, scope.selected_visible, scope.all_active, scope.hidden, scope.generated_active),
                         (2, 1, 5, 3, 2))

    def test_generated_derivatives_not_assumed_in_review(self):
        data = active_examples()
        source = data.iloc[[0, 1, 4]].copy()
        scope = summarize_selection(data, source, [source.iloc[0].to_dict()], hidden_count=0)
        self.assertEqual(scope.selected_generated, 0)
        self.assertEqual(scope.generated_active, 2)

    def test_truthy_synthetic_aliases_and_false_string(self):
        data = pd.DataFrame([
            {'frame_id': 'f1', 'is_synthetic': 'false'},
            {'frame_id': 'f2', 'pitrainer_synthetic': 'yes'},
            {'frame_id': 's_f3'},
            {'frame_id': 'f4', 'aug_variant': 'hflip'},
            {'frame_id': 'f5', 'aug_variant': 'original'},
        ])
        scope = summarize_selection(data, data, [data.iloc[1].to_dict()], hidden_count=0)
        self.assertEqual(scope.generated_active, 3)
        self.assertEqual(scope.selected_generated, 1)

    def test_hidden_unknown_not_misrepresented_as_zero(self):
        scope = summarize_selection(active_examples(), pd.DataFrame(), [], hidden_count=None)
        self.assertIsNone(scope.hidden)
        self.assertIn('Hidden: Unavailable', scope.toolbar_text())

    def test_zero_hidden_is_explicit(self):
        scope = summarize_selection(active_examples(), active_examples(), [], hidden_count=0)
        self.assertIn('Hidden: 0', scope.toolbar_text())

    def test_empty_frames(self):
        empty = pd.DataFrame()
        scope = summarize_selection(empty, empty, [], hidden_count=0)
        self.assertEqual((scope.visible, scope.selected_visible, scope.all_active, scope.generated_active),
                         (0, 0, 0, 0))

    def test_all_active_includes_filtered_out_frames(self):
        data = active_examples()
        scope = summarize_selection(data, data.iloc[0:1], [], hidden_count=1)
        self.assertEqual(scope.all_active, 5)
        self.assertEqual(scope.visible, 1)

    def test_input_frames_not_mutated(self):
        data = active_examples()
        original = data.copy(deep=True)
        records = [data.iloc[0].to_dict()]
        _ = summarize_selection(data, data, records, hidden_count=2)
        pd.testing.assert_frame_equal(data, original)
        self.assertEqual(len(records), 1)

    def test_selection_order_does_not_change_identity_scope(self):
        data = active_examples()
        selected = [data.iloc[0].to_dict(), data.iloc[4].to_dict()]
        first = summarize_selection(data, data, selected, hidden_count=0)
        second = summarize_selection(data, data.iloc[::-1], list(reversed(selected)), hidden_count=0)
        self.assertEqual(first, second)

    def test_selection_impact_reports_exact_selected_visible_count(self):
        rows = [active_examples().iloc[i].to_dict() for i in (0, 1, 4)]
        impact = selected_visible_impact(rows)
        self.assertIn('3 selected visible frame(s)', impact)
        self.assertIn('Generated derivatives included: 0 of 3', impact)

    def test_selected_generated_variants_disclosed(self):
        rows = [active_examples().iloc[i].to_dict() for i in (0, 2, 3)]
        impact = selected_visible_impact(rows)
        self.assertIn('3 selected visible frame(s)', impact)
        self.assertIn('Generated derivatives included: 2 of 3', impact)

    def test_empty_selection_not_all_active(self):
        impact = selected_visible_impact([])
        self.assertIn('0 selected visible frame(s)', impact)
        self.assertIn('not targeted', impact)

    def test_summary_definitions_explicit(self):
        scope = summarize_selection(active_examples(), active_examples(), [], hidden_count=2)
        self.assertIn('filtered, editable source frames', scope.detail_text())
        self.assertIn('including generated rows', scope.detail_text())

    def test_hidden_negative_inputs_are_clamped(self):
        scope = summarize_selection(active_examples(), active_examples(), [], hidden_count=-8)
        self.assertEqual(scope.hidden, 0)


class HiddenMetadataScopeTests(unittest.TestCase):
    def _make_session(self, root: Path, name: str, labels: list[dict], records: list[dict]) -> None:
        session = root / name
        session.mkdir(parents=True)
        for filename, entries in (('labels.jsonl', labels), ('records.jsonl', records)):
            with (session / filename).open('w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(json.dumps(entry) + '\n')

    @staticmethod
    def row(frame_id: str, *, hidden: bool = False) -> dict:
        return {'frame_id': frame_id, 'ts': f'{frame_id}-time',
                'image': f'{frame_id}.jpg', 'hidden_from_training': hidden}

    def test_dual_jsonl_hidden_frame_is_counted_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hidden = self.row('a', hidden=True)
            self._make_session(root, 's1', [hidden], [hidden, self.row('b')])
            self.assertEqual(count_hidden_frames(root, ['s1']), 1)

    def test_hidden_count_is_scoped_to_loaded_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_session(root, 's1', [self.row('a', hidden=True)], [])
            self._make_session(root, 's2', [self.row('b', hidden=True)], [])
            self.assertEqual(count_hidden_frames(root, ['s1']), 1)
            self.assertEqual(count_hidden_frames(root, ['s1', 's2']), 2)

    def test_nonhidden_and_missing_jsonl_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_session(root, 's1', [self.row('a')], [])
            (root / 's1' / 'records.jsonl').unlink()
            self.assertEqual(count_hidden_frames(root, ['s1']), 0)

    def test_no_selected_sessions_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(count_hidden_frames(Path(tmp), []), 0)


try:
    from PySide6.QtCore import Qt, QItemSelectionModel, QPersistentModelIndex
    from PySide6.QtWidgets import QApplication
    from piTrainer.panels.data.preview_panel import PreviewPanel
except ImportError:
    PreviewPanel = None


@unittest.skipUnless(PreviewPanel is not None, 'PySide6 desktop GUI unavailable')
class PreviewSortIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_source_row_multiselection_survives_sort_and_toolbar_updates(self):
        rows = pd.DataFrame([
            {'session':'2026-01-01', 'frame_id':'f02', 'ts':'t2', 'abs_image':'/a/2.jpg',
             'steering': 0.3, 'throttle': 0.4, 'mode':'manual'},
            {'session':'2026-01-01', 'frame_id':'f01', 'ts':'t1', 'abs_image':'/a/1.jpg',
             'steering': -0.3, 'throttle': 0.4, 'mode':'manual'},
            {'session':'2026-01-02', 'frame_id':'f01', 'ts':'t3', 'abs_image':'/b/1.jpg',
             'steering': 0.1, 'throttle': 0.5, 'mode':'manual'},
        ])
        preview = PreviewPanel(selection_callback=lambda _record: None)
        preview.set_dataframe(rows)
        preview.set_scope_totals(all_active=5, generated_active=2, hidden=1)
        selection = preview.table.selectionModel()
        selection.clearSelection()
        flags = preview._selection_flags('Select', 'Rows')
        for source_row in (0, 2):
            selection.select(preview.model.index(preview.model.view_row_for_source_row(source_row), 0), flags)
        self.app.processEvents()
        before = {(r['session'], r['frame_id'], r['abs_image']) for r in preview.selected_records()}
        self.assertEqual(before, {('2026-01-01', 'f02', '/a/2.jpg'),
                                  ('2026-01-02', 'f01', '/b/1.jpg')})
        current = preview.model.index(preview.model.view_row_for_source_row(2), 0)
        selection.setCurrentIndex(current, QItemSelectionModel.NoUpdate)
        persistent = QPersistentModelIndex(current)
        for order in (Qt.DescendingOrder, Qt.AscendingOrder, Qt.DescendingOrder):
            preview.table.sortByColumn(0, order)
            self.app.processEvents()
            after = {(r['session'], r['frame_id'], r['abs_image']) for r in preview.selected_records()}
            self.assertEqual(before, after)
            self.assertEqual(preview.current_row(), 2)
            self.assertEqual(preview.model.source_row(persistent.row()), 2)
        self.assertIn('Selected visible: 2', preview.scope_label.text())
        self.assertIn('All active: 5', preview.scope_label.text())
        # Validation's Edit in Data path targets a source-frame identity,
        # not whatever row a sorting operation moved into the old position.
        target_identity = preview.record_identity(rows.iloc[1].to_dict())
        self.assertTrue(preview.select_record_identity(target_identity))
        self.assertEqual(preview.record_identity(preview.selected_record()), target_identity)
        # Sorting an empty selection must not fabricate selected source rows.
        selection.clearSelection()
        preview.table.sortByColumn(0, Qt.AscendingOrder)
        self.app.processEvents()
        self.assertEqual(preview.selected_records(), [])
        self.assertEqual(preview.record_identity(preview.selected_record()), target_identity)
        preview.deleteLater()


@unittest.skipUnless(PreviewPanel is not None, 'PySide6 desktop GUI unavailable')
class PerformanceSourceLookupTests(unittest.TestCase):
    def test_reverse_mapping_after_default_sort_header_sort_edit_and_reset(self):
        from piTrainer.panels.data.preview_model import RecordPreviewModel
        app = QApplication.instance() or QApplication([])
        model = RecordPreviewModel()
        rows = [{"frame_id": f"f{i}", "session": "session", "steering": float(i)} for i in (10, 2, 1, 5)]
        columns = ["frame_id", "session", "steering"]
        model.set_preview_rows(rows, columns)
        def check():
            for source in range(model.rowCount()):
                view = model.view_row_for_source_row(source)
                self.assertEqual(model.source_row(view), source)
            self.assertEqual(model.view_row_for_source_row(-1), -1)
            self.assertEqual(model.view_row_for_source_row(model.rowCount()), -1)
        check()
        for column in (0, 2, 1):
            for order in (Qt.DescendingOrder, Qt.AscendingOrder):
                model.sort(column, order)
                check()
        model.set_value(2, "steering", -0.5)
        self.assertEqual(model.rows[model.view_row_for_source_row(2)]["steering"], -0.5)
        model.set_preview_rows([], columns)
        check()
        model.set_preview_rows(rows[:2], columns)
        check()


if __name__ == '__main__':
    unittest.main()
