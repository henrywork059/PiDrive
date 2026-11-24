"""F3 integration tests against the real simulation-only PiSD application."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pisd.app import create_app
from pisd.core.access_control import validate_bind_host
from pisd.core.errors import PiSDErrorCodes

TOKEN = "test-only-" + "a" * 40
BASE = "http://192.168.1.2:5050"
LAN = {"REMOTE_ADDR": "192.168.1.3"}
ORIGIN = {"Origin": BASE, "Sec-Fetch-Site": "same-origin"}
BEARER = {"Authorization": "Bearer " + TOKEN}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def make_app(self, token):
        with patch.dict(os.environ, {"PISD_ACCESS_TOKEN": token, "PISD_SESSION_SECURE": "0"}), patch("pisd.app.RUNTIME_SETTINGS_PATH", Path(self.tmp.name) / "runtime.json"):
            app = create_app(hardware_enabled=False)
        self.addCleanup(app.config["pisd_services"]["camera"].stop)
        self.addCleanup(app.config["pisd_services"]["motor"].close)
        self.addCleanup(app.config["pisd_services"]["ai_drive"].close)
        return app

    def test_bind_policy_and_invalid_token_before_hardware(self):
        for host in ("127.0.0.1", "::1", "localhost"):
            validate_bind_host(host, {})
        with self.assertRaises(RuntimeError):
            validate_bind_host("0.0.0.0", {})
        validate_bind_host("0.0.0.0", {"PISD_ACCESS_TOKEN": TOKEN})
        with patch.dict(os.environ, {"PISD_ACCESS_TOKEN": "weak"}), patch("pisd.app.MotorService") as motor:
            with self.assertRaises(RuntimeError):
                create_app()
            motor.assert_not_called()

    def test_local_mode_rejects_remote_rebinding_and_cross_origin(self):
        app = self.make_app("")
        c = app.test_client()
        self.assertEqual(c.get("/api/status").status_code, 200)
        self.assertEqual(c.get("/api/status", base_url=BASE, environ_overrides=LAN).status_code, 403)
        self.assertEqual(c.post("/api/control/manual", base_url="http://attacker.example", json={"throttle": .5}).status_code, 403)
        self.assertEqual(c.post("/api/control/manual", headers={"Origin": "http://attacker.example"}, json={"throttle": .5}).status_code, 403)
        self.assertEqual(c.post("/api/control/stop", json={}).status_code, 200)

    def test_unauthorized_lan_has_no_service_side_effect(self):
        app = self.make_app(TOKEN)
        c = app.test_client()
        motor = app.config["pisd_services"]["motor"]
        with patch.object(motor, "update_manual") as move, patch.object(motor, "apply_settings") as settings:
            for route in ("/api/control/manual", "/api/motor/apply", "/api/control/heartbeat", "/api/control/stop", "/api/ai/start"):
                r = c.post(route, base_url=BASE, environ_overrides=LAN, json={"throttle": .5})
                self.assertEqual(r.status_code, 401, route)
                self.assertEqual(r.get_json()["code"], PiSDErrorCodes.API_AUTH_REQUIRED)
            move.assert_not_called()
            settings.assert_not_called()
        for route in ("/api/status", "/video_feed", "/api/recording/download.zip", "/testing/static/js/manual_drive.js"):
            self.assertEqual(c.get(route, base_url=BASE, environ_overrides=LAN).status_code, 401)
        self.assertEqual(c.get("/manual-drive", base_url=BASE, environ_overrides=LAN).status_code, 302)

    def test_session_login_same_origin_stop_beacon_and_logout(self):
        app = self.make_app(TOKEN)
        c = app.test_client()
        def post(path, **kw):
            return c.post(path, base_url=BASE, environ_overrides=LAN, **kw)
        self.assertEqual(post("/login", data={"token": TOKEN}).status_code, 403)
        self.assertEqual(post("/login", headers=ORIGIN, data={"token": "wrong"}).status_code, 401)
        r = post("/login", headers=ORIGIN, data={"token": TOKEN})
        self.assertEqual(r.status_code, 303)
        cookie = r.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertNotIn(TOKEN, cookie)
        self.assertEqual(c.get("/manual-drive", base_url=BASE, environ_overrides=LAN).status_code, 200)
        for headers in ({}, {"Origin": "http://evil.example"}, {"Sec-Fetch-Site": "same-site"}):
            self.assertEqual(post("/api/control/manual", headers=headers, json={"throttle": .3}).status_code, 403)
        move = post("/api/control/manual", headers=ORIGIN, json={"throttle": .3})
        self.assertTrue(move.get_json()["ok"])
        lease = move.get_json()["manual_lease_id"]
        self.assertEqual(post("/api/control/heartbeat", headers=ORIGIN, json={"lease_id": lease}).status_code, 200)
        stopped = post("/api/control/stop", headers={"Sec-Fetch-Site": "same-origin"}, data='{}', content_type="application/json")
        self.assertEqual(stopped.status_code, 200)
        self.assertTrue(stopped.get_json()["ok"])
        self.assertEqual(post("/api/control/heartbeat", headers=ORIGIN, json={"lease_id": lease}).status_code, 409)
        with patch.object(app.config["pisd_services"]["motor"].left, "stop", return_value=False):
            self.assertEqual(post("/logout", headers=ORIGIN).status_code, 503)
        self.assertEqual(c.get("/api/status", base_url=BASE, environ_overrides=LAN).status_code, 200)
        self.assertEqual(post("/logout", headers=ORIGIN).status_code, 303)
        self.assertEqual(c.get("/api/status", base_url=BASE, environ_overrides=LAN).status_code, 401)

    def test_bearer_api_and_degraded_stop(self):
        app = self.make_app(TOKEN)
        c = app.test_client()
        def post(path, **kw):
            return c.post(path, base_url=BASE, environ_overrides=LAN, headers=BEARER, **kw)
        r = post("/api/control/manual", json={"throttle": .3})
        self.assertTrue(r.get_json()["ok"])
        self.assertEqual(post("/api/control/heartbeat", json={"lease_id": r.get_json()["manual_lease_id"]}).status_code, 200)
        ai = app.config["pisd_services"]["ai_drive"]
        with ai._lock:
            ai._camera_frame_fault_latched = True
        r = post("/api/control/stop", json={})
        self.assertTrue(r.get_json()["ok"])
        self.assertTrue(ai.safety_status()["latched"])
        self.assertEqual(c.post("/api/control/manual", base_url=BASE, environ_overrides=LAN, headers={"Authorization": "Bearer wrong"}, json={}).status_code, 401)
        self.assertNotIn(TOKEN, str(c.get("/api/status", base_url=BASE, environ_overrides=LAN, headers=BEARER).get_json()))


if __name__ == "__main__":
    unittest.main()
