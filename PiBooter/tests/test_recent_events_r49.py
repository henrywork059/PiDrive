"""R49 PiBooter sanitized event projection and browser/source safety tests."""
from __future__ import annotations

import ast
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pibooter.recent_events import classify, project_recent_events
from pibooter.state import RuntimeState

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "pibooter" / "app.py"
MODULE = ROOT / "pibooter" / "recent_events.py"


def item(message, ts=1700000000.0, level="info"):
    return {"message": message, "ts": ts, "level": level}


class PiBooterRecentEventsR49(unittest.TestCase):
    def test_successful_wifi_connection_is_classified_without_ssid(self):
        events = project_recent_events([item("Pi connected to SecretHomeWiFi. Last known IP 192.168.0.2")])
        self.assertEqual(events[0]["operation"], "wifi_connect")
        self.assertEqual(events[0]["outcome"], "succeeded")
        self.assertNotIn("SecretHomeWiFi", str(events))
        self.assertNotIn("192.168", str(events))

    def test_failed_wifi_connection_never_exports_password(self):
        log = item("Wi-Fi connection failed for SecretHomeWiFi: password=superSecret")
        events = project_recent_events([log])
        self.assertEqual(events[0]["outcome"], "failed")
        self.assertNotIn("superSecret", json.dumps(events))

    def test_wifi_scan_and_forget_are_distinct_operator_events(self):
        events = project_recent_events([
            item("Wi-Fi scan refreshed. Found 6 network(s)."),
            item("Forgot saved Wi-Fi profile: HomeNetwork."),
        ])
        self.assertEqual([e["operation"] for e in events], ["wifi_scan", "wifi_forget"])

    def test_hotspot_start_stop_have_distinct_entries(self):
        events = project_recent_events([
            item("Hotspot started: SuperSecretName (http://192.168.4.1)"),
            item("Hotspot stopped before PiBooter exit."),
        ])
        self.assertEqual([x["operation"] for x in events], ["hotspot_start", "hotspot_stop"])
        self.assertNotIn("SuperSecretName", str(events))

    def test_monitor_errors_are_generic_no_raw_exception(self):
        events = project_recent_events([item("Background monitor error: /root/private token=bad")])
        self.assertEqual(events[0]["operation"], "network_error")
        self.assertNotIn("private", str(events))

    def test_http_access_logs_and_unrecognized_messages_are_excluded(self):
        logs = [
            item("HTTP GET /?ssid=Home&password=bad HTTP/1.1 200"),
            item("Something sensitive /root/foo"),
        ]
        self.assertEqual(project_recent_events(logs), [])

    def test_invalid_timestamps_are_dropped(self):
        logs = [item("PiBooter controller initialised.", ts="not a timestamp"),
                item("PiBooter controller initialised.", ts=float("inf"))]
        self.assertEqual(project_recent_events(logs), [])

    def test_output_has_bounded_public_schema(self):
        events = project_recent_events([item("PiBooter controller initialised.")])
        self.assertEqual(set(events[0]),
                         {"timestamp_utc", "operation", "category", "title", "outcome"})
        self.assertIn("+00:00", events[0]["timestamp_utc"])

    def test_projection_bounded_even_when_underlying_logs_overflow(self):
        logs = [item("Wi-Fi scan refreshed. Found 2 network(s).", 1700000000.0 + i) for i in range(1000)]
        self.assertEqual(len(project_recent_events(logs)), 80)
        self.assertEqual(len(project_recent_events(logs, limit=12)), 12)

    def test_existing_state_log_is_already_fixed_capacity(self):
        state = RuntimeState(log_limit=20)
        for i in range(100):
            state.log("Wi-Fi scan refreshed. Found 1 network(s).")
        self.assertEqual(len(state.snapshot()["logs"]), 20)
        self.assertEqual(len(project_recent_events(state.snapshot()["logs"])), 20)

    def test_no_new_network_or_config_write_in_projection(self):
        source = MODULE.read_text(encoding="utf-8")
        ast.parse(source, filename=str(MODULE))
        for forbidden in ("nmcli", "start_hotspot(", "stop_hotspot(", "save(", "requests.",
                          "socket.", "subprocess.", ".write_text(", "password="):
            self.assertNotIn(forbidden, source)

    def test_get_handler_has_explicit_read_only_event_route(self):
        src = APP.read_text(encoding="utf-8")
        ast.parse(src, filename=str(APP))
        self.assertIn('if path == "/api/recent-events":', src)
        self.assertIn("project_recent_events(snapshot.get(\"logs\", []))", src)
        self.assertIn("self.controller.state.snapshot()", src)

    def test_ui_preserves_network_post_security(self):
        src = APP.read_text(encoding="utf-8")
        for required in ("authorized_setup_client(", "trusted_post_origin(",
                         "request_token_matches(", "hotspot_password_safe("):
            self.assertIn(required, src)

    def test_recent_operator_display_does_not_use_raw_logs(self):
        src = APP.read_text(encoding="utf-8")
        self.assertIn('safe_events = project_recent_events(snapshot.get("logs", []))', src)
        self.assertIn('id="recent-events-output"', src)
        self.assertIn("Copy events", src)

    def test_no_motor_stop_implementation_in_pibooter_event_view(self):
        src = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("motor_service", src)
        self.assertIsNone(classify("HTTP POST /system/estop"))

    def test_version_marker_advances_component_line(self):
        self.assertIn('server_version = "PiBooter/0.1.8"', APP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
