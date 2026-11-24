"""F2 manual lease: fake-clock policy and real watchdog smoke in simulation."""
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pisd.app import create_app
from pisd.services.motor_service import MotorService


class ManualLeaseTests(unittest.TestCase):
    def setUp(self):
        self.motor = MotorService(hardware_enabled=False)

    def tearDown(self):
        self.motor.close()

    def test_expiry_renewal_and_no_replay(self):
        with patch.object(self.motor, "_ensure_lease_worker_locked"), patch("pisd.services.motor_service.time.monotonic", return_value=10.0):
            _, _, token = self.motor.update_manual(0.0, 0.4)
        self.assertTrue(token)
        with patch("pisd.services.motor_service.time.monotonic", return_value=10.5):
            self.assertTrue(self.motor.renew_manual_lease(token))
        with patch("pisd.services.motor_service.time.monotonic", return_value=11.4):
            self.assertFalse(self.motor.renew_manual_lease(token))
        self.assertEqual(self.motor.status()["last_left"], 0)
        self.assertTrue(self.motor.status()["manual_command_timed_out"])
        self.assertFalse(self.motor.renew_manual_lease(token))

    def test_stop_and_new_owner_invalidate_token(self):
        with patch.object(self.motor, "_ensure_lease_worker_locked"):
            _, _, first = self.motor.update_manual(0.0, 0.4)
            _, _, second = self.motor.update_manual(0.0, 0.2, control_source="manual_assist")
        self.assertNotEqual(first, second)
        self.assertFalse(self.motor.renew_manual_lease(first))
        self.motor.stop()
        self.assertFalse(self.motor.renew_manual_lease(second))
        with patch.object(self.motor, "_ensure_lease_worker_locked"):
            _, _, third = self.motor.update_manual(0.0, 0.4)
        self.motor.update(0, 0.2, control_source="ai")
        self.assertFalse(self.motor.renew_manual_lease(third))
        self.assertEqual(self.motor.status()["last_command"]["control_source"], "ai")

    def test_worker_expires_without_browser_or_status_request(self):
        self.motor.manual_command_timeout_s = 0.05
        self.motor.update_manual(0.0, 0.3)
        deadline = time.monotonic() + 1.0
        while self.motor.last_left != 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(self.motor.status()["last_left"], 0)
        self.assertTrue(self.motor.status()["manual_command_timed_out"])

    def test_http_heartbeat_cannot_restart_after_stop(self):
        with tempfile.TemporaryDirectory() as tmp, patch("pisd.app.RUNTIME_SETTINGS_PATH", Path(tmp) / "runtime.json"):
            app = create_app(hardware_enabled=False)
            motor = app.config["pisd_services"]["motor"]
            client = app.test_client()
            try:
                response = client.post("/api/control/manual", json={"throttle": 0.3})
                token = response.get_json()["manual_lease_id"]
                self.assertTrue(token)
                self.assertNotIn(token, str(client.get("/api/status").get_json()))
                self.assertEqual(client.post("/api/control/heartbeat", json={"lease_id": token}).status_code, 200)
                client.post("/api/control/stop", json={})
                self.assertEqual(client.post("/api/control/heartbeat", json={"lease_id": token}).status_code, 409)
                self.assertEqual(motor.status()["last_left"], 0)
            finally:
                app.config["pisd_services"]["ai_drive"].close()
                motor.close()
                app.config["pisd_services"]["camera"].stop()


if __name__ == "__main__":
    unittest.main()
