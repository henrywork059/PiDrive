"""R49 safe bounded event tests; no Flask or hardware initialized."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path
from dataclasses import dataclass

from custom_drive.recent_events import RecentEventRing, record_api_response

ROOT = Path(__file__).resolve().parents[1]
MODULE_FILE = ROOT / "custom_drive/recent_events.py"


@dataclass
class FakeRequest:
    method: str = "POST"
    endpoint: str = "api_estop"
    enabled: object = True

    def get_json(self, silent=True):
        return {"enabled": self.enabled}


class FakeResponse:
    is_json = True

    def __init__(self, payload=None, status=200):
        self.status_code = status
        self.payload = {"ok": True} if payload is None else payload

    def get_json(self, silent=True):
        return self.payload


class RecentEventsR49(unittest.TestCase):
    def test_fixed_capacity_and_latest_order(self):
        ring = RecentEventRing(5)
        for i in range(12):
            ring.record("safety_stop" if i % 2 else "model_load", "succeeded")
        self.assertEqual(len(ring.snapshot(80)), 5)
        self.assertEqual(ring.capacity, 5)

    def test_user_cannot_expand_capacity_beyond_128(self):
        self.assertEqual(RecentEventRing(10000).capacity, 128)
        self.assertEqual(RecentEventRing(0).capacity, 1)

    def test_timestamp_is_utc_and_iso_formatted(self):
        event = RecentEventRing().snapshot()
        self.assertEqual(event, [])
        ring = RecentEventRing()
        ring.record("startup")
        self.assertTrue(ring.snapshot()[0]["timestamp_utc"].endswith("+00:00"))

    def test_event_has_only_five_safe_fields(self):
        ring = RecentEventRing()
        ring.record("motor_apply", "succeeded")
        self.assertEqual(set(ring.snapshot()[0]),
                         {"timestamp_utc", "operation", "category", "title", "outcome"})

    def test_unknown_operation_is_not_echoed(self):
        ring = RecentEventRing()
        ring.record("password=super_secret C:\\Users\\private", "succeeded")
        event = ring.snapshot()[0]
        self.assertEqual(event["operation"], "other")
        self.assertNotIn("super_secret", str(event))
        self.assertNotIn("Users", str(event))

    def test_unknown_outcome_is_normalized(self):
        ring = RecentEventRing()
        ring.record("model_load", "Bearer secret_token")
        self.assertEqual(ring.snapshot()[0]["outcome"], "observed")

    def test_snapshot_is_not_internal_deque_reference(self):
        ring = RecentEventRing()
        ring.record("startup")
        items = ring.snapshot()
        items[0]["title"] = "modified"
        self.assertEqual(ring.snapshot()[0]["title"], "Service initialized")

    def test_safe_emergency_stop_is_explicit(self):
        ring = RecentEventRing()
        request = FakeRequest(enabled=True)
        response = FakeResponse()
        self.assertIs(record_api_response(ring, response, request, {"api_estop": "safety_stop"}), response)
        event = ring.snapshot()[0]
        self.assertEqual(event["operation"], "safety_stop")
        self.assertEqual(event["category"], "safety")
        self.assertIn("STOP", event["title"])

    def test_estop_disabled_classifies_as_rearm_not_stop(self):
        ring = RecentEventRing()
        request = FakeRequest(enabled=False)
        record_api_response(ring, FakeResponse(), request, {"api_estop": "safety_stop"})
        self.assertEqual(ring.snapshot()[0]["operation"], "safety_rearm")

    def test_rejected_emergency_stop_is_not_claimed_successful(self):
        ring = RecentEventRing()
        record_api_response(ring, FakeResponse({"ok": False}, status=409),
                            FakeRequest(), {"api_estop": "safety_stop"})
        self.assertEqual(ring.snapshot()[0]["outcome"], "failed")

    def test_http_200_body_failure_is_recorded_failed(self):
        ring = RecentEventRing()
        record_api_response(ring, FakeResponse({"ok": False}, status=200),
                            FakeRequest(), {"api_estop": "safety_stop"})
        self.assertEqual(ring.snapshot()[0]["outcome"], "failed")

    def test_unconfirmed_save_is_partial(self):
        ring = RecentEventRing()
        request = FakeRequest(endpoint="api_save")
        record_api_response(ring, FakeResponse({"ok": True, "saved": False}),
                            request, {"api_save": "config_save"})
        self.assertEqual(ring.snapshot()[0]["outcome"], "partial")

    def test_get_does_not_record_event(self):
        ring = RecentEventRing()
        record_api_response(ring, FakeResponse(), FakeRequest(method="GET"),
                            {"api_estop": "safety_stop"})
        self.assertEqual(ring.snapshot(), [])

    def test_unknown_and_high_frequency_control_are_excluded(self):
        ring = RecentEventRing()
        record_api_response(ring, FakeResponse(), FakeRequest(endpoint="api_control"),
                            {"api_estop": "safety_stop"})
        self.assertEqual(ring.snapshot(), [])

    def test_failure_does_not_log_payload_or_secrets(self):
        ring = RecentEventRing()
        record_api_response(ring,
            FakeResponse({"ok": False, "message": "password=superSecret /home/pi/private",
                          "config": {"token": "bearerSecret"}}, 400),
            FakeRequest(), {"api_estop": "safety_stop"})
        output = str(ring.snapshot())
        for secret in ("superSecret", "/home/pi/", "bearerSecret", "config"):
            self.assertNotIn(secret, output)

    def test_source_does_not_persist_or_network_publish(self):
        source = MODULE_FILE.read_text(encoding="utf-8")
        ast.parse(source, filename=str(MODULE_FILE))
        for forbidden in ("requests.post(", "urllib.", "socket.", ".write_text(",
                          "open(", "subprocess.", "save_config(", "motor_service.update("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
