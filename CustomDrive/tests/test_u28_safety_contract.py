"""U28 contract checks for the Mission 1 safety latch (no real motors)."""
import threading
import unittest
from unittest.mock import Mock

try:
    from custom_drive.mission1_session_app import Mission1SessionContext
except ImportError:
    Mission1SessionContext = None


class FakeMotor:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def stop(self):
        self.calls += 1
        if self.fail:
            raise OSError("simulated motor failure")


@unittest.skipIf(Mission1SessionContext is None, "Mission 1 Flask/runtime dependencies unavailable")
class U28MissionSafetyTests(unittest.TestCase):
    def make_context(self, *, motor_fail=False, stop_ok=True):
        ctx = Mission1SessionContext.__new__(Mission1SessionContext)
        ctx._lock = threading.RLock()
        ctx._thread = None
        ctx._stop_event = threading.Event()
        ctx._safety_fault_latched = True
        ctx.failure_reason = "frame_stale"
        ctx.last_error = "stale camera"
        ctx.motor_service = FakeMotor(fail=motor_fail)
        ctx.last_command = {'mode': 'drive', 'steering': 0.8, 'throttle': 0.9}
        ctx.intended_motion = 'moving'
        ctx._record = Mock()
        ctx.stop_session = Mock(return_value=(stop_ok, "worker still active" if not stop_ok else "stopped"))
        return ctx

    def test_contract(self):
        ctx = self.make_context()
        s = ctx.safety_status()
        self.assertEqual(s["schema_version"], 1)
        self.assertEqual(s["component"], "CustomDrive")
        self.assertTrue(s["latched"])
        self.assertTrue(s["rearm_required"])
        self.assertFalse(s["motion_allowed"])

    def test_confirmation_is_explicit(self):
        ctx = self.make_context()
        for v in (None, False, "true", 1):
            ok, _ = ctx.rearm_safety(confirm=v)
            self.assertFalse(ok)
        self.assertEqual(ctx.motor_service.calls, 0)
        self.assertTrue(ctx._safety_fault_latched)

    def test_rearm_stops_and_preserves_a_fresh_start_boundary(self):
        ctx = self.make_context()
        ok, _ = ctx.rearm_safety(confirm=True)
        self.assertTrue(ok)
        self.assertFalse(ctx._safety_fault_latched)
        self.assertEqual(ctx.motor_service.calls, 1)
        self.assertEqual(ctx.last_command["throttle"], 0.0)
        self.assertEqual(ctx.intended_motion, "stopped")

    def test_motor_stop_failure_does_not_rearm(self):
        ctx = self.make_context(motor_fail=True)
        ok, _ = ctx.rearm_safety(confirm=True)
        self.assertFalse(ok)
        self.assertTrue(ctx._safety_fault_latched)

    def test_worker_stop_failure_does_not_rearm(self):
        ctx = self.make_context(stop_ok=False)
        ok, _ = ctx.rearm_safety(confirm=True)
        self.assertFalse(ok)
        self.assertTrue(ctx._safety_fault_latched)
        self.assertEqual(ctx.motor_service.calls, 0)


if __name__ == '__main__':
    unittest.main()
