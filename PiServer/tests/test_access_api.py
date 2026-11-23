"""PiServer auth integration tests (no motor hardware required)."""
from __future__ import annotations

import os
import unittest
from importlib.util import find_spec
from unittest.mock import patch

from test_control_service import DummyCamera, DummyMotor, DummyModel, DummyRecorder, DummyConfig, ManualAlgo
from piserver.services.control_service import ControlService


@unittest.skipUnless(find_spec("flask") is not None, "Flask is required for auth API integration tests")
class AccessApiTests(unittest.TestCase):
    TOKEN = "secret-token-long-enough-for-32-bytes-123"

    def build_app(self, *, token: str = ""):
        camera, motor, model, recorder, config = DummyCamera(), DummyMotor(), DummyModel(), DummyRecorder(), DummyConfig()
        camera.start = lambda: None
        camera.stop = lambda: None
        motor.close = lambda: None
        import piserver.app
        env = {"PISERVER_ACCESS_TOKEN": token}
        with (
            patch.dict(os.environ, env),
            patch("piserver.app.CameraService", return_value=camera),
            patch("piserver.app.MotorService", return_value=motor),
            patch("piserver.app.ModelService", return_value=model),
            patch("piserver.app.RecorderService", return_value=recorder),
            patch("piserver.app.ConfigStore", return_value=config),
            patch("piserver.app.build_registry", return_value={"manual": ManualAlgo()}),
            patch.object(ControlService, "start", lambda self: None),
        ):
            return piserver.app.create_app(), motor

    def test_anonymous_lan_requests_and_camera_are_protected(self):
        app, motor = self.build_app(token=self.TOKEN)
        with app.test_client() as client:
            self.assertEqual(client.get("/").status_code, 302)
            self.assertIn("/login", client.get("/").headers["Location"])
            self.assertEqual(client.get("/login").status_code, 200)
            for url in ("/api/status", "/api/camera/frame.jpg", "/video_feed", "/api/record/download?session=test"):
                self.assertEqual(client.get(url).status_code, 401, url)
            self.assertEqual(client.post("/api/control", json={"throttle": 0.9}).status_code, 401)
            self.assertEqual(client.post("/api/system/estop", json={"enabled": False}).status_code, 401)
            self.assertEqual(motor.update_calls, [])

    def test_browser_login_csrf_and_origin(self):
        app, motor = self.build_app(token=self.TOKEN)
        with app.test_client() as client:
            self.assertEqual(client.post("/api/auth/login", json={"token": "wrong"}).status_code, 401)
            login = client.post("/api/auth/login", json={"token": self.TOKEN}, headers={"Origin": "http://localhost"})
            self.assertEqual(login.status_code, 200)
            self.assertIn("HttpOnly", login.headers["Set-Cookie"])
            self.assertIn("SameSite=Strict", login.headers["Set-Cookie"])
            self.assertEqual(client.get("/api/status").status_code, 200)
            csrf = client.get("/api/auth/csrf").json["csrf_token"]
            self.assertTrue(csrf)
            self.assertEqual(client.post("/api/control", json={"throttle": 0.2}).status_code, 403)
            self.assertEqual(client.post("/api/control", json={"throttle": 0.2}, headers={"X-PiServer-CSRF": "bad"}).status_code, 403)
            self.assertEqual(client.post("/api/control", json={"throttle": 0.2}, headers={"X-PiServer-CSRF": csrf,"Origin":"http://attacker.test"}).status_code, 403)
            good = client.post("/api/control", json={"throttle": 0.2}, headers={"X-PiServer-CSRF": csrf})
            self.assertEqual(good.status_code, 200)
            self.assertAlmostEqual(good.json["manual_throttle"], 0.2)
            self.assertEqual(client.post("/api/auth/logout", headers={"X-PiServer-CSRF": csrf}).status_code, 200)
            self.assertEqual(client.get("/api/status").status_code, 401)

    def test_bearer_api_needs_no_cookie_csrf(self):
        app, _ = self.build_app(token=self.TOKEN)
        with app.test_client() as client:
            headers = {"Authorization": "Bearer " + self.TOKEN}
            self.assertEqual(client.get("/api/status", headers=headers).status_code, 200)
            resp = client.post("/api/control", json={"throttle": 0.15}, headers=headers)
            self.assertEqual(resp.status_code, 200)
            self.assertAlmostEqual(resp.json["manual_throttle"], 0.15)
            self.assertEqual(client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code, 401)

    def test_local_mode_rejects_non_loopback_even_if_exposed(self):
        app, _ = self.build_app(token="")
        with app.test_client() as client:
            self.assertEqual(client.get("/api/status").status_code, 200)
            self.assertEqual(client.get("/api/status", environ_overrides={"REMOTE_ADDR":"192.168.10.4"}).status_code, 403)
            self.assertEqual(client.post("/api/control", json={"throttle": 1}, environ_overrides={"REMOTE_ADDR":"192.168.10.4"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
