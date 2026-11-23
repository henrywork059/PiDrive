#!/usr/bin/env python3
"""Hardware-free interrupted-recording recovery tests (U20)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pisd.services.recording_recovery import inspect_session, recover_session
from pisd.services.recording_service import RecordingService
from pisd.core.errors import PiSDErrorCodes

TRAINER_PROJECT = ROOT.parent / 'piTrainer'
if TRAINER_PROJECT.is_dir() and str(TRAINER_PROJECT) not in sys.path:
    sys.path.insert(0, str(TRAINER_PROJECT))


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'recordings'
        self.session = self.root / '2026-11-22' / 'session-test'
        (self.session / 'frames').mkdir(parents=True)
        self.manifest = self.session / 'manifest.json'
        self.records = self.session / 'records.jsonl'
        self.labels = self.session / 'labels.jsonl'
        self.manifest.write_text(json.dumps({'session_id': 'session-test', 'label': 'manual_drive',
                                             'frame_count': 0, 'running': False, 'schema': {'custom': 'keep'}}))
        self.records.write_text('')
        self.labels.write_text('')

    def add(self, index: int, *, record: bool = True, label: bool = True, frame: bool = True,
            steering: float = 0.25, throttle: float = 0.45):
        name = f'frame_{index:06d}_20261122T120000Z_deadbeef.jpg'
        relative = 'frames/' + name
        p = self.session / relative
        if frame:
            p.write_bytes(b'\xff\xd8\xff\xd9')
        label_row = {
            'frame': relative, 'relative_file': f'PiSD/recordings/2026-11-22/session-test/{relative}',
            'steering': steering, 'throttle': throttle, 'session_id': 'session-test',
            'timestamp_utc': '2026-11-22T12:00:00+00:00',
            'source_frame_seq': index, 'overlay_settings': {'opacity': 0.3},
            'overlay_settings_file': 'overlay_settings.json',
        }
        record_row = {
            'frame_id': 'original_' + str(index), 'frame_index': index, 'session_id': 'session-test',
            'file': str(p), 'relative_file': label_row['relative_file'],
            'steering': steering, 'throttle': throttle, 'source_frame_seq': index,
            'saved_at_utc': label_row['timestamp_utc'], 'camera_settings': {'fps': 30},
            'motor_state': {'motor': 'status'}, 'training_label': label_row,
        }
        if record:
            with self.records.open('a') as f:
                f.write(json.dumps(record_row) + '\n')
        if label:
            with self.labels.open('a') as f:
                f.write(json.dumps(label_row) + '\n')
        return p, record_row, label_row

    def test_healthy_recordings_are_inspected_without_modification(self):
        self.add(1)
        self.manifest.write_text(json.dumps({'session_id': 'session-test', 'frame_count': 1, 'schema': {'custom': 'keep'}}))
        before = {x: x.read_bytes() for x in (self.manifest, self.records, self.labels)}
        report = inspect_session(self.session)
        self.assertFalse(report['needs_attention'], report)
        self.assertEqual(report['complete_pairs'], 1)
        result = recover_session(self.session, confirm_offline=True)
        self.assertFalse(result['repaired'])
        self.assertEqual({x: x.read_bytes() for x in before}, before)
        self.assertFalse((self.session / '.recovery_backups').exists())

    def test_record_only_restores_trainer_label_and_keeps_source(self):
        _, record, label = self.add(1, label=False)
        old = self.records.read_bytes()
        report = inspect_session(self.session)
        self.assertEqual(len(report['missing_labels']), 1)
        result = recover_session(self.session, confirm_offline=True)
        self.assertTrue(result['repaired'], result)
        self.assertEqual(result['added_labels'], 1)
        self.assertEqual(self.records.read_bytes(), old)
        labels = [json.loads(x) for x in self.labels.read_text().splitlines()]
        self.assertEqual(labels[0]['steering'], record['steering'])
        self.assertEqual(labels[0]['frame'], label['frame'])
        self.assertEqual(json.loads(self.manifest.read_text())['frame_count'], 1)
        self.assertEqual(json.loads(self.manifest.read_text())['schema'], {'custom': 'keep'})
        self.assertEqual((Path(result['backup_dir']) / 'records.jsonl').read_bytes(), old)
        self.assertFalse(inspect_session(self.session)['needs_attention'])

    def test_label_only_restores_minimal_trace_with_explicit_missing_provenance(self):
        _, _, label = self.add(1, record=False)
        old = self.labels.read_bytes()
        result = recover_session(self.session, confirm_offline=True)
        self.assertEqual(result['added_records'], 1)
        record = json.loads(self.records.read_text())
        self.assertEqual(record['training_label']['frame'], label['frame'])
        self.assertTrue(record['frame_id'].startswith('recovered_'))
        self.assertTrue(record['recovery']['limited_metadata'])
        self.assertNotIn('camera_settings', record)
        self.assertEqual(self.labels.read_bytes(), old)
        self.assertFalse(inspect_session(self.session)['needs_attention'])

    def test_orphan_jpeg_never_generates_fake_steering(self):
        frame, _, _ = self.add(1, record=False, label=False)
        result = recover_session(self.session, confirm_offline=True)
        self.assertFalse(result['repaired'])
        self.assertEqual(result['orphan_jpegs'], ['frames/' + frame.name])
        self.assertTrue(frame.exists())
        self.assertFalse(self.records.read_bytes())
        self.assertFalse(self.labels.read_bytes())

    def test_malformed_tail_preserved_and_next_record_recovers(self):
        self.add(1, label=False)
        with self.records.open('ab') as f:
            f.write(b'{"incomplete":')  # Interrupted JSON write lacking newline
        original = self.records.read_bytes()
        result = recover_session(self.session, confirm_offline=True)
        self.assertEqual(result['added_labels'], 1)
        self.assertTrue(result['needs_attention'])
        self.assertIn(b'{"incomplete":', self.records.read_bytes())
        self.assertEqual((Path(result['backup_dir']) / 'records.jsonl').read_bytes(), original)
        self.assertIn('incomplete or invalid JSON', ' '.join(result['issues']))
        self.assertEqual(len(self.labels.read_text().splitlines()), 1)

    def test_multiple_interruptions_recover_both_sides_without_duplication(self):
        self.add(1, label=False)
        self.add(2, record=False)
        self.add(3)
        self.manifest.write_text(json.dumps({'session_id': 'session-test', 'frame_count': 0}))
        report = recover_session(self.session, confirm_offline=True)
        self.assertEqual((report['added_records'], report['added_labels']), (1, 1))
        self.assertEqual(report['complete_pairs'], 3)
        self.assertEqual(len(self.records.read_text().splitlines()), 3)
        self.assertEqual(len(self.labels.read_text().splitlines()), 3)
        second = recover_session(self.session, confirm_offline=True)
        self.assertFalse(second['repaired'])
        self.assertEqual(len(self.records.read_text().splitlines()), 3)
        self.assertEqual(len(list((self.session / '.recovery_backups').iterdir())), 1)

    def test_manifest_count_reconciled_without_rewriting_labels(self):
        self.add(1)
        old_records, old_labels = self.records.read_bytes(), self.labels.read_bytes()
        self.manifest.write_text(json.dumps({'frame_count': 10, 'running': True, 'custom': 'retain'}))
        result = recover_session(self.session, confirm_offline=True)
        self.assertTrue(result['repaired'])
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data['frame_count'], 1)
        self.assertEqual(data['recording_recovery']['source_frame_count'], 10)
        self.assertFalse(data['running'])  # Explicit offline confirmation closes stale state.
        self.assertTrue(data['recording_recovery']['was_marked_running'])
        self.assertEqual(data['custom'], 'retain')
        self.assertEqual(self.records.read_bytes(), old_records)
        self.assertEqual(self.labels.read_bytes(), old_labels)

    def test_stale_running_flag_only_is_reconciled_without_adding_rows(self):
        self.add(1)
        self.manifest.write_text(json.dumps({'frame_count': 1, 'running': True, 'ended_at_utc': ''}))
        result = recover_session(self.session, confirm_offline=True)
        self.assertTrue(result['repaired'])
        manifest = json.loads(self.manifest.read_text())
        self.assertFalse(manifest['running'])
        self.assertEqual(manifest['ended_at_utc'], '')
        self.assertEqual(result['added_records'], 0)
        self.assertEqual(result['added_labels'], 0)

    def test_single_snapshot_after_orphan_does_not_reuse_frame_index(self):
        orphan = self.session / 'frames' / 'frame_000005_20261122T120000Z_abcd1234.jpg'
        orphan.write_bytes(b'\xff\xd8\xff\xd9')
        service = RecordingService(self.session.parent.parent.parent, root_name='recordings')
        try:
            # The single-capture date folder layout is intentionally distinct.
            day = service.root_dir / 'single_captures'
            from pisd.services import recording_service
            with patch.object(recording_service, '_utc_now') as clock:
                from datetime import datetime, timezone
                now = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
                clock.return_value = now
                folder = day / '2026-11-22' / 'frames'
                folder.mkdir(parents=True, exist_ok=True)
                (folder / orphan.name).write_bytes(orphan.read_bytes())
                _session, index = service._single_capture_session('capture')
            self.assertEqual(index, 6)
        finally:
            service.close()

    def test_piTrainer_loads_recovered_labels_when_available(self):
        try:
            from piTrainer.services.data.record_loader_service import load_records_dataframe
        except ImportError:
            self.skipTest('piTrainer and pandas are not installed alongside PiSD')
        self.add(1, label=False)
        self.add(2, record=False, steering=-0.35)
        recover_session(self.session, confirm_offline=True)
        frame = load_records_dataframe(self.root, ['2026-11-22/session-test'])
        self.assertEqual(len(frame), 2)
        self.assertAlmostEqual(sorted(frame['steering'].tolist())[0], -0.35, places=5)
        self.assertAlmostEqual(sorted(frame['steering'].tolist())[1], 0.25, places=5)
        self.assertTrue(all(Path(p).is_file() for p in frame['abs_image']))

    def test_invalid_control_metadata_refused_without_fabrication(self):
        self.add(1, label=False, steering=9)
        result = recover_session(self.session, confirm_offline=True)
        self.assertFalse(result['repaired'])
        self.assertIn('finite training controls', ' '.join(result['skipped_recovery']))
        self.assertFalse(self.labels.read_text())

    def test_dangling_metadata_and_duplicate_entries_reported_not_pruned(self):
        self.add(1)
        self.add(1)  # Duplicate stable image identity
        self.add(2, frame=False)
        original = self.records.read_bytes()
        report = inspect_session(self.session)
        self.assertTrue(any('duplicate frame' in item for item in report['issues']))
        self.assertTrue(any('JPEG missing' in item for item in report['issues']))
        recover_session(self.session, confirm_offline=True)
        self.assertEqual(self.records.read_bytes(), original)

    def test_malformed_manifest_not_overwritten(self):
        self.add(1, label=False)
        self.manifest.write_bytes(b'{bad manifest')
        before = self.manifest.read_bytes()
        report = recover_session(self.session, confirm_offline=True)
        self.assertFalse(report['repaired'])
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual(self.labels.read_text(), '')

    def test_recovery_requires_explicit_offline_acknowledgement(self):
        self.add(1, label=False)
        with self.assertRaisesRegex(RuntimeError, 'Stop recording first'):
            recover_session(self.session)
        self.assertEqual(self.labels.read_text(), '')

    def test_atomic_replacement_failure_preserves_original_and_backup(self):
        self.add(1, label=False)
        original = self.labels.read_bytes()
        with patch('pisd.services.recording_recovery.os.replace', side_effect=OSError('simulated rename failure')):
            with self.assertRaisesRegex(OSError, 'simulated rename failure'):
                recover_session(self.session, confirm_offline=True)
        self.assertEqual(self.labels.read_bytes(), original)
        backups = list((self.session / '.recovery_backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'labels.jsonl').read_bytes(), original)
        self.assertEqual(list(self.session.glob('*.recovery-tmp')), [])

    def test_cli_read_only_and_explicit_repair(self):
        self.add(1, label=False)
        script = ROOT / 'scripts' / 'recover_recordings.py'
        cli = [sys.executable, str(script), '2026-11-22/session-test', '--root', str(self.root)]
        dry = subprocess.run(cli, capture_output=True, text=True)
        self.assertEqual(dry.returncode, 1, dry.stderr)
        self.assertEqual(self.labels.read_text(), '')
        missing_flag = subprocess.run(cli + ['--repair'], capture_output=True, text=True)
        self.assertEqual(missing_flag.returncode, 2)
        result = subprocess.run(cli + ['--repair', '--confirm-offline'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['repaired'])

    def test_cli_refuses_directory_traversal(self):
        script = ROOT / 'scripts' / 'recover_recordings.py'
        command = [sys.executable, str(script), '../', '--root', str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_stop_does_not_finalize_manifest_while_capture_thread_alive(self):
        class HangingThread:
            def is_alive(self):
                return True
            def join(self, timeout):
                pass
        service = RecordingService(self.session.parent.parent.parent, root_name='recordings')
        service._active_session = {'session_id': 'session-test', 'manifest_file': str(self.manifest),
                                   'session_dir': str(self.session),
                                   'frames_dir': str(self.session / 'frames'),
                                   'records_file': str(self.records),
                                   'labels_file': str(self.labels)}
        service._thread = HangingThread()
        before = self.manifest.read_bytes()
        try:
            stop = service.stop()
            self.assertFalse(stop['ok'], stop)
            self.assertEqual(stop['code'], PiSDErrorCodes.RECORDING_STOP_FAILED)
            self.assertIn('did not exit', stop['message'])
            self.assertEqual(self.manifest.read_bytes(), before)
            self.assertIsNotNone(service._active_session)
        finally:
            service._thread = None
            service._active_session = None


if __name__ == '__main__':
    unittest.main()
