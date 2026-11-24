"""U28: explicit stale-camera rearm requires recovery (no Pi hardware)."""
import tempfile
import unittest

from pisd.services.ai_drive_service import AIDriveService


class FakeCamera:
    running = True

    def __init__(self, *, progresses=True):
        self.progresses = progresses

    def get_jpeg_frame_info(self):
        return b"cached", 7, "", 6

    def wait_for_jpeg_frame(self, last_seq=None, timeout=0.5):
        return (b"fresh", 8, "", 5) if self.progresses else (None, 7, "", 0)


class FakeMotor:
    def __init__(self, *, fail=False):
        self.stops = 0
        self.fail = fail

    def stop(self):
        self.stops += 1
        if self.fail:
            raise OSError("simulated stop failure")


class U28SafetyRearmTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ai = AIDriveService(self.dir.name)
        self.ai._camera_frame_fault_latched = True

    def tearDown(self):
        self.ai.stop()
        self.dir.cleanup()

    def test_contract_and_latch_survives_stop(self):
        status = self.ai.safety_status()
        self.assertEqual(status["schema_version"], 1)
        self.assertEqual(status["component"], "PiSD")
        self.assertTrue(status["latched"])
        self.assertFalse(status["motion_allowed"])
        self.ai.stop()
        self.assertTrue(self.ai.safety_status()["latched"])

    def test_repeated_stop_preserves_latch_until_checked_rearm(self):
        camera, motor = FakeCamera(), FakeMotor()
        for _ in range(2):
            self.ai.stop(motor)
            self.assertTrue(self.ai.safety_status()["latched"])
            self.assertFalse(self.ai.safety_status()["motion_allowed"])
        self.assertFalse(self.ai.rearm_camera_fault(
            FakeCamera(progresses=False), motor, confirm=True)["ok"])
        self.assertTrue(self.ai.safety_status()["latched"])
        self.assertTrue(self.ai.rearm_camera_fault(camera, motor, confirm=True)["ok"])
        self.assertFalse(self.ai.safety_status()["latched"])
        self.assertEqual(motor.stops, 3)

    def test_stop_motor_failure_does_not_clear_latch(self):
        result = self.ai.stop(FakeMotor(fail=True))
        self.assertFalse(result.get("ok"))
        self.assertTrue(self.ai.safety_status()["latched"])
        self.assertFalse(self.ai.safety_status()["motion_allowed"])

    def test_explicit_false_motor_stop_does_not_clear_latch(self):
        motor = FakeMotor()
        motor.stop = lambda: False
        self.assertFalse(self.ai.stop(motor)["ok"])
        self.assertFalse(self.ai.rearm_camera_fault(FakeCamera(), motor, confirm=True)["ok"])
        self.assertTrue(self.ai.safety_status()["latched"])

    def test_start_does_not_implicitly_rearm(self):
        result = self.ai.start(FakeCamera(), FakeMotor(), mode="drive", safety_ack=True, enable_motor_output=True)
        self.assertFalse(result.get("ok"))
        self.assertTrue(self.ai.safety_status()["latched"])

    def test_exact_confirm_and_fresh_frame_required(self):
        camera, motor = FakeCamera(), FakeMotor()
        for value in (None, False, "true", 1):
            self.assertFalse(self.ai.rearm_camera_fault(camera, motor, confirm=value)["ok"])
        self.assertEqual(motor.stops, 0)
        self.assertFalse(self.ai.rearm_camera_fault(FakeCamera(progresses=False), motor, confirm=True)["ok"])
        self.assertEqual(motor.stops, 0)
        result = self.ai.rearm_camera_fault(camera, motor, confirm=True)
        self.assertTrue(result["ok"])
        self.assertFalse(self.ai.safety_status()["latched"])
        self.assertEqual(motor.stops, 1)
        self.assertEqual(self.ai.status()["last_safe_command"]["throttle"], 0.0)

    def test_motor_stop_failure_does_not_clear_latch(self):
        motor = FakeMotor(fail=True)
        result = self.ai.rearm_camera_fault(FakeCamera(), motor, confirm=True)
        self.assertFalse(result["ok"])
        self.assertTrue(self.ai.safety_status()["latched"])

    def test_camera_must_be_running(self):
        camera = FakeCamera()
        camera.running = False
        result = self.ai.rearm_camera_fault(camera, FakeMotor(), confirm=True)
        self.assertFalse(result["ok"])
        self.assertTrue(self.ai.safety_status()["latched"])


if __name__ == "__main__":
    unittest.main()
