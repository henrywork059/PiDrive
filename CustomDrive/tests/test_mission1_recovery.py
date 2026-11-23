"""Hardware-free tests for Mission 1 fail-closed recovery and structured reports."""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Flask is a runtime dependency; pure recovery methods can be verified without
# installing Flask in a safe simulation test environment.
try:
    import flask  # noqa: F401
except ImportError:
    flask_stub = types.ModuleType('flask')
    for name in ('Flask', 'Response', 'jsonify', 'render_template', 'request'):
        setattr(flask_stub, name, Mock())
    sys.modules['flask'] = flask_stub

from custom_drive.mission_safety import MissionAbort, save_mission_report
from custom_drive.mission1_session_app import (
    Mission1SessionContext, normalize_mission1_config, DEFAULT_MISSION1_CONFIG,
)


class FakeMotor:
    def __init__(self):
        self.stops = 0
        self.commands = []

    def stop(self):
        self.stops += 1

    def update(self, *args, **kwargs):
        self.commands.append((args, kwargs))


def context_for_tests():
    ctx = Mission1SessionContext.__new__(Mission1SessionContext)
    ctx._lock = threading.RLock()
    ctx._thread = None
    ctx._stop_event = threading.Event()
    ctx.motor_service = FakeMotor()
    ctx.arm_service = Mock()
    ctx.detector = Mock()
    ctx.detector.backend_ready.return_value = (True, 'ready')
    ctx.camera_service = Mock()
    ctx.current_phase = 'ai_pickup_search'
    ctx.mission_state = 'pickup_search'
    ctx.detail = 'searching'
    ctx.mission_outcome = 'running'
    ctx.failure_reason = ''
    ctx.failure_stage = ''
    ctx.target_loss_count = 0
    ctx.grip_confirmation = 'not_sensor_confirmed'
    ctx.held_class_id = None
    ctx.mission_report_path = ''
    ctx._session_report_id = 'test1234'
    ctx._report_written = False
    ctx._no_frame_since = None
    ctx._search_started_at = None
    ctx._search_kind = ''
    ctx.events = []
    ctx.last_error = ''
    ctx.last_command = {'mode': 'stop', 'throttle': 0, 'steering': 0}
    ctx.route_text = '--forward 2'
    ctx.started_at = 1.0
    ctx.arm_target_lock_engaged = False
    ctx.last_frame = {'width': 640, 'height': 360}
    ctx.pipeline_fps = 0.0
    ctx.pipeline_cycle_time_ms = 0.0
    ctx.target_found = False
    ctx.target_side = 'none'
    ctx.intended_motion = 'search_rotate_clockwise'
    ctx.last_detections = []
    ctx.control_target = None
    ctx.last_output_summary = ''
    ctx._record = Mock()
    ctx._shutdown_camera = Mock()
    ctx._mission_config = lambda: {'search_timeout_s': 4.0, 'frame_timeout_s': 1.0}
    return ctx


