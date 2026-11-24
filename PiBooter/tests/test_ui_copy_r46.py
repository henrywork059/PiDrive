"""R46 PiBooter empty/recovery copy checks without any network or Wi-Fi calls."""
from __future__ import annotations
import ast
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "pibooter" / "app.py"


class OnboardingCopyR46(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")
        ast.parse(cls.source, filename=str(APP))

    def test_no_network_scan_gives_refresh_or_manual_option(self):
        self.assertIn("No Wi-Fi networks found. Select Refresh scan or enter the SSID below.", self.source)
        self.assertIn('action="/rescan"', self.source)

    def test_no_saved_profile_points_to_connect(self):
        self.assertIn("No saved Wi-Fi profiles. Connect the Pi to Wi-Fi to create one.", self.source)

    def test_no_adapter_points_to_physical_diagnostic(self):
        self.assertIn("No network devices reported. Check the Pi Wi-Fi adapter.", self.source)

    def test_no_hotspot_clients_points_to_phone_connection(self):
        self.assertIn("No hotspot client yet. Connect your phone to the setup hotspot.", self.source)

    def test_permissions_and_csrf_enforcement_remain(self):
        self.assertIn("HTTPStatus.FORBIDDEN", self.source)
        self.assertIn("Cross-origin Wi-Fi changes are not allowed.", self.source)
        self.assertIn("request_token_matches", self.source)

    def test_recovery_for_authentication_and_timing_remains(self):
        self.assertIn("Wi-Fi authentication failed. Check the password and retry.", self.source)
        self.assertIn("Wi-Fi connection timed out. Check the signal and retry.", self.source)

    def test_forward_version_only(self):
        version = re.search(r'server_version\s*=\s*"PiBooter/0\.1\.(\d+)"', self.source)
        self.assertIsNotNone(version)
        self.assertGreaterEqual(int(version.group(1)), 7)


if __name__ == "__main__":
    unittest.main()
