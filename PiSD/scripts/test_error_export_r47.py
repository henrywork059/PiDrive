"""R47 PiSD diagnostic-export redaction, hardware/Flask-free."""
from __future__ import annotations

import json
import unittest

from pisd.core.errors import ErrorReporter, PiSDErrorCodes, report_payload


class ErrorExportR47(unittest.TestCase):
    def setUp(self):
        self.reporter = ErrorReporter("test", max_history=4)
        self.report = self.reporter.report(
            PiSDErrorCodes.API_SERVICE_EXCEPTION,
            "password=secretKey /home/pi/private/model.tflite",
            context={
                "path": "/home/pi/.config/credentials",
                "authorization": "Bearer sensitive",
                "source": "sensor",
                "file_path": "C:\\Users\\Owner\\token.txt",
            },
            exc=RuntimeError("access token=secretKey in /root/private"),
            include_traceback=True,
        )

    def test_history_scrubs_message_context_and_token(self):
        result = self.reporter.history(limit=1)[0]
        encoded = json.dumps(result)
        for secret in ("secretKey", "/home/pi/", "C:\\Users\\", "Bearer sensitive"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(result["context"]["source"], "sensor")
        self.assertEqual(result["code"], PiSDErrorCodes.API_SERVICE_EXCEPTION)

    def test_traceback_is_not_exported_even_when_explicitly_requested(self):
        result = self.reporter.history(limit=1, include_traceback=True)[0]
        self.assertEqual(result["traceback"], "[redacted: traceback not exported]")
        self.assertNotIn("secretKey", json.dumps(result))

    def test_status_fields_do_not_reexpose_unsanitized_last_error(self):
        status = self.reporter.status_fields(limit=1)
        self.assertNotIn("secretKey", json.dumps(status))
        self.assertIn("recent_errors", status)

    def test_mutation_error_embedded_diagnostics_are_sanitized(self):
        data = report_payload(False, self.report)
        self.assertFalse(data["ok"])
        self.assertNotIn("secretKey", json.dumps(data))
        self.assertEqual(data["error"]["context"]["source"], "sensor")

    def test_history_stays_bounded_as_before(self):
        for i in range(8):
            self.reporter.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, "safe error " + str(i))
        self.assertEqual(len(self.reporter.history(limit=20)), 4)


if __name__ == "__main__":
    unittest.main()
