"""Free-space and write-failure regression checks, without physical hardware."""
from __future__ import annotations
import errno
import json
import tempfile
import unittest
from pathlib import Path
from collections import namedtuple
from unittest.mock import patch

from pisd.core.recording_storage import RecordingStorageGuard, RecordingStorageError


class StorageGuardTests(unittest.TestCase):
    def test_ok_warn_critical_and_missing_disk(self):
        with tempfile.TemporaryDirectory() as t:
            guard = RecordingStorageGuard(Path(t) / 'absent', prefix='TESTU26')
            usage = namedtuple('usage', 'total used free')
            with patch('pisd.core.recording_storage.shutil.disk_usage', return_value=usage(1024**3, 500*1024**2, 400*1024**2)):
                self.assertEqual(guard.check()['state'], 'warning')
                guard.require_space()
            with patch('pisd.core.recording_storage.shutil.disk_usage', return_value=usage(1024**3, 800*1024**2, 200*1024**2)):
                self.assertEqual(guard.check()['state'], 'critical')
                with self.assertRaises(RecordingStorageError):
                    guard.require_space()
            with patch('pisd.core.recording_storage.shutil.disk_usage', side_effect=OSError(errno.EIO, 'statvfs failed')):
                self.assertEqual(guard.check()['state'], 'unavailable')
                with self.assertRaises(RecordingStorageError):
                    guard.require_space()

    def test_threshold_environment_clamped_and_reserved_write(self):
        usage = namedtuple('usage', 'total used free')
        with tempfile.TemporaryDirectory() as t, patch.dict('os.environ', {'TESTU26_RECORDING_MIN_FREE_MB':'50','TESTU26_RECORDING_WARN_FREE_MB':'60'}):
            guard = RecordingStorageGuard(t, prefix='TESTU26')
            with patch('pisd.core.recording_storage.shutil.disk_usage', return_value=usage(500*1024**2, 440*1024**2, 60*1024**2)):
                self.assertEqual(guard.check()['state'], 'ok')
                with self.assertRaises(RecordingStorageError):
                    guard.require_space(estimated_bytes=11*1024**2)

    def test_error_history_bounded_and_session_sizes(self):
        with tempfile.TemporaryDirectory() as t:
            guard = RecordingStorageGuard(t, prefix='TESTU26')
            folder = Path(t) / 'session'; folder.mkdir(); (folder/'frames').mkdir()
            (folder/'frames'/'frame.jpg').write_bytes(b'0123456789')
            (folder/'records.jsonl').write_text('{}\n')
            self.assertEqual(guard.session_size(folder), 13)
            for i in range(9): guard.note_error('write', RuntimeError(f'error-{i}'))
            self.assertEqual(len(guard.recent_errors()), 5)
            self.assertIn('error-8', guard.recent_errors()[-1]['message'])
            self.assertEqual(guard.status(folder)['cleanup_policy'], 'manual_confirmation_only')

if __name__ == '__main__': unittest.main()
