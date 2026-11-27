"""F7: recovery is byte-for-byte and failed writes do not change effective settings."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pisd.app import create_app
from pisd.core.settings_manager import SettingsManager


class ConfigRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "runtime_settings.json"

    def test_corruption_preserved_before_save_and_restart(self):
        for raw in (b'{"manual_drive":', b'[]', b'{"manual_drive":null}', b'\xff'):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                store = SettingsManager(self.path)
                status = store.recovery_status()
                backup = self.path.parent / status["backup"]
                self.assertEqual(backup.read_bytes(), raw)
                self.assertEqual(self.path.read_bytes(), raw)
                self.assertTrue(status["warning"])
                self.assertTrue(store.save({"manual_drive": {"speed": 0.37}})[0])
                self.assertEqual(backup.read_bytes(), raw)
                self.assertAlmostEqual(SettingsManager(self.path).get()["manual_drive"]["speed"], 0.37)

    def test_external_corruption_detected_before_write(self):
        store = SettingsManager(self.path)
        self.assertTrue(store.save({"manual_drive": {"speed": 0.31}})[0])
        raw = b'{"motor":'
        self.path.write_bytes(raw)
        self.assertTrue(store.save({"manual_drive": {"speed": 0.42}})[0])
        self.assertEqual((self.path.parent / store.recovery_status()["backup"]).read_bytes(), raw)
        self.assertAlmostEqual(store.get()["manual_drive"]["speed"], 0.42)

    def test_backup_failure_blocks_save_and_reset_without_memory_mutation(self):
        store = SettingsManager(self.path)
        self.assertTrue(store.save({"manual_drive": {"speed": 0.32}})[0])
        raw = b'{"manual_drive":'
        self.path.write_bytes(raw)
        with patch("pisd.core.config_recovery.os.open", side_effect=PermissionError("denied")):
            self.assertFalse(store.save({"manual_drive": {"speed": 0.99}})[0])
            self.assertFalse(store.reset()[0])
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertAlmostEqual(store.get()["manual_drive"]["speed"], 0.32)
        self.assertTrue(store.recovery_status()["write_blocked"])

    def test_failed_replacement_does_not_commit_memory(self):
        store = SettingsManager(self.path)
        self.assertTrue(store.save({"manual_drive": {"speed": 0.2}})[0])
        before = self.path.read_bytes()
        with patch("pisd.core.config_recovery.os.replace", side_effect=OSError("disk failure")):
            self.assertFalse(store.save({"manual_drive": {"speed": 0.9}})[0])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertAlmostEqual(store.get()["manual_drive"]["speed"], 0.2)

    def test_valid_unknown_settings_roundtrip(self):
        self.path.write_text(json.dumps({"camera": {"future_key": "keep"}, "manual_drive": {"speed": 0.3}}))
        store = SettingsManager(self.path)
        self.assertTrue(store.save({"manual_drive": {"speed": 0.4}})[0])
        self.assertEqual(SettingsManager(self.path).get()["camera"]["future_key"], "keep")
        self.assertFalse(list(self.path.parent.glob("*.bak")))

    def test_visible_warning_and_stop_available(self):
        self.path.write_bytes(b"invalid-json")
        with patch("pisd.app.RUNTIME_SETTINGS_PATH", self.path), patch.dict("os.environ", {"PISD_ACCESS_TOKEN": ""}):
            app = create_app(hardware_enabled=False)
        services = app.config["pisd_services"]
        self.addCleanup(services["camera"].stop)
        self.addCleanup(services["motor"].close)
        self.addCleanup(services["ai_drive"].close)
        client = app.test_client()
        self.assertTrue(client.get("/api/settings").get_json()["config_recovery"]["warning"])
        self.assertIn(b"Malformed runtime configuration", client.get("/settings").data)
        self.assertEqual(client.post("/api/control/stop").status_code, 200)


class PerformanceSettingsReadTests(unittest.TestCase):
    def test_preview_scalar_tracks_successful_save_reload_and_failed_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime_settings.json"
            store = SettingsManager(path)
            self.assertEqual(store.get_camera_live_preview_fps(20),
                             float(store.get()["camera"].get("live_preview_fps", 20)))
            self.assertTrue(store.save({"camera": {"live_preview_fps": 17}})[0])
            self.assertEqual(store.get_camera_live_preview_fps(20), 17)
            with patch.object(store._recovery, "write", side_effect=OSError("test failure")):
                self.assertFalse(store.save({"camera": {"live_preview_fps": 29}})[0])
            self.assertEqual(store.get_camera_live_preview_fps(20), 17)
            self.assertEqual(SettingsManager(path).get_camera_live_preview_fps(20), 17)


if __name__ == "__main__":
    unittest.main()
