"""Protect piTrainer JSONL source recordings from interrupted metadata saves."""
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from piTrainer.services.data import delete_service, edit_service
from piTrainer.services.data.jsonl_atomic_service import file_signature, replace_jsonl_lines


class AtomicJsonlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'labels.jsonl'
        self.original = '{"steering":0.1}\nnot-json\n{"steering":0.4}\n'
        self.path.write_text(self.original, encoding='utf-8')

    def test_atomic_replacement_succeeds_and_cleans_staged_file(self):
        signature = file_signature(self.path)
        replace_jsonl_lines(self.path, ['{"steering":0.5}\n', 'not-json\n'], expected_signature=signature)
        self.assertEqual(self.path.read_text(), '{"steering":0.5}\nnot-json\n')
        self.assertEqual(list(self.root.glob('.labels.jsonl.*.tmp')), [])

    def test_line_generation_error_does_not_truncate_original(self):
        def broken_lines():
            yield '{"steering":0.9}\n'
            raise OSError('simulated disk write failure')
        with self.assertRaisesRegex(OSError, 'simulated'):
            replace_jsonl_lines(self.path, broken_lines(), expected_signature=file_signature(self.path))
        self.assertEqual(self.path.read_text(), self.original)
        self.assertEqual(list(self.root.glob('.labels.jsonl.*.tmp')), [])

    def test_failed_atomic_rename_preserves_source(self):
        with patch('piTrainer.services.data.jsonl_atomic_service.os.replace', side_effect=OSError('rename failed')):
            with self.assertRaisesRegex(OSError, 'rename failed'):
                replace_jsonl_lines(self.path, ['replacement\n'], expected_signature=file_signature(self.path))
        self.assertEqual(self.path.read_text(), self.original)
        self.assertEqual(list(self.root.glob('.labels.jsonl.*.tmp')), [])

    def test_one_time_recovery_copy_preserves_pre_edit_bytes(self):
        backup = self.root / 'labels.jsonl.pitrainer-original.bak'
        original_bytes = self.path.read_bytes()
        replace_jsonl_lines(self.path, ['first edit\n'], expected_signature=file_signature(self.path))
        self.assertEqual(backup.read_bytes(), original_bytes)
        replace_jsonl_lines(self.path, ['second edit\n'], expected_signature=file_signature(self.path))
        self.assertEqual(backup.read_bytes(), original_bytes)
        self.assertEqual(self.path.read_text(), 'second edit\n')

    def test_backup_failure_refuses_to_commit_any_change(self):
        with patch('piTrainer.services.data.jsonl_atomic_service.os.link', side_effect=OSError('backup disk full')):
            with self.assertRaisesRegex(OSError, 'backup disk full'):
                replace_jsonl_lines(self.path, ['replacement\n'], expected_signature=file_signature(self.path))
        self.assertEqual(self.path.read_text(), self.original)
        self.assertFalse((self.root / 'labels.jsonl.pitrainer-original.bak').exists())
        self.assertEqual(list(self.root.glob('.*.tmp')), [])

    def test_failed_fsync_preserves_source(self):
        with patch('piTrainer.services.data.jsonl_atomic_service.os.fsync', side_effect=OSError('fsync failed')):
            with self.assertRaisesRegex(OSError, 'fsync failed'):
                replace_jsonl_lines(self.path, ['replacement\n'], expected_signature=file_signature(self.path))
        self.assertEqual(self.path.read_text(), self.original)

    def test_external_modification_blocks_stale_write(self):
        signature = file_signature(self.path)
        with self.path.open('a', encoding='utf-8') as fh:
            fh.write('{"new":true}\n')
        with self.assertRaisesRegex(RuntimeError, 'Metadata changed on disk'):
            replace_jsonl_lines(self.path, ['replacement\n'], expected_signature=signature)
        self.assertTrue(self.path.read_text().endswith('{"new":true}\n'))

    def test_external_replacement_same_size_and_mtime_blocks_stale_write(self):
        signature = file_signature(self.path)
        previous = self.path.stat()
        replacement = self.root / 'external.tmp'
        replacement.write_text(self.original.replace('0.1', '0.3'), encoding='utf-8')
        self.assertEqual(replacement.stat().st_size, previous.st_size)
        os.utime(replacement, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        os.replace(replacement, self.path)
        with self.assertRaisesRegex(RuntimeError, 'Metadata changed on disk'):
            replace_jsonl_lines(self.path, ['replacement\n'], expected_signature=signature)
        self.assertIn('0.3', self.path.read_text())

    def test_source_file_permissions_preserved(self):
        if os.name != 'posix':
            self.skipTest('POSIX permission mode assertions')
        self.path.chmod(0o640)
        replace_jsonl_lines(self.path, ['done\n'], expected_signature=file_signature(self.path))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)

    def test_conflict_after_staging_preserves_external_change(self):
        signature = file_signature(self.path)
        def lines():
            yield 'replacement\n'
            with self.path.open('a', encoding='utf-8') as out:
                out.write('external update\n')
        with self.assertRaisesRegex(RuntimeError, 'changed on disk'):
            replace_jsonl_lines(self.path, lines(), expected_signature=signature)
        self.assertTrue(self.path.read_text().endswith('external update\n'))
        self.assertEqual(list(self.root.glob('.labels.jsonl.*.tmp')), [])


class MetadataWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.session = self.root / 'session_one'
        self.session.mkdir()
        (self.session / 'frames').mkdir()
        self.rows = [
            {'frame_id': 'frame001', 'frame': 'frames/001.jpg', 'timestamp_utc': '2026-11-22T10:00:00Z', 'steering': 0.1, 'throttle': 0.2},
            {'frame_id': 'frame002', 'frame': 'frames/002.jpg', 'timestamp_utc': '2026-11-22T10:00:01Z', 'steering': 0.3, 'throttle': 0.4},
        ]
        self.labels = self.session / 'labels.jsonl'
        self.records = self.session / 'records.jsonl'
        for path in (self.labels, self.records):
            path.write_text('\n'.join(json.dumps(r) for r in self.rows) + '\ninvalid-json-still-here\n', encoding='utf-8')
        for name in ('001.jpg', '002.jpg'):
            (self.session / 'frames' / name).write_bytes(b'frame')
        # The cache is process-wide, so isolate each test's per-file entries.
        edit_service._JSONL_CACHE.clear()
        edit_service._JSONL_CACHE_ORDER.clear()

    def record(self, i=0, steering=0.5, throttle=0.6):
        r = self.rows[i]
        return {'session': 'session_one', 'frame_id': r['frame_id'], 'ts': r['timestamp_utc'],
                'abs_image': str(self.session / r['frame']), 'steering': steering, 'throttle': throttle}

    def load_rows(self, path):
        lines = path.read_text(encoding='utf-8').splitlines()
        self.assertIn('invalid-json-still-here', lines)
        return [json.loads(line) for line in lines if line.startswith('{')]

    def test_single_frame_edit_uses_atomic_save_in_both_metadata_files(self):
        valid, message = edit_service.update_frame_controls(
            self.root, 'session_one', 'frame001', str(self.session/'frames/001.jpg'),
            '2026-11-22T10:00:00Z', 0.8, .7)
        self.assertTrue(valid, message)
        for path in (self.labels, self.records):
            rows = self.load_rows(path)
            self.assertEqual([row['steering'] for row in rows], [.8, .3])
            self.assertEqual([row['throttle'] for row in rows], [.7, .4])
        self.assertEqual(list(self.session.glob('.*.tmp')), [])

    def test_individual_preview_updates_preserve_each_frame_values(self):
        result = edit_service.update_frame_controls_many(self.root, [
            self.record(0, .8, .7), self.record(1, -.5, .1),
        ])
        self.assertEqual(result['updated_count'], 2)
        self.assertEqual(result['metadata_rows_changed'], 4)
        self.assertEqual([r['steering'] for r in self.load_rows(self.labels)], [.8, -.5])

    def test_bulk_edit_preserves_unedited_field_and_malformed_line(self):
        result = edit_service.update_frame_controls_batch(
            self.root, [self.record(0), self.record(1)], steering=-.4,
            throttle=.9, update_steering=True, update_throttle=False)
        self.assertEqual(result['updated_count'], 2)
        self.assertEqual([r['steering'] for r in self.load_rows(self.labels)], [-.4, -.4])
        self.assertEqual([r['throttle'] for r in self.load_rows(self.labels)], [.2, .4])

    def test_failed_preview_save_leaves_disk_and_cache_unmodified(self):
        old = self.labels.read_bytes()
        old_records = self.records.read_bytes()
        with patch('piTrainer.services.data.edit_service.replace_jsonl_lines', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                edit_service.update_frame_controls_many(self.root, [self.record(0, .9, .8)])
        self.assertEqual(self.labels.read_bytes(), old)
        self.assertEqual(self.records.read_bytes(), old_records)
        # No speculative cache edits may be returned to subsequent readers.
        self.assertEqual(edit_service._load_jsonl_entries(self.labels)[0]['record']['steering'], .1)
        result = edit_service.update_frame_controls_many(self.root, [self.record(1, .6, .7)])
        self.assertEqual(result['updated_count'], 1)
        self.assertEqual([r['steering'] for r in self.load_rows(self.labels)], [.1, .6])

    def test_hidden_frames_can_be_recovered_with_atomic_replacement(self):
        hide = delete_service.hide_frames_from_training(self.root, [self.record(0)])
        self.assertEqual(hide['hidden_count'], 1)
        self.assertTrue(self.load_rows(self.labels)[0]['hidden_from_training'])
        recovered = delete_service.recover_hidden_frames(self.root, ['session_one'], recover_all=True)
        self.assertEqual(recovered['recovered_count'], 1)
        self.assertFalse(delete_service.is_record_hidden(self.load_rows(self.labels)[0]))
        self.assertEqual(list(self.session.glob('.*.tmp')), [])

    def test_permanent_hidden_delete_removes_only_hidden_metadata_and_images(self):
        delete_service.hide_frames_from_training(self.root, [self.record(0)])
        purged = delete_service.purge_hidden_frames(self.root, ['session_one'])
        self.assertEqual(purged['purged_count'], 1)
        self.assertFalse((self.session / 'frames/001.jpg').exists())
        self.assertTrue((self.session / 'frames/002.jpg').exists())
        for path in (self.labels, self.records):
            rows = self.load_rows(path)
            self.assertEqual([r['frame_id'] for r in rows], ['frame002'])

    def test_failed_hide_save_leaves_source_untouched(self):
        old = self.labels.read_bytes()
        with patch('piTrainer.services.data.delete_service.replace_jsonl_lines', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                delete_service.hide_frames_from_training(self.root, [self.record(0)])
        self.assertEqual(self.labels.read_bytes(), old)

    def test_failed_purge_metadata_save_does_not_delete_image(self):
        delete_service.hide_frames_from_training(self.root, [self.record(0)])
        old = self.labels.read_bytes()
        with patch('piTrainer.services.data.delete_service.replace_jsonl_lines', side_effect=OSError('rename failed')):
            with self.assertRaisesRegex(OSError, 'rename failed'):
                delete_service.purge_hidden_frames(self.root, ['session_one'])
        self.assertEqual(self.labels.read_bytes(), old)
        self.assertTrue((self.session / 'frames/001.jpg').exists())


if __name__ == '__main__':
    unittest.main()
