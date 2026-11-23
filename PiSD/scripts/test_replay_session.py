"""U29: read-only and deterministic replay tests; no Flask or motor dependencies."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_session import (digest, main, read_jsonl, replay, safe_frame,
                            write_report)

FIXTURE = Path(__file__).resolve().parent / 'fixtures/steering_replay.jsonl'


class SteeringReplayTests(unittest.TestCase):
    def test_determinism_mae_and_hardware_isolation(self):
        before = digest(FIXTURE)
        first = replay(FIXTURE)
        second = replay(FIXTURE)
        self.assertEqual(first, second)
        self.assertEqual(first['total_frames'], 3)
        self.assertEqual(first['steering_mae'], 0.1)
        self.assertFalse(first['hardware_initialized'])
        self.assertEqual(first['mode'], 'synthetic_predictions')
        self.assertEqual(first['failed_frames'], 0)
        self.assertTrue(all('predicted_steering' in x for x in first['frames']))
        self.assertEqual(first['input']['source_sha256'], before)
        self.assertEqual(digest(FIXTURE), before)
        self.assertFalse('RPi.GPIO' in sys.modules)

    def test_failed_prediction_is_not_counted_in_mae(self):
        rows = read_jsonl(FIXTURE)
        rows[1]['predicted_steering'] = 'nan'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.jsonl'
            path.write_text(''.join(json.dumps(x) + '\n' for x in rows))
            result = replay(path)
        self.assertEqual(result['failed_frames'], 1)
        self.assertEqual(result['successful_predictions'], 2)
        self.assertEqual(result['steering_mae'], 0.1)
        self.assertEqual(result['failure_events'][0]['index'], 1)

    def test_source_session_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {'frame': '../outside.jpg', 'steering': 0.0}
            path = root / 'labels.jsonl'
            path.write_text(json.dumps(record)+'\n')
            result = replay(path, session_dir=root, predictor=lambda *_: (0.0, None))
            self.assertEqual(result['failed_frames'], 1)
            self.assertIn('escapes', result['failure_events'][0]['detail'])

    def test_exclusive_report_and_source_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / 'report.json'
            report = replay(FIXTURE)
            write_report(report, report_path, FIXTURE, None)
            saved = json.loads(report_path.read_text())
            self.assertEqual(saved, report)
            with self.assertRaises(FileExistsError):
                write_report(report, report_path, FIXTURE, None)
            with self.assertRaises(ValueError):
                write_report(report, FIXTURE, FIXTURE, None)

    def test_missing_synthetic_predictions_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'labels.jsonl'
            row = read_jsonl(FIXTURE)[0]
            del row['predicted_steering']
            path.write_text(json.dumps(row)+'\n')
            result = replay(path)
            self.assertEqual(result['successful_predictions'], 0)
            self.assertIsNone(result['steering_mae'])
            self.assertEqual(result['failure_events'][0]['event'], 'prediction_failure')

    def test_cli_fails_threshold_and_reports_success_without_motor(self):
        import contextlib
        from io import StringIO
        with contextlib.redirect_stdout(StringIO()):
            self.assertEqual(main(['--fixture', str(FIXTURE), '--max-steering-mae', '0.09']), 2)
            self.assertEqual(main(['--fixture', str(FIXTURE), '--max-steering-mae', '0.11']), 0)


if __name__ == '__main__':
    unittest.main()