class PolicyTests(unittest.TestCase):
    def test_config_preserves_existing_trigger_semantics(self):
        cfg = normalize_mission1_config({'arm': {'grip_trigger_y_ratio': .83, 'dropoff_trigger_y_ratio': .28}})
        self.assertEqual(cfg['arm']['grip_trigger_y_ratio'], .83)
        self.assertEqual(cfg['arm']['dropoff_trigger_y_ratio'], .28)
        self.assertEqual(cfg['mission']['search_timeout_s'], 20.0)
        self.assertEqual(cfg['mission']['frame_timeout_s'], 2.0)

    def test_invalid_new_timeouts_clamped(self):
        cfg = normalize_mission1_config({'mission': {'search_timeout_s': -9, 'frame_timeout_s': 900}})
        self.assertGreaterEqual(cfg['mission']['search_timeout_s'], 2.0)
        self.assertLessEqual(cfg['mission']['frame_timeout_s'], 30.0)

    def test_no_frame_clears_motion_and_aborts_after_timeout(self):
        ctx = context_for_tests()
        ctx._fail_if_stale_frame(None, now=10, frame_present=False)
        self.assertEqual(ctx.motor_service.stops, 0)
        with self.assertRaises(MissionAbort) as raised:
            ctx._fail_if_stale_frame(None, now=11.1, frame_present=False)
        self.assertEqual(raised.exception.reason, 'frame_stale')
        self.assertEqual(ctx.motor_service.stops, 1)

    def test_cached_frame_age_aborts_immediately(self):
        ctx = context_for_tests()
        with self.assertRaises(MissionAbort) as raised:
            ctx._fail_if_stale_frame(1.8, now=10.0, frame_present=True)
        self.assertEqual(raised.exception.reason, 'frame_stale')
        self.assertEqual(ctx.motor_service.stops, 1)

    def test_fresh_frame_resets_no_frame_watchdog(self):
        ctx = context_for_tests()
        ctx._fail_if_stale_frame(None, now=10, frame_present=False)
        ctx._fail_if_stale_frame(0.05, now=10.8, frame_present=True)
        ctx._fail_if_stale_frame(None, now=13, frame_present=False)
        self.assertEqual(ctx.motor_service.stops, 0)

    def test_search_is_bounded_and_requires_operator_restart(self):
        ctx = context_for_tests()
        ctx._search_watchdog('pickup', False, now=10)
        ctx._search_watchdog('pickup', False, now=13.5)
        with self.assertRaises(MissionAbort) as raised:
            ctx._search_watchdog('pickup', False, now=14.1)
        self.assertEqual(raised.exception.reason, 'retry_exhausted')
        self.assertEqual(ctx.motor_service.stops, 1)

    def test_search_watchdog_switches_stage(self):
        ctx = context_for_tests()
        ctx._search_watchdog('pickup', False, now=10)
        ctx._search_watchdog('pickup', True, now=11)
        ctx._search_watchdog('dropoff', False, now=100)
        ctx._search_watchdog('dropoff', False, now=103)
        self.assertEqual(ctx.motor_service.stops, 0)

    def test_target_loss_fails_closed_no_moving_retry(self):
        ctx = context_for_tests()
        ctx.arm_target_lock_engaged = True
        with self.assertRaises(MissionAbort) as raised:
            ctx._handle_target_loss('pickup')
        self.assertEqual(raised.exception.reason, 'target_lost')
        self.assertEqual(ctx.target_loss_count, 1)
        self.assertEqual(ctx.motor_service.stops, 1)
        self.assertFalse(ctx.motor_service.commands)

    def test_missing_arm_pose_aborts_before_motion(self):
        ctx = context_for_tests()
        ctx._load_arm_role_pose = Mock(return_value=(False, 'No servo backend'))
        with self.assertRaises(MissionAbort) as raised:
            ctx._require_arm_role_pose('grip', reason='pickup')
        self.assertEqual(raised.exception.reason, 'arm_unavailable')
        self.assertEqual(ctx.motor_service.stops, 1)
        self.assertFalse(ctx.motor_service.commands)

    def test_successful_pose_is_not_grip_sensor_confirmation(self):
        ctx = context_for_tests()
        ctx._load_arm_role_pose = Mock(return_value=(True, 'pose applied'))
        ctx._require_arm_role_pose('grip', reason='pickup')
        self.assertEqual(ctx.grip_confirmation, 'not_sensor_confirmed')

    def test_start_arm_failure_cannot_execute_route_and_writes_failure_report(self):
        ctx = context_for_tests()
        ctx._require_arm_role_pose = Mock(side_effect=MissionAbort('arm_unavailable', 'start pose failed'))
        ctx._run_start_route = Mock()
        ctx._run_camera_boot = Mock()
        ctx._run_model_boot = Mock()
        ctx._run_detection_loop = Mock()
        with tempfile.TemporaryDirectory() as tmp, patch('custom_drive.mission1_session_app.CUSTOMDRIVE_ROOT', Path(tmp)):
            ctx._run_session()
            self.assertEqual(ctx.current_phase, 'failed')
            self.assertEqual(ctx.failure_reason, 'arm_unavailable')
            self.assertEqual(ctx.failure_stage, 'pickup_search')
            self.assertEqual(ctx.mission_outcome, 'failed')
            ctx._run_start_route.assert_not_called()
            self.assertGreater(ctx.motor_service.stops, 0)
            report = json.loads(Path(ctx.mission_report_path).read_text())
            self.assertEqual(report['failure_reason'], 'arm_unavailable')
            self.assertEqual(report['grip_confirmation'], 'not_sensor_confirmed')
            ctx._save_session_report()
            self.assertEqual(len(list((Path(tmp)/'mission_reports').glob('mission1_*.json'))), 1)

    def test_operator_stop_during_pose_is_stopped_not_failure(self):
        ctx = context_for_tests()
        ctx._require_arm_role_pose = Mock(side_effect=MissionAbort('operator_stopped', 'Stop requested'))
        with tempfile.TemporaryDirectory() as tmp, patch('custom_drive.mission1_session_app.CUSTOMDRIVE_ROOT', Path(tmp)):
            ctx._run_session()
            self.assertEqual(ctx.current_phase, 'stopped')
            self.assertEqual(ctx.mission_outcome, 'stopped')
            self.assertEqual(ctx.failure_reason, '')

    def test_hung_thread_prevents_handover_and_detector_unload(self):
        ctx = context_for_tests()
        ctx._thread = Mock()
        ctx._thread.is_alive.return_value = True
        ctx._thread.join.side_effect = lambda timeout: None
        ctx._thread.name = 'other'
        ok, message = ctx.stop_session(join=True)
        self.assertFalse(ok)
        self.assertIn('thread is still active', message)
        self.assertIsNotNone(ctx._thread)
        ctx.detector.unload.assert_not_called()
        ctx._shutdown_camera.assert_not_called()
        self.assertGreater(ctx.motor_service.stops, 0)

    def test_live_detection_refuses_stale_cached_frame_before_inference(self):
        import numpy as np
        ctx = context_for_tests()
        ctx.camera_service.get_latest_frame.return_value = np.zeros((12, 20, 3), dtype=np.uint8)
        ctx.camera_service.get_raw_frame_age.return_value = 4.0
        ctx.get_config = lambda: normalize_mission1_config(DEFAULT_MISSION1_CONFIG)
        ctx._pickup_classes = lambda: [1, 2]
        ctx._search_rotate_speed = lambda: .2
        with self.assertRaises(MissionAbort) as raised:
            ctx._run_detection_loop()
        self.assertEqual(raised.exception.reason, 'frame_stale')
        self.assertEqual(ctx.motor_service.stops, 1)
        ctx.detector.detect.assert_not_called()

    def test_failed_release_keeps_assumed_held_state_and_motor_stopped(self):
        import numpy as np
        ctx = context_for_tests()
        ctx.held_class_id = 1
        ctx.grip_confirmation = 'pose_applied_unverified'
        ctx.camera_service.get_latest_frame.return_value = np.zeros((360, 640, 3), dtype=np.uint8)
        ctx.camera_service.get_raw_frame_age.return_value = 0.05
        ctx.get_config = lambda: normalize_mission1_config(DEFAULT_MISSION1_CONFIG)
        ctx._pickup_classes = lambda: [1, 2]
        ctx._dropoff_class_for = lambda held: 3
        ctx._search_rotate_speed = lambda: .2
        ctx._build_detection_rows = lambda *args: []
        ctx._best_detection_for_classes = lambda *args, **kwargs: {
            'center': {'x': 0.0, 'y': -100.0}, 'box': {'width': 80, 'height': 90},
            'confidence': 0.9, 'class_id': 3,
        }
        ctx._mark_active_target = Mock()
        ctx._tracking_deadband_px = lambda w: 20.0
        ctx._target_close_enough = lambda *args: (True, 25.0, -40.0)
        ctx._update_target_side = Mock(return_value='center')
        ctx._stop_for_pose_transition = Mock(side_effect=lambda **kwargs: ctx.motor_service.stop())
        ctx._set_motion_state = Mock()
        ctx._require_arm_role_pose = Mock(side_effect=MissionAbort('arm_unavailable', 'release servo offline'))
        with self.assertRaises(MissionAbort) as raised:
            ctx._run_detection_loop()
        self.assertEqual(raised.exception.reason, 'arm_unavailable')
        self.assertEqual(ctx.held_class_id, 1)
        self.assertEqual(ctx.grip_confirmation, 'pose_applied_unverified')
        self.assertEqual(ctx.motor_service.stops, 1)
        ctx._require_arm_role_pose.assert_called_once()

    def test_thresholds_are_not_swapped_in_detection_branches(self):
        import inspect
        source = inspect.getsource(Mission1SessionContext._run_detection_loop)
        pickup = source[source.index('if self.held_class_id in pickup_classes:'):source.index('            else:\n                target = self._best_detection_for_classes(detection_rows, pickup_classes')]
        dropoff = source[source.index('            else:\n                target = self._best_detection_for_classes(detection_rows, pickup_classes'):]
        self.assertIn('self._dropoff_trigger_y_px(frame_h)', pickup)
        self.assertIn('self._pickup_trigger_y_px(frame_h)', dropoff)


class ReportTests(unittest.TestCase):
    def test_report_written_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = {'session_id': 'abc123', 'result': 'failed', 'failure_reason': 'frame_stale'}
            path = save_mission_report(Path(tmp), report)
            self.assertEqual(json.loads(path.read_text()), report)
            with self.assertRaises(FileExistsError):
                save_mission_report(Path(tmp), dict(report, result='success'))
            self.assertEqual(json.loads(path.read_text()), report)
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_invalid_report_session_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_mission_report(Path(tmp), {'session_id': '../bad'})
            self.assertFalse(list(Path(tmp).iterdir()))


if __name__ == '__main__':
    unittest.main()
