"""R47 request trace integration tests, no Flask/hardware installation needed.

Run: python -m unittest discover -s tests -p 'test_request_trace_r47.py' -v
The fake Flask module supplies only the after_request contract; it exercises
the actual component request_trace install hook and sanitizer functions.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import types
import unittest
from unittest.mock import Mock, patch

from custom_drive.request_trace import install_mutation_trace, safe_diagnostic, safe_diagnostic_text


class FakeResponse:
    def __init__(self, payload, status=400, is_json=True):
        self.payload = payload
        self.status_code = status
        self.is_json = is_json
        self.mimetype = "application/json" if is_json else "text/html"
        self.headers = {}
        self.body = None

    def get_json(self, silent=False):
        return self.payload if self.is_json else None

    def set_data(self, value):
        self.body = value
        self.payload = json.loads(value)


class FakeApp:
    def __init__(self):
        self.callback = None
        self.json = types.SimpleNamespace(dumps=json.dumps)
        self.logger = Mock()

    def after_request(self, callback):
        self.callback = callback
        return callback


class RequestTraceR47(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.request = types.SimpleNamespace(
            method="POST", path="/api/camera/apply",
            endpoint="api_camera_apply",
            headers={"Authorization": "Bearer should_not_log",
                     "X-Correlation-ID": "attacker_id"},
            data=b"password=superSecretKey",
        )
        fake_flask = types.ModuleType("flask")
        fake_flask.request = self.request
        fake_flask.jsonify = lambda *args, **kwargs: None
        with patch.dict(sys.modules, {"flask": fake_flask}):
            install_mutation_trace(self.app)
        self.assertIsNotNone(self.app.callback)

    def dispatch(self, payload, status=400, is_json=True):
        response = FakeResponse(payload, status=status, is_json=is_json)
        return self.app.callback(response)

    def test_failed_json_mutation_has_server_id_operation_and_header(self):
        r = self.dispatch({"ok": False, "message": "Invalid motor setting"}, 400)
        self.assertRegex(r.payload["correlation_id"], r"^[0-9a-f]{16}$")
        self.assertEqual(r.payload["operation"], "api_camera_apply")
        self.assertEqual(r.headers["X-Correlation-ID"], r.payload["correlation_id"])
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertEqual(r.status_code, 400)

    def test_http_200_ok_false_gets_trace_without_status_change(self):
        r = self.dispatch({"ok": False, "code": "PISD-CAM-002"}, 200)
        self.assertEqual(r.status_code, 200)
        self.assertRegex(r.payload["correlation_id"], r"^[0-9a-f]{16}$")

    def test_http_200_saved_false_gets_trace_without_mutation(self):
        r = self.dispatch({"ok": True, "saved": False, "config": {"value": 0.3}}, 200)
        self.assertTrue(r.payload["ok"])
        self.assertFalse(r.payload["saved"])
        self.assertEqual(r.payload["config"], {"value": 0.3})
        self.assertEqual(r.status_code, 200)
        self.assertIn("correlation_id", r.payload)

    def test_success_is_unchanged_and_unlogged(self):
        r = self.dispatch({"ok": True, "saved": True}, 200)
        self.assertEqual(r.payload, {"ok": True, "saved": True})
        self.assertNotIn("X-Correlation-ID", r.headers)
        self.app.logger.warning.assert_not_called()

    def test_failed_read_only_get_is_not_mutation_logged(self):
        self.request.method = "GET"
        r = self.dispatch({"ok": False, "message": "not found"}, 404)
        self.assertNotIn("correlation_id", r.payload)
        self.app.logger.warning.assert_not_called()

    def test_non_api_post_is_unchanged(self):
        self.request.path = "/login"
        r = self.dispatch({"ok": False, "message": "bad token"}, 401)
        self.assertNotIn("correlation_id", r.payload)

    def test_unexpected_html_500_becomes_safe_json_without_traceback(self):
        r = self.dispatch(None, 500, is_json=False)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.mimetype, "application/json")
        self.assertTrue(r.payload["message"].startswith("Pi request failed."))
        self.assertIn("correlation_id", r.payload)
        self.assertNotIn("traceback", r.payload)

    def test_exported_diagnostics_redact_paths_and_credentials(self):
        data = {
            "message": "password=orange /home/pi/secret/config.json",
            "context": {"path": "/home/pi/.config/password",
                        "access_token": "secret-token",
                        "status": "failed"},
            "files": ["C:\\Users\\Owner\\secret.txt", "/etc/passwd"],
        }
        safe = safe_diagnostic(data)
        encoded = json.dumps(safe)
        for secret in ("orange", "/home/pi/", "secret-token", "C:\\Users\\", "/etc/passwd"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(safe["context"]["status"], "failed")

    def test_trace_message_scrubs_secrets_paths_and_urls(self):
        r = self.dispatch({"ok": False, "message": "token=secret123 /home/pi/private https://pi.local/?password=x"}, 400)
        for sensitive in ("secret123", "/home/pi/private", "pi.local", "password=x"):
            self.assertNotIn(sensitive, r.payload["message"])

    def test_one_bounded_log_line_contains_only_safe_metadata(self):
        self.dispatch({"ok": False, "code": "PISD-APP-001", "message": "secret password=hello"}, 400)
        self.app.logger.warning.assert_called_once()
        args = self.app.logger.warning.call_args.args
        self.assertIn("id=%s operation=%s http_status=%d code=%s", args[0])
        self.assertRegex(args[1], r"^[0-9a-f]{16}$")
        self.assertEqual(args[2], "api_camera_apply")
        self.assertEqual(args[3], 400)
        self.assertEqual(args[4], "PISD-APP-001")
        self.assertNotIn("superSecretKey", repr(args))

    def test_attacker_supplied_correlation_id_not_accepted(self):
        r = self.dispatch({"ok": False, "correlation_id": "attacker_id"}, 403)
        self.assertNotEqual(r.payload["correlation_id"], "attacker_id")
        self.assertRegex(r.payload["correlation_id"], r"^[0-9a-f]{16}$")

    def test_endpoint_sanitized_and_bounded(self):
        self.request.endpoint = "api_/../token=" + "X" * 128
        r = self.dispatch({"ok": False}, 400)
        self.assertRegex(r.payload["operation"], r"^[a-zA-Z0-9_.-]{1,64}$")

    def test_error_dict_is_redacted_without_changing_success_payload_fields(self):
        r = self.dispatch({"ok": False, "error": {"context": {"file_path": "/tmp/secret",
                       "password": "abc"}, "message": "bad /root/private"},
                       "state": {"motor": {"speed": 0}}}, 400)
        self.assertNotIn("/tmp/secret", json.dumps(r.payload["error"]))
        self.assertNotIn("abc", json.dumps(r.payload["error"]))
        self.assertEqual(r.payload["state"]["motor"]["speed"], 0)

    def test_no_user_text_in_log_even_if_error_message_is_long(self):
        r = self.dispatch({"ok": False, "message": "p" * 500}, 500)
        self.assertLessEqual(len(r.payload["message"]), 240)
        self.assertNotIn("p" * 100, repr(self.app.logger.warning.call_args))

    def test_safe_diagnostic_does_not_print_bearer_credentials(self):
        self.assertNotIn("bearerSecret", safe_diagnostic_text("Bearer bearerSecret"))


if __name__ == "__main__":
    unittest.main()
