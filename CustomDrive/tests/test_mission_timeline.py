"""Deterministic, simulation-free tests for R33 Mission 1 stage observations."""
from __future__ import annotations

import unittest

from custom_drive.mission_timeline import MissionProgressTimeline


def timeline():
    progress = MissionProgressTimeline()
    progress.reset('session-test')
    return progress


class MissionTimelineTests(unittest.TestCase):
    def test_initial_empty_session_is_not_running(self):
        t = MissionProgressTimeline()
        t.observe('start_route')
        self.assertIsNone(t.snapshot()['current_step'])
        self.assertEqual(t.snapshot()['recent_steps'], [])

    def test_route_then_camera_starts_at_real_observed_phases(self):
        t = timeline()
        t.observe('start_route', 'pickup_search')
        t.observe('camera_boot', 'pickup_search')
        snapshot = t.snapshot()
        self.assertEqual([x['id'] for x in snapshot['recent_steps']], ['route', 'camera'])
        self.assertEqual(snapshot['last_completed_step']['id'], 'route')

    def test_only_observed_phases_are_in_history(self):
        t = timeline()
        t.observe('start_route')
        t.observe('model_boot')
        self.assertEqual([x['id'] for x in t.snapshot()['recent_steps']], ['route', 'model'])
        self.assertNotIn('camera', [x['id'] for x in t.snapshot()['recent_steps']])

    def test_repeat_poll_does_not_duplicate_stages(self):
        t = timeline()
        for _ in range(100):
            t.observe('ai_pickup_search', 'pickup_search')
        self.assertEqual(len(t.snapshot()['recent_steps']), 1)

    def test_fast_grip_stop_then_pose_keeps_one_stage(self):
        t = timeline()
        t.observe('ai_pickup_stop', 'pickup_stop_for_grip')
        t.observe('ai_pickup_grip', 'pickup_grip')
        snap = t.snapshot()
        self.assertEqual(len(snap['recent_steps']), 1)
        self.assertEqual(snap['current_step']['label'], 'Grip · pose')

    def test_lift_completes_grip_not_lift(self):
        t = timeline()
        t.observe('ai_pickup_grip')
        t.observe('ai_pickup_lift')
        snap = t.snapshot()
        self.assertEqual(snap['last_completed_step']['id'], 'grip')
        self.assertEqual(snap['current_step']['id'], 'lift')

    def test_missing_frame_does_not_complete_pickup(self):
        t = timeline()
        t.observe('ai_pickup_track')
        t.observe('ai_wait_frame')
        snap = t.snapshot()
        self.assertIsNone(snap['last_completed_step'])
        self.assertEqual(snap['recent_steps'][0]['state'], 'left')
        self.assertEqual(snap['current_step']['id'], 'wait_frame')

    def test_recovery_from_wait_does_not_complete_pause(self):
        t = timeline()
        t.observe('ai_wait_frame')
        t.observe('ai_pickup_search')
        self.assertIsNone(t.snapshot()['last_completed_step'])

    def test_backtracking_does_not_claim_alignment_completed(self):
        t = timeline()
        t.observe('ai_pickup_track')
        t.observe('ai_pickup_search')
        self.assertIsNone(t.snapshot()['last_completed_step'])

    def test_failure_retains_current_failed_stage(self):
        t = timeline()
        t.observe('ai_pickup_grip', 'pickup_grip')
        t.observe('failed', 'failed', outcome='failed',
                  failure_reason='arm_unavailable', failure_stage='pickup_grip', last_error='servo failed')
        snap = t.snapshot()
        self.assertEqual(snap['current_step']['id'], 'grip')
        self.assertEqual(snap['current_step']['state'], 'failed')
        self.assertEqual(snap['last_failure']['reason'], 'arm_unavailable')
        self.assertEqual(snap['last_failure']['stage'], 'pickup_grip')

    def test_stop_never_marks_active_stage_completed(self):
        t = timeline()
        t.observe('ai_dropoff_search')
        t.observe('stopped', outcome='stopped')
        snap = t.snapshot()
        self.assertEqual(snap['current_step']['state'], 'interrupted')
        self.assertIsNone(snap['last_completed_step'])

    def test_failure_remains_after_repeated_terminal_polling(self):
        t = timeline()
        t.observe('ai_pickup_grip')
        t.observe('failed', outcome='failed', failure_reason='target_lost', failure_stage='pickup_grip')
        t.observe('failed', outcome='failed', failure_reason='different', failure_stage='failed')
        self.assertEqual(t.snapshot()['last_failure']['reason'], 'target_lost')

    def test_rearm_does_not_implicitly_reset_history(self):
        t = timeline()
        t.observe('ai_pickup_grip')
        t.observe('failed', outcome='failed', failure_reason='arm_unavailable')
        t.observe('failed', outcome='failed')
        self.assertEqual(t.snapshot()['last_failure']['reason'], 'arm_unavailable')

    def test_new_session_explicitly_resets_previous_failure(self):
        t = timeline()
        t.observe('failed', outcome='failed', failure_reason='runtime_error')
        t.reset('session-two')
        t.observe('route_pending')
        self.assertIsNone(t.snapshot()['last_failure'])
        self.assertEqual(t.snapshot()['session_id'], 'session-two')
        self.assertEqual(len(t.snapshot()['recent_steps']), 1)

    def test_cycles_only_increase_after_release_or_reset(self):
        t = timeline()
        t.observe('ai_pickup_search')
        t.observe('ai_pickup_track')
        t.observe('ai_pickup_search')
        self.assertEqual(t.snapshot()['current_step']['cycle'], 1)
        t.observe('ai_dropoff_release')
        t.observe('ai_pickup_search')
        self.assertEqual(t.snapshot()['current_step']['cycle'], 2)

    def test_release_is_not_complete_until_next_observed_step(self):
        t = timeline()
        t.observe('ai_dropoff_release')
        self.assertIsNone(t.snapshot()['last_completed_step'])
        t.observe('ai_reverse_reset')
        self.assertEqual(t.snapshot()['last_completed_step']['id'], 'release')

    def test_completed_outcome_marks_current_step(self):
        t = timeline()
        t.observe('ai_dropoff_release')
        t.observe('complete', outcome='complete')
        self.assertEqual(t.snapshot()['last_completed_step']['id'], 'release')
        self.assertEqual(t.snapshot()['current_step']['state'], 'completed')

    def test_arm_settle_note_is_observed_not_computed(self):
        t = timeline()
        t.observe('ai_pickup_grip')
        snap = t.snapshot(outcome='running', detail='Loading servo pose',
                          arm_sequence={'state':'grip_loaded', 'note':'Settling #3'})
        self.assertEqual(snap['arm_sequence']['note'], 'Settling #3')
        self.assertEqual(snap['detail'], 'Loading servo pose')

    def test_history_is_bounded(self):
        t = MissionProgressTimeline(history_limit=8)
        t.reset('bounded')
        for _ in range(20):
            t.observe('ai_pickup_search')
            t.observe('ai_pickup_track')
        self.assertEqual(len(t._history), 8)
        self.assertEqual(len(t.snapshot()['recent_steps']), 8)

    def test_unrecognized_phases_are_not_inferred(self):
        t = timeline()
        t.observe('robot_maybe_has_gripped')
        self.assertEqual(t.snapshot()['recent_steps'], [])

    def test_snapshot_does_not_mutate_internal_history(self):
        t = timeline()
        t.observe('ai_pickup_search')
        snap = t.snapshot()
        snap['recent_steps'][0]['label'] = 'Forged'
        self.assertEqual(t.snapshot()['current_step']['label'], 'Search · pickup')

    def test_model_boot_is_observed_separately_from_camera(self):
        t = timeline()
        t.observe('camera_boot')
        t.observe('model_boot')
        self.assertEqual(t.snapshot()['current_step']['label'], 'Model loading')
        self.assertEqual(t.snapshot()['last_completed_step']['label'], 'Camera startup')


if __name__ == '__main__':
    unittest.main()
