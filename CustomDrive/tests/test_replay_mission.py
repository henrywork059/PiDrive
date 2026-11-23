"""U29 deterministic fake-robot mission regression tests."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from replay_mission import replay, write_report, sha256

FIXTURE = ROOT / 'scripts/fixtures/mission_replay.json'


class MissionReplayTests(unittest.TestCase):
    def test_same_fixture_same_results_and_mock_motor(self):
        src_hash = sha256(FIXTURE)
        a, b = replay(FIXTURE), replay(FIXTURE)
        self.assertEqual(a, b)
        self.assertEqual(a['total_frames'], 6)
        self.assertEqual(a['final_state'], 'align_to_target')
        self.assertEqual(a['steering_mae'], 0.11552083)
        self.assertEqual(a['failure_events'], [])
        self.assertEqual(a['motor_adapter'], 'FakeRobot')
        self.assertFalse(a['hardware_initialized'])
        self.assertEqual(a['input']['fixture_sha256'], src_hash)
        self.assertTrue(a['input']['controller_source_sha256'])
        self.assertEqual(sha256(FIXTURE), src_hash)

    def test_failed_expectation_event_deterministic(self):
        data = json.loads(FIXTURE.read_text())
        data['frames'][0]['expected_state'] = 'complete'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.json'
            path.write_text(json.dumps(data))
            a = replay(path)
            b = replay(path)
        self.assertEqual(a, b)
        self.assertTrue(a['regression_failed'])
        self.assertEqual(a['failure_events'][0]['event'], 'state_mismatch')

    def test_terminal_failure_event(self):
        data = json.loads(FIXTURE.read_text())
        data['config'].update({'search_timeout_s': 0.1, 'max_retries_per_stage': 0})
        data['frames'] = data['frames'][:4] + [
            {'at_s': 4.0, 'detections': [], 'expected_state': 'failed'}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'failure.json'
            path.write_text(json.dumps(data))
            report = replay(path)
        self.assertEqual(report['final_state'], 'failed')
        self.assertEqual(report['failure_events'][-1]['event'], 'mission_failed')

    def test_nonmonotonic_time_and_invalid_detection_rejected(self):
        data = json.loads(FIXTURE.read_text())
        data['frames'][1]['at_s'] = 0.1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.json'
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'strictly increasing'):
                replay(path)
            data['frames'][1]['at_s'] = 1.3
            data['frames'][4]['detections'][0]['confidence'] = 2
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'confidence'):
                replay(path)

    def test_report_never_overwrites_fixture_or_existing_file(self):
        report = replay(FIXTURE)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'report.json'
            write_report(report, target, FIXTURE)
            self.assertEqual(json.loads(target.read_text()), report)
            with self.assertRaises(FileExistsError):
                write_report(report, target, FIXTURE)
            with self.assertRaises(ValueError):
                write_report(report, FIXTURE, FIXTURE)

    def test_regression_threshold_detects_drift(self):
        self.assertFalse(replay(FIXTURE, max_steering_mae=0.12)['regression_failed'])
        self.assertTrue(replay(FIXTURE, max_steering_mae=0.11)['regression_failed'])


if __name__ == '__main__':
    unittest.main()
