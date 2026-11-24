"""F4: verify current STOP outcome rather than historical motor errors."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pisd.app import create_app
from pisd.core.errors import PiSDErrorCodes


class StopOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with patch("pisd.app.RUNTIME_SETTINGS_PATH", Path(self.tmp.name) / "runtime.json"):
            self.app = create_app(hardware_enabled=False)
        self.services = self.app.config["pisd_services"]
        self.motor = self.services["motor"]
        self.ai = self.services["ai_drive"]
        self.client = self.app.test_client()

    def tearDown(self):
        self.ai.close()
        self.motor.close()
        self.services["camera"].stop()
        self.tmp.cleanup()

    def test_successful_stop_after_invalid_motor_test(self):
        invalid = self.client.post("/api/motor/test-channel", json={"side": "wrong"})
        self.assertEqual(invalid.status_code, 400)
        self.motor.update(0.2, 0.3, control_source="manual")
        response = self.client.post("/api/control/stop")
        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result["ok"])
        self.assertEqual(result["code"], PiSDErrorCodes.OK)
        self.assertEqual(result["motor"]["last_left"], 0.0)
        self.assertEqual(result["motor"]["last_right"], 0.0)
        self.assertTrue(self.motor.errors.history())

    def test_failed_adapter_stop_is_not_success(self):
        with patch.object(self.motor.left, "stop", return_value=False):
            response = self.client.post("/api/control/stop")
        result = response.get_json()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], PiSDErrorCodes.MOTOR_STOP_FAILED)

    def test_failed_ai_stop_is_not_success_even_when_motor_stop_succeeds(self):
        with patch.object(self.ai, "stop", return_value={"ok": False, "code": "PISD-AI-004", "message": "worker still active"}):
            response = self.client.post("/api/control/stop")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["ok"])

    def test_preview_preserving_stop_disables_ai_drive_output(self):
        with self.ai._lock:
            self.ai._mode = "drive"
            self.ai._drive_output_enabled = True
        response = self.client.post("/api/control/stop", json={"keep_ai_preview": True})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.ai._drive_output_enabled)
        self.assertEqual(self.motor.status()["last_left"], 0.0)


if __name__ == "__main__":
    unittest.main()
