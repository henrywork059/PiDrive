"""U28: fail-closed safety rearm contract (no physical GPIO)."""
import threading
import unittest

from piserver.core.runtime_state import RuntimeState
from piserver.services.control_service import ControlService


class FakeMotor:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def stop(self):
        self.calls += 1
        if self.fail:
            raise OSError("simulated stop failure")


class SafetyRearmContractTests(unittest.TestCase):
    def make_control(self, fail=False):
        service = ControlService.__new__(ControlService)
        service.lock = threading.RLock()
        service.running = True
        service.state = RuntimeState()
        service.state.safety_stop = True
        service.state.active_algorithm = "auto"
        service.state.manual_steering = 0.9
        service.state.manual_throttle = 0.7
        service.state.motor_left = 0.8
        service.state.motor_right = 0.6
        service._manual_command_at = 1.0
        service._manual_command_timed_out = True
        service._processing_enabled_cached = True
        service.motor_service = FakeMotor(fail)
        return service

    def test_status_contract_is_additive_and_latched(self):
        s = self.make_control()
        status = s.safety_status()
        self.assertEqual(status["schema_version"], 1)
        self.assertEqual(status["component"], "PiServer")
        self.assertTrue(status["latched"])
        self.assertFalse(status["motion_allowed"])

    def test_rearm_requires_exact_true(self):
        s = self.make_control()
        for confirmation in (None, False, "true", 1):
            ok, _ = s.rearm_safety(confirm=confirmation)
            self.assertFalse(ok)
            self.assertTrue(s.state.safety_stop)
            self.assertEqual(s.motor_service.calls, 0)

    def test_rearm_clears_motion_and_leases_before_release(self):
        s = self.make_control()
        ok, _ = s.rearm_safety(confirm=True)
        self.assertTrue(ok)
        self.assertFalse(s.state.safety_stop)
        self.assertEqual(s.state.active_algorithm, "manual")
        self.assertEqual(s.state.manual_steering, 0.0)
        self.assertEqual(s.state.manual_throttle, 0.0)
        self.assertEqual(s.state.motor_left, 0.0)
        self.assertEqual(s.state.motor_right, 0.0)
        self.assertIsNone(s._manual_command_at)
        self.assertEqual(s.motor_service.calls, 1)

    def test_stop_failure_preserves_latch(self):
        s = self.make_control(fail=True)
        ok, _ = s.rearm_safety(confirm=True)
        self.assertFalse(ok)
        self.assertTrue(s.state.safety_stop)

    def test_legacy_clear_cannot_bypass_rearm(self):
        s = self.make_control()
        self.assertFalse(s.set_safety_stop(False))
        self.assertTrue(s.state.safety_stop)


if __name__ == "__main__":
    unittest.main()
